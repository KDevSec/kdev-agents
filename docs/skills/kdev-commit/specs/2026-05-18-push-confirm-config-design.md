# 2026-05-18 · kdev-commit push 确认可配置 · 设计 spec

> 状态：**design 已锁定（待用户复核）**
> 起源：[dev-notes/2026-05-18-push-确认可关闭-配置开关-backlog.md](../dev-notes/2026-05-18-push-确认可关闭-配置开关-backlog.md)
> 目标版本：kdev-commit v0.3.0
> 关联文件：`plugins/kdev-commit/hooks/confirm-push.js`、`plugins/kdev-commit/skills/kdev-commit/SKILL.md`、`plugins/kdev-commit/README.md`

## 1. 一句话

让用户可关闭 `git push` 前的 IDE 弹窗（节省一次点击），同时通过 SKILL.md 加粗约束**保证 AI 永不擅自 push**——push 的"唯一 gate"从"IDE 弹窗 + 对话确认"退化为"对话确认"。

## 2. 范围

### 包含
- `confirm-push.js` 增加配置读取与三档行为
- env 变量 `KDEV_COMMIT_PUSH_CONFIRM` 临时切换
- 用户级 JSON 配置文件持久化
- `SKILL.md` 强化"AI 不允许擅自 push"硬规
- `README.md` 新增"配置项"小节
- 回归测试覆盖 8 个核心场景

### 不包含（明确排除）
- ❌ 一次授权永久放行（每次对话仍需重新问）
- ❌ "提交并推送"作为隐式连推授权
- ❌ 白名单仓库 / 按 remote / 按 branch 精细控制
- ❌ 复用 `~/.claude/settings.json` 的 `pluginConfig`（未确认是 Claude Code 官方约定，避免耦合内部 schema）

> ⚠️ 上面前两条（"一次授权永久放行 / 每次重新问"、"提交并推送不作隐式授权"）已被 [2026-06-20-kdev-commit-自主推进令牌放行-design.md](../../../superpowers/specs/2026-06-20-kdev-commit-自主推进令牌放行-design.md) §8 在「自主推进态」开例外（v0.4.0）：用户显式说自主推进触发词后授予 standing 授权，该期间 AI 给 push 盖 `# 自主推进` 令牌跳过弹窗、不再每次问。以新 spec 为准（R-009 回写）。

## 3. 配置入口（最终决策）

### 3.1 两个通道，优先级 env > file > default

| 优先级 | 通道 | 形态 | 用途 |
|--------|------|------|------|
| 1（最高）| env 变量 | `KDEV_COMMIT_PUSH_CONFIRM=off\|warn-force\|ask` | 临时切换、调试、CI |
| 2 | 用户级 JSON | `~/.config/kdev-commit/config.json` | 持久化 |
| 3（兜底）| 默认 | `ask` | 向后兼容 v0.2.0 行为 |

### 3.2 JSON 文件路径与 schema

**路径**：
- Linux / macOS：`~/.config/kdev-commit/config.json`（XDG-style）
- Windows：`%APPDATA%/kdev-commit/config.json`

**schema**（v0.3.0）：
```json
{
  "pushConfirm": "ask"
}
```

`pushConfirm` 取值：
- `"ask"`（默认）：所有 push 弹框
- `"warn-force"`：仅裸 `--force`（非 `--force-with-lease`）弹框，普通 push 静默放行
- `"off"`：完全不弹框（含 `--force`；如需保留 force gate 请用 `warn-force`）

**未来扩展约定**：新增字段（如 `denyForce`）不破坏现有 schema；未知字段忽略不报错。

### 3.3 失败兜底（保守策略）

| 异常 | 行为 |
|------|------|
| env 值为非法字符串（`"yes"` / `"1"` 等） | 静默回落到下一档（file → default） |
| 配置文件不存在 | 回落 default `ask`（正常默认状态） |
| 配置文件 JSON 解析失败 | 静默回落 `ask`，**不抛错**（保证 push 流程不中断） |
| `pushConfirm` 字段缺失或为非法值 | 回落 `ask` |
| 配置文件读权限错误 | 静默回落 `ask` |

