#!/usr/bin/env node
// Confirm every `git push` from AI agent via IDE permission prompt.
// PreToolUse/Bash hook. Emits permissionDecision="ask" so Claude Code
// surfaces a one-click allow/deny dialog.
// --force (without -with-lease) is flagged in the reason.
// v0.3.0+: KDEV_COMMIT_PUSH_CONFIRM env / ~/.config/kdev-commit/config.json
//          three-level config (off / warn-force / ask). SKILL.md 仍硬约束 AI
//          不擅自 push——hook 关只关 IDE 弹窗，对话层 gate 永在。
// v0.4.0+: 「自主推进」令牌——命令含 `# 自主推进` 注释（正则 /#\s*自主推进/）则
//          放行普通 push（跳弹窗），但裸 --force 即便带令牌也仍弹窗兜底。
//          授权来自用户对话（SKILL.md 触发集），AI 翻译成这个单一令牌盖在命令上。

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
  // 裸强推：`--force`（后面不接 `-`，区分 `--force-with-lease`）或短别名 `-f`
  const hasBareForce = /(^|\s)(--force(?!-)(\s|$)|-f(\s|$))/.test(cmd);
  // 自主推进令牌：`#` 注释前缀 + 仅空白 + `自主推进`（强制 `#` 防 branch 名/commit msg 误触）
  const hasAutoToken = /#\s*自主推进/.test(cmd);

  if (mode === 'off') return;
  // 令牌放行普通 push；裸 --force 即便带令牌也落到后面的弹窗兜底
  if (hasAutoToken && !hasBareForce) return;
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
