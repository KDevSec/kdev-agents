#!/usr/bin/env node
// Confirm every `git push` from AI agent via IDE permission prompt.
// PreToolUse/Bash hook. Emits permissionDecision="ask" so Claude Code
// surfaces a one-click allow/deny dialog.
// --force (without -with-lease) is flagged in the reason.

'use strict';

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

  // 只警告裸 --force；--force-with-lease 等变体不警告
  const hasBareForce = /(^|\s)--force(\s|$)/.test(cmd);
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
