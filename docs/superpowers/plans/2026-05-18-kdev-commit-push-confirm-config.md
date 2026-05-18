# kdev-commit v0.3.0 · push 确认可配置 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 `confirm-push.js` 加 env + 用户级 JSON 配置入口，让用户可关 IDE 弹窗（三档：`off` / `warn-force` / `ask`），并强化 SKILL.md 硬规防 AI 擅自 push。

**Architecture:** 在 hook 主流程前插入 `readMode()`（env → file → default），按 mode 早返；保持现有 `permissionDecision: "ask"` 输出路径不变。新增 `__tests__/confirm-push.test.js`（Node 内置 `node:test`）spawn 子进程验证 stdin/env/fs → stdout。SKILL.md 在步骤 6/7 加粗"对话层永远 gate"硬规。

**Tech Stack:** Node.js ≥18（仓库 v24.14.1，`node:test` 内建）、纯 stdlib（`fs` / `path` / `os` / `child_process`），不引入任何 npm 包。

**Spec:** [docs/skills/kdev-commit/specs/2026-05-18-push-confirm-config-design.md](../../skills/kdev-commit/specs/2026-05-18-push-confirm-config-design.md)

---

## File Structure

| 路径 | 操作 | 责任 |
|------|------|------|
| `plugins/kdev-commit/hooks/confirm-push.js` | 修改 | 增 `readMode()`、`getConfigPath()`、按 mode 分支早返 |
| `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js` | 新建 | 覆盖 T1-T9 回归 |
| `plugins/kdev-commit/hooks/__tests__/run-tests.sh` | 新建 | 一行启动 `node --test` 的入口（便于本地/CI 调用） |
| `plugins/kdev-commit/skills/kdev-commit/SKILL.md` | 修改 | 步骤 6/7 加粗硬规 + "永远不要"加 `--force` 额外确认 |
| `plugins/kdev-commit/README.md` | 修改 | 新增"配置项"小节 |
| `plugins/kdev-commit/.claude-plugin/plugin.json` | 修改 | version `0.2.0` → `0.3.0` |

---

## Task 1: 测试脚手架 + 默认行为基线测试（T1）

**目的**：在改任何实现代码前，先用一条"默认状态弹框"的回归测试锁住 v0.2.0 行为，确保后续改动不破坏向后兼容。

**Files:**
- Create: `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`
- Create: `plugins/kdev-commit/hooks/__tests__/run-tests.sh`

- [ ] **Step 1: 写测试文件骨架 + T1 默认行为测试**

`plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`：

```js
'use strict';

const { test } = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const HOOK = path.join(__dirname, '..', 'confirm-push.js');

// 在隔离的临时 HOME 下跑 hook，避免读到真实用户的 ~/.config
function runHook({ cmd, env = {}, configContent = null, configPath = null }) {
  const tmpHome = fs.mkdtempSync(path.join(os.tmpdir(), 'kdev-test-home-'));
  try {
    if (configContent !== null) {
      const cfgDir = configPath
        ? path.join(tmpHome, ...configPath)
        : path.join(tmpHome, '.config', 'kdev-commit');
      fs.mkdirSync(cfgDir, { recursive: true });
      fs.writeFileSync(path.join(cfgDir, 'config.json'), configContent);
    }

    const childEnv = {
      ...process.env,
      HOME: tmpHome,
      USERPROFILE: tmpHome,
      APPDATA: path.join(tmpHome, 'AppData', 'Roaming'),
      // 显式清理可能存在的 env，避免污染
      KDEV_COMMIT_PUSH_CONFIRM: '',
      ...env,
    };

    const input = JSON.stringify({ tool_input: { command: cmd } });
    const result = spawnSync(process.execPath, [HOOK], {
      input,
      env: childEnv,
      encoding: 'utf8',
      timeout: 5000,
    });

    return {
      stdout: result.stdout || '',
      stderr: result.stderr || '',
      status: result.status,
      parsed: result.stdout ? safeParse(result.stdout) : null,
    };
  } finally {
    fs.rmSync(tmpHome, { recursive: true, force: true });
  }
}

function safeParse(s) {
  try { return JSON.parse(s); } catch { return null; }
}

function asksForConfirm(out) {
  return out.parsed
    && out.parsed.hookSpecificOutput
    && out.parsed.hookSpecificOutput.permissionDecision === 'ask';
}

test('T1: 默认（env 未设、文件不存在）git push 应弹框', () => {
  const out = runHook({ cmd: 'git push' });
  assert.ok(asksForConfirm(out), `期望弹框但 stdout=${out.stdout}`);
});
```

