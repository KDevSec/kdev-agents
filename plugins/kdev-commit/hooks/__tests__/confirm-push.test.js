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