**设计原则**：配置错误绝不打断 push；最坏情况退化为弹框（v0.2.0 行为），用户能感知"配置没生效"而不是"push 崩了"。

## 4. SKILL.md 硬规强化

`SKILL.md` 步骤 6 / 7 在原文基础上加入下列加粗硬规（与现有"永远不要"清单合并）：

1. **AI 永不擅自 push**：用户未在当前对话里说出"push / 推 / 推送 / yes / 是 / OK / 推到 X / 推上去"等显式肯定信号前，绝对不执行 `git push`。配置关闭 IDE 弹窗只是省去 IDE 那一道；**对话里那一道永远在**。
2. **"提交并推送" ≠ 永久授权**：即使用户原话是"提交并推送"，下一次提交（下一轮对话循环）仍要重新询问。
3. **commit ≠ push**：若用户原话只说"提交"没说"推"，commit 后必须停下报告状态，不要默认连推。
4. **`--force` 永远额外确认**：即使在 `off` 模式下，AI 在对话里仍要单独强调一次"这是 `--force`，会覆盖远端历史"，等用户再确认一次才推。

这些约束写进 SKILL.md "步骤 6/7" 和"永远不要"两处，确保 AI 加载 skill 时立即看到。

## 5. confirm-push.js 实现草图

```js
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const VALID = new Set(['off', 'warn-force', 'ask']);

function readMode() {
  // 1. env 优先
  const env = process.env.KDEV_COMMIT_PUSH_CONFIRM;
  if (env && VALID.has(env)) return env;

  // 2. 用户级文件
  try {
    const base = process.platform === 'win32'
      ? (process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'))
      : path.join(os.homedir(), '.config');
    const file = path.join(base, 'kdev-commit', 'config.json');
    const data = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (data && VALID.has(data.pushConfirm)) return data.pushConfirm;
  } catch { /* 静默回落 */ }

  // 3. default
  return 'ask';
}

// ... 主流程
const mode = readMode();

// 命令未匹配 git push → 不干预（原逻辑）
if (!/(^|[;&|\s])git(\s+-c\s+\S+)*\s+push(\s|$)/.test(cmd)) return;

const hasBareForce = /(^|\s)--force(\s|$)/.test(cmd);

if (mode === 'off') return;                                // 完全不弹
if (mode === 'warn-force' && !hasBareForce) return;        // 非强推放行

// 其余走原 'ask' 路径
// ... 原 permissionDecision: 'ask' 输出
```

## 6. 测试场景（回归 9 条）

| # | 场景 | 期望 |
|---|------|------|
| T1 | 默认状态（env 未设、文件不存在）+ `git push` | 弹框（同 v0.2.0） |
| T2 | `KDEV_COMMIT_PUSH_CONFIRM=off` + `git push` | 不弹框 |
| T3 | `KDEV_COMMIT_PUSH_CONFIRM=off` + `git push --force` | 不弹框（off 即全关） |
| T4 | `KDEV_COMMIT_PUSH_CONFIRM=warn-force` + `git push` | 不弹框 |
| T5 | `KDEV_COMMIT_PUSH_CONFIRM=warn-force` + `git push --force` | 弹框 |
| T6 | `KDEV_COMMIT_PUSH_CONFIRM=warn-force` + `git push --force-with-lease` | 不弹框 |
| T7 | env=ask + 文件={"pushConfirm":"off"} | 弹框（env 优先） |
| T8 | 配置文件 JSON 损坏（非法字符）+ `git push` | 弹框（回落 ask，无崩溃） |
| T9 | env=`"yes"`（非法值）+ 文件不存在 + `git push` | 弹框（非法值回落） |

