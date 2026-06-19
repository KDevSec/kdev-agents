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
      timeout: 30000,
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

test('T5b: env=warn-force + git push -f（短别名）弹框', () => {
  const out = runHook({
    cmd: 'git push -f',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'warn-force' },
  });
  assert.ok(asksForConfirm(out), `期望弹框（-f 是 --force 短别名）但 stdout=${out.stdout}`);
});

test('T5c: env=warn-force + git push -f origin main 弹框', () => {
  const out = runHook({
    cmd: 'git push -f origin main',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'warn-force' },
  });
  assert.ok(asksForConfirm(out));
});

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

// ── v0.4.0 自主推进令牌（# 自主推进）放行 ──

test('T10: 令牌 + 普通 push（默认 ask）→ 不弹框', () => {
  const out = runHook({ cmd: 'git push # 自主推进' });
  assert.equal(out.stdout, '', `期望令牌放行静默但 stdout=${out.stdout}`);
});

test('T11: 令牌 + 裸 --force → 仍弹框（--force 兜底，令牌不放行）', () => {
  const out = runHook({ cmd: 'git push --force # 自主推进' });
  assert.ok(asksForConfirm(out), `期望强推仍弹框但 stdout=${out.stdout}`);
  assert.match(
    out.parsed.hookSpecificOutput.permissionDecisionReason,
    /--force/,
    '弹框 reason 应包含 --force 警告'
  );
});

test('T12: 令牌 + --force-with-lease → 不弹框（非裸 force）', () => {
  const out = runHook({ cmd: 'git push --force-with-lease # 自主推进' });
  assert.equal(out.stdout, '', `期望放行静默但 stdout=${out.stdout}`);
});

test('T13: 无令牌 + 普通 push（ask）→ 弹框（手动模式兜底回归）', () => {
  const out = runHook({ cmd: 'git push' });
  assert.ok(asksForConfirm(out), `期望手动模式弹框但 stdout=${out.stdout}`);
});

test('T14: 令牌 + env=off → 不弹框（off 即全关，令牌无关）', () => {
  const out = runHook({
    cmd: 'git push # 自主推进',
    env: { KDEV_COMMIT_PUSH_CONFIRM: 'off' },
  });
  assert.equal(out.stdout, '');
});

test('T15: 防误触 — branch 名含"自主推进"但无 # 注释 → 弹框', () => {
  const out = runHook({ cmd: 'git push origin feat-自主推进' });
  assert.ok(asksForConfirm(out), `branch 名字样不应算令牌，期望弹框但 stdout=${out.stdout}`);
});

test('T16: 防误触 — "自主推进"在 commit message 里（链式命令）→ 弹框', () => {
  const out = runHook({ cmd: 'git commit -m "feat: 自主推进模式" && git push' });
  assert.ok(asksForConfirm(out), `commit msg 字样不应算令牌，期望弹框但 stdout=${out.stdout}`);
});

test('T17: 容错 — `git push #自主推进`（# 与字之间无空格）→ 不弹框', () => {
  const out = runHook({ cmd: 'git push #自主推进' });
  assert.equal(out.stdout, '', `\\s* 应容忍 0 空白，期望放行但 stdout=${out.stdout}`);
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