- [ ] **Step 2: 写 runner 脚本**

`plugins/kdev-commit/hooks/__tests__/run-tests.sh`：

```bash
#!/usr/bin/env bash
# kdev-commit hook 测试入口（Node 内置 node:test，零外部依赖）
set -euo pipefail
cd "$(dirname "$0")/.."
exec node --test __tests__/
```

设置可执行权限：

```bash
chmod +x plugins/kdev-commit/hooks/__tests__/run-tests.sh
```

- [ ] **Step 3: 跑测试，确认 T1 PASS（v0.2.0 现状已满足）**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 1 test passed（T1）。如失败说明 v0.2.0 基线行为已经偏移，需先排查。

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-commit/hooks/__tests__/
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-commit): 测试脚手架 + T1 默认弹框基线"
```

---

## Task 2: T2/T3 — env=off 全静默（含 --force）

**Files:**
- Modify: `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`（追加）
- Modify: `plugins/kdev-commit/hooks/confirm-push.js`

- [ ] **Step 1: 追加 T2/T3 测试（先失败）**

在 `confirm-push.test.js` 末尾追加：

```js
test('T2: env=off + git push 不弹框', () => {
  const out = runHook({
    cmd: 'git push',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'off' },
  });
  assert.equal(out.stdout, '', `期望静默但 stdout=${out.stdout}`);
});

test('T3: env=off + git push --force 仍不弹框（off 即全关）', () => {
  const out = runHook({
    cmd: 'git push --force',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'off' },
  });
  assert.equal(out.stdout, '', `期望静默但 stdout=${out.stdout}`);
});
```

- [ ] **Step 2: 跑测试，确认 T2/T3 FAIL**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: T2/T3 FAIL（当前实现没有 env 读取，所有 push 都弹框）

- [ ] **Step 3: 实现 readMode() 的 env 层**

修改 `plugins/kdev-commit/hooks/confirm-push.js`，在文件顶部 `'use strict';` 之后插入：

```js
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const VALID_MODES = new Set(['off', 'warn-force', 'ask']);

function getConfigPath() {
  if (process.platform === 'win32') {
    const base = process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming');
    return path.join(base, 'kdev-commit', 'config.json');
  }
  return path.join(os.homedir(), '.config', 'kdev-commit', 'config.json');
}

function readMode() {
  // 1. env 优先
  const env = process.env.KDEV_COMMIT_PUSH_CONFIRM;
  if (env && VALID_MODES.has(env)) return env;

  // 2. 用户级 JSON 文件
  try {
    const data = JSON.parse(fs.readFileSync(getConfigPath(), 'utf8'));
    if (data && VALID_MODES.has(data.pushConfirm)) return data.pushConfirm;
  } catch { /* 静默回落 */ }

  // 3. default
  return 'ask';
}
```

然后在主 IIFE 内，命令匹配通过之后、`hasBareForce` 计算之前，插入 mode 分支：

```js
  if (!/(^|[;&|\s])git(\s+-c\s+\S+)*\s+push(\s|$)/.test(cmd)) {
    return;
  }

  const mode = readMode();
  const hasBareForce = /(^|\s)--force(\s|$)/.test(cmd);

  if (mode === 'off') return;
  if (mode === 'warn-force' && !hasBareForce) return;

  // 其余继续走 'ask' 原路径
  const warn = hasBareForce
    ? '\n警告：包含 --force（非 --force-with-lease），可能覆盖远端历史。'
    : '';
```

完整改后文件（确认上下文）：

```js
#!/usr/bin/env node
// Confirm every `git push` from AI agent via IDE permission prompt.
// PreToolUse/Bash hook. Emits permissionDecision="ask" so Claude Code
// surfaces a one-click allow/deny dialog.
// --force (without -with-lease) is flagged in the reason.
// v0.3.0+: KDEV_COMMIT_PUSH_CONFIRM env / ~/.config/kdev-commit/config.json
//          three-level config (off / warn-force / ask). SKILL.md 仍硬约束 AI
//          不擅自 push——hook 关只关 IDE 弹窗，对话层 gate 永在。

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const VALID_MODES = new Set(['off', 'warn-force', 'ask']);

function getConfigPath() {
  if (process.platform === 'win32') {
    const base = process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming');
    return path.join(base, 'kdev-commit', 'config.json');
  }
  return path.join(os.homedir(), '.config', 'kdev-commit', 'config.json');
}