**额外不破坏验证**：
- block-unattributed-commit.js 行为完全不变（commit 身份校验照常 deny）
- 非 `git push` 命令（如 `git status` / `npm run push:foo`）不被 hook 拦截

## 7. 文档变更

### 7.1 `plugins/kdev-commit/README.md`
新增"配置项"小节，紧跟"## 核心机制"之后：

```markdown
## 配置项（v0.3.0+）

可选关闭 push 前的 IDE 弹窗。**关闭后 AI 仍由 skill 约束不擅自 push**。

### 三档行为
- `ask`（默认）：所有 push 弹框
- `warn-force`：仅裸 `--force` 弹框，普通 push 静默
- `off`：完全不弹框

### 配置方式
| 优先级 | 通道 | 示例 |
|--------|------|------|
| 1 | env | `export KDEV_COMMIT_PUSH_CONFIRM=warn-force` |
| 2 | 文件 | `~/.config/kdev-commit/config.json`（Windows: `%APPDATA%/kdev-commit/config.json`） |

文件 schema：
\`\`\`json
{ "pushConfirm": "warn-force" }
\`\`\`

### 注意
- 即使关闭 IDE 弹窗，AI 仍**只在对话里收到显式 push 指令后**才推送（由 SKILL.md 硬规约束）
- `--force` 操作建议永远保留 `warn-force` 或 `ask`
```

### 7.2 `plugins/kdev-commit/skills/kdev-commit/SKILL.md`
- 步骤 6 末尾加加粗硬规第 1-3 条
- "永远不要"清单加第 4 条（--force 在 off 模式仍额外确认）

### 7.3 `CHANGELOG`（如有）
v0.3.0 增量：`pushConfirm` 三档配置（env + 文件，默认 `ask` 向后兼容）

## 8. 边界与风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| SKILL.md 约束被 AI 误解，关掉 hook 后真的擅自推 | 严重（用户失去最后 gate） | 步骤 6/7 加粗 + "永远不要"清单 + README 反复提示；回归测试 T2/T3 在 `off` 模式下不自动 push（人工 + AI 协议双重） |
| `~/.config/kdev-commit/` 路径未来与 Claude Code 官方 plugin config 约定冲突 | 中等（需要迁移） | schema 极简（单字段），未来加迁移脚本即可 |
| Windows `%APPDATA%` 与 XDG 路径行为差异 | 低 | 测试 T8 覆盖路径不存在场景；platform 分支显式处理 |
| 配置文件 JSON 损坏导致 hook 崩溃，进而 push 全失败 | 中等（影响所有 push） | T8 验证；try/catch 包住所有 IO + JSON.parse |

## 9. 实现顺序（writing-plans 输入）

1. **测试先行**：在 `plugins/kdev-commit/hooks/__tests__/confirm-push.test.js` 新建测试套件，覆盖 T1-T9 + 不破坏验证（mock stdin / env / fs）
2. **实现 `readMode()`**：env → file → default 三层，含失败兜底
3. **嵌入主流程**：在原命令匹配逻辑前先读 mode，按 mode 分支返回
4. **SKILL.md 更新**：步骤 6/7 + "永远不要"清单
5. **README 更新**：新增"配置项"小节
6. **回归**：跑测试 + 手动验证 v0.2.0 默认行为不变
7. **ship**：bump `plugins/kdev-commit/.claude-plugin/plugin.json` version `0.2.0` → `0.3.0`，commit，PR

## 10. 验收标准

- [ ] 9 个回归测试全部 pass
- [ ] block-unattributed-commit 行为完全不变（commit 身份校验照常）
- [ ] 默认配置下行为与 v0.2.0 完全一致（向后兼容）
- [ ] SKILL.md 在 `off` 模式下被 AI 读到时，AI 不主动 push（人工抽样验证）
- [ ] README 配置项小节让一个没读过源码的用户 5 分钟内能跑通 `off` 模式
