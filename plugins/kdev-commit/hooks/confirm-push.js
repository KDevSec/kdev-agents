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