function readMode() {
  const env = process.env.KDEV_COMMIT_PUSH_CONFIRM;
  if (env && VALID_MODES.has(env)) return env;

  try {
    const data = JSON.parse(fs.readFileSync(getConfigPath(), 'utf8'));
    if (data && VALID_MODES.has(data.pushConfirm)) return data.pushConfirm;
  } catch { /* 静默回落 */ }

  return 'ask';
}

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
  });
}

(async () => {
  let input;
  try {
    input = JSON.parse(await readStdin() || '{}');
  } catch {
    return;
  }

  const cmd = (input && input.tool_input && input.tool_input.command) || '';

  if (!/(^|[;&|\s])git(\s+-c\s+\S+)*\s+push(\s|$)/.test(cmd)) {
    return;
  }

  const mode = readMode();
  const hasBareForce = /(^|\s)--force(\s|$)/.test(cmd);

  if (mode === 'off') return;
  if (mode === 'warn-force' && !hasBareForce) return;

  const warn = hasBareForce
    ? '\n警告：包含 --force（非 --force-with-lease），可能覆盖远端历史。'
    : '';

  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'ask',
      permissionDecisionReason: `AI 请求执行 push：\n  ${cmd}${warn}\n是否确认？`,
    },
  }));
})();
```

- [ ] **Step 4: 跑测试，确认 T1/T2/T3 全 PASS**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 3 tests passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-commit/hooks/confirm-push.js plugins/kdev-commit/hooks/__tests__/confirm-push.test.js
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-commit): readMode() env 层 + off 模式全静默"
```

---

## Task 3: T4/T5/T6 — warn-force 模式（仅裸 --force 弹框）

**Files:**
- Modify: `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`（追加）

注：实现 Task 2 已完成所有 mode 分支，本 Task 仅追加测试验证。

- [ ] **Step 1: 追加 T4/T5/T6 测试**

```js
test('T4: env=warn-force + 普通 push 不弹框', () => {
  const out = runHook({
    cmd: 'git push',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'warn-force' },
  });
  assert.equal(out.stdout, '');
});

test('T5: env=warn-force + git push --force 弹框', () => {
  const out = runHook({
    cmd: 'git push --force',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'warn-force' },
  });
  assert.ok(asksForConfirm(out), `期望弹框但 stdout=${out.stdout}`);
  assert.match(
    out.parsed.hookSpecificOutput.permissionDecisionReason,
    /--force/,
    '弹框 reason 应包含 --force 警告'
  );
});

test('T6: env=warn-force + git push --force-with-lease 不弹框', () => {
  const out = runHook({
    cmd: 'git push --force-with-lease',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'warn-force' },
  });
  assert.equal(out.stdout, '');
});
```

- [ ] **Step 2: 跑测试，确认 T1-T6 全 PASS**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 6 tests passed

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/hooks/__tests__/confirm-push.test.js
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-commit): warn-force 模式 T4/T5/T6 覆盖"
```

---

## Task 4: T7 — env 优先级高于 file

**Files:**
- Modify: `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`（追加）

- [ ] **Step 1: 追加 T7 测试**

```js
test('T7: env=ask + file=off → env 赢，弹框', () => {
  const out = runHook({
    cmd: 'git push',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'ask' },
    configContent: JSON.stringify({ pushConfirm: 'off' }),
  });
  assert.ok(asksForConfirm(out), `期望弹框（env 优先）但 stdout=${out.stdout}`);
});

test('T7b: env 未设 + file=off → file 生效，不弹框', () => {
  const out = runHook({
    cmd: 'git push',
    configContent: JSON.stringify({ pushConfirm: 'off' }),
  });
  assert.equal(out.stdout, '', '期望 file=off 生效');
});
```

- [ ] **Step 2: 跑测试，确认 T7/T7b PASS**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 8 tests passed

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/hooks/__tests__/confirm-push.test.js
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-commit): env > file 优先级 T7 覆盖"
```

---

## Task 5: T8/T9 — 失败兜底（JSON 损坏 / env 非法值）

**Files:**
- Modify: `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js`（追加）

- [ ] **Step 1: 追加 T8/T9 + 边界测试**

```js
test('T8: 配置文件 JSON 损坏 → 回落 ask，弹框，不崩溃', () => {
  const out = runHook({
    cmd: 'git push',
    configContent: '{ this is not valid json',
  });
  assert.ok(asksForConfirm(out), `期望弹框（回落 ask）但 stdout=${out.stdout}`);
  assert.equal(out.status, 0, 'hook 应正常退出（不崩溃）');
});

test('T9: env 非法值（"yes"） → 回落到 file/default，弹框', () => {
  const out = runHook({
    cmd: 'git push',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'yes' },
  });
  assert.ok(asksForConfirm(out));
});

test('T9b: file 字段非法值（"yes"） → 回落 ask', () => {
  const out = runHook({
    cmd: 'git push',
    configContent: JSON.stringify({ pushConfirm: 'yes' }),
  });
  assert.ok(asksForConfirm(out));
});

test('T9c: file 缺少 pushConfirm 字段 → 回落 ask', () => {
  const out = runHook({
    cmd: 'git push',
    configContent: JSON.stringify({ unrelated: 'value' }),
  });
  assert.ok(asksForConfirm(out));
});

test('不破坏验证: 非 git push 命令（如 git status）→ 不拦截', () => {
  const out = runHook({
    cmd: 'git status',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'ask' },
  });
  assert.equal(out.stdout, '');
});

test('不破坏验证: 名字像 push 的别的命令（npm run push:foo）不拦截', () => {
  const out = runHook({
    cmd: 'npm run push:foo',
  });
  assert.equal(out.stdout, '');
});
```

- [ ] **Step 2: 跑测试**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 14 tests passed（T1-T9c + 2 个不破坏验证）

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/hooks/__tests__/confirm-push.test.js
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-commit): 失败兜底 T8/T9 + 命令匹配边界"
```

---

## Task 6: SKILL.md 强化"AI 永不擅自 push"硬规

**Files:**
- Modify: `plugins/kdev-commit/skills/kdev-commit/SKILL.md`

- [ ] **Step 1: 修改步骤 6（询问用户是否 push）**

定位 `### 步骤 6：询问用户是否 push` 段落，把当前内容：

```markdown
### 步骤 6：询问用户是否 push

commit 完成后，用自然语言问用户："要 push 到远端吗？"

- 用户答"要 / yes / 推 / 是" → 继续步骤 7
- 用户答"不要 / 先别 / 等等" → 停，报告 commit hash 和未推送状态
```

替换为：

```markdown
### 步骤 6：询问用户是否 push

commit 完成后，用自然语言问用户："要 push 到远端吗？"

- 用户答"要 / yes / 推 / 是 / OK / 推上去" → 继续步骤 7
- 用户答"不要 / 先别 / 等等" → 停，报告 commit hash 和未推送状态

**🔴 对话层硬规（v0.3.0 起 IDE 弹窗可配置，对话层 gate 永远在）**：

1. **AI 永不擅自 push**：用户未在**当前对话**里说出 push / 推 / 推送 / yes / 是 / OK / 推到 X / 推上去 等显式肯定信号前，绝对不执行 `git push`。`KDEV_COMMIT_PUSH_CONFIRM=off` 只关 IDE 那道，**这道永远不关**。
2. **"提交并推送" ≠ 永久授权**：即使用户原话含"提交并推送"，下一次提交（下一轮请求循环）仍要重新询问。
3. **commit ≠ push**：用户原话只说"提交 / commit"没说"推 / push"时，commit 后必须停下报告 hash + 未推状态，**不要默认连推**。
```

- [ ] **Step 2: 修改"永远不要"清单**

定位步骤 7 末尾的 `**永远不要**：` 块：

```markdown
**永远不要**：
- 用 `--force`（除非用户明确说"强推"，且优先建议 `--force-with-lease`）
- 在用户没说"push"的情况下擅自推
```

替换为：

```markdown
**永远不要**：
- 用 `--force`（除非用户明确说"强推"，且优先建议 `--force-with-lease`）
- 在用户没说"push"的情况下擅自推
- **`--force` 在 `off` 配置下擅自推**：即使 hook 不弹框，AI 在对话里仍要单独提示一次"这是 `--force`，会覆盖远端历史"，等用户再确认一次才推
```

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/skills/kdev-commit/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-commit): SKILL.md 加粗 AI 不擅自 push 对话层硬规"
```

---

## Task 7: README.md 配置项小节

**Files:**
- Modify: `plugins/kdev-commit/README.md`

- [ ] **Step 1: 在 README "## 核心机制（v0.2.0）" 之后、"### 零外部依赖" 之前插入新小节**

定位 `### 4. 运行时动态派生 AI 身份` 段落结束后（`### 零外部依赖` 之前），插入：

```markdown
### 5. 可配置 push 弹窗（v0.3.0+）

默认每次 push 都弹 IDE 权限框（"两道 gate"）。成熟用户可关掉 IDE 那道，节省一次点击。**对话层那道永远在**：AI 仍由 SKILL.md 约束不擅自 push。

三档：

| 值 | 行为 |
|---|---|
| `ask`（默认） | 所有 push 弹框 |
| `warn-force` | 仅裸 `--force`（非 `--force-with-lease`）弹框，普通 push 静默 |
| `off` | 完全不弹框（含 `--force`；要保留 `--force` gate 请用 `warn-force`） |

两个配置通道（**env 优先级高于文件**）：

```bash
# 临时切换（当前 shell 生效）
export KDEV_COMMIT_PUSH_CONFIRM=warn-force

# 持久化（Linux/macOS）
mkdir -p ~/.config/kdev-commit
echo '{"pushConfirm":"warn-force"}' > ~/.config/kdev-commit/config.json

# Windows
# %APPDATA%/kdev-commit/config.json
```

配置错误（JSON 损坏 / 非法值 / 文件不存在）→ 静默回落到 `ask`（默认行为），不影响 push 流程。

```

- [ ] **Step 2: 把开头"核心机制（v0.2.0）"标题改为"核心机制"（避免版本绑定漂移）**

定位：

```markdown
## 核心机制（v0.2.0）
```

替换为：

```markdown
## 核心机制
```

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/README.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-commit): README 新增 v0.3.0 配置项小节"
```

---

## Task 8: 版本 bump 到 0.3.0

**Files:**
- Modify: `plugins/kdev-commit/.claude-plugin/plugin.json`

- [ ] **Step 1: 读当前 plugin.json**

```bash
cat plugins/kdev-commit/.claude-plugin/plugin.json
```

确认 `"version": "0.2.0"` 在第 4 行附近。

- [ ] **Step 2: 改 version**

用 Edit 把 `"version": "0.2.0"` 改为 `"version": "0.3.0"`。

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-commit/.claude-plugin/plugin.json
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-commit): v0.3.0—push 确认可配置（env + 用户级 JSON）"
```

---

## Task 9: 端到端回归 + 手动确认默认行为

**Files:**（验证）

- [ ] **Step 1: 跑完整测试套件**

Run: `bash plugins/kdev-commit/hooks/__tests__/run-tests.sh`
Expected: 14 tests passed (T1-T9c + 不破坏 × 2)

- [ ] **Step 2: 手动验证默认行为不变（env 未设 + 文件不存在）**

```bash
# 确认本机没有遗留配置
test -f ~/.config/kdev-commit/config.json && echo "WARN: 已有配置" || echo "OK: 无遗留"
unset KDEV_COMMIT_PUSH_CONFIRM

# 模拟 Claude Code 调用 hook
echo '{"tool_input":{"command":"git push"}}' | node plugins/kdev-commit/hooks/confirm-push.js
```

Expected: 输出 JSON 含 `"permissionDecision":"ask"`

- [ ] **Step 3: 手动验证 off 模式**

```bash
echo '{"tool_input":{"command":"git push"}}' | KDEV_COMMIT_PUSH_CONFIRM=off node plugins/kdev-commit/hooks/confirm-push.js
```

Expected: 完全无输出（静默放行）

- [ ] **Step 4: 手动验证 warn-force**

```bash
# 普通 push 应静默
echo '{"tool_input":{"command":"git push"}}' | KDEV_COMMIT_PUSH_CONFIRM=warn-force node plugins/kdev-commit/hooks/confirm-push.js

# --force 应弹框
echo '{"tool_input":{"command":"git push --force"}}' | KDEV_COMMIT_PUSH_CONFIRM=warn-force node plugins/kdev-commit/hooks/confirm-push.js
```

Expected: 第一条无输出；第二条输出含 `--force` 警告的 ask JSON。

- [ ] **Step 5: 验证 block-unattributed-commit 不受影响**

```bash
echo '{"tool_input":{"command":"git commit -m test"}}' | node plugins/kdev-commit/hooks/block-unattributed-commit.js
```

Expected: 输出 `deny` 决定（要求 `-c user.name=*-AI`），证明 commit 校验完全不变。

- [ ] **Step 6: 报告完成**

如全部通过，本计划完成；如任一失败，回到对应 Task 修复。

---

## 验收对照表（来自 spec §10）

| 验收项 | 由哪条 Task / Step 满足 |
|---|---|
| 9 个回归测试全部 pass | Task 9 Step 1（14 个测试覆盖 T1-T9c + 不破坏 × 2） |
| block-unattributed-commit 行为完全不变 | Task 9 Step 5（手动验证） |
| 默认配置下行为与 v0.2.0 完全一致 | Task 1（T1 基线） + Task 9 Step 2 |
| SKILL.md 在 off 模式下 AI 不主动 push | Task 6（步骤 6 加粗 + "永远不要"加项） |
| README 配置项小节让新手 5 分钟跑通 | Task 7（含三档表 + 双通道 + 示例命令） |
