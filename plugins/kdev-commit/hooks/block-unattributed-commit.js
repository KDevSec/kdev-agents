#!/usr/bin/env node
// Block git commit from any AI agent when AI identity override is missing.
// PreToolUse/Bash hook. Reads hook JSON on stdin, inspects tool_input.command.
// Human terminal commits are unaffected (hook only runs inside agent sessions).
//
// v0.2.0 身份策略：
//   AI_NAME  = <git user.name>-AI（ASCII 规范化）
//   AI_EMAIL = <git user.email> 真实邮箱（不拼后缀）
// name 和 email 必须同时被 -c 覆盖，否则 deny。
//
// 零外部依赖——只用 Node 内置 child_process。Claude Code 自带 Node 运行时。

'use strict';

const { execSync } = require('node:child_process');

function readStdin() {
  return new Promise((resolve) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
  });
}

function gitConfig(key) {
  try {
    return execSync(`git config ${key}`, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return '';
  }
}

function emitDeny(reason) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
}

(async () => {
  let input;
  try {
    input = JSON.parse(await readStdin() || '{}');
  } catch {
    // malformed stdin → allow silently, don't break the tool call
    return;
  }

  const cmd = (input && input.tool_input && input.tool_input.command) || '';

  // 只拦 git commit 调用（允许中间插 -c k=v）
  if (!/(^|[;&|\s])git(\s+-c\s+\S+)*\s+commit(\s|$)/.test(cmd)) {
    return;
  }

  const userName = gitConfig('user.name');
  const userEmail = gitConfig('user.email');

  if (!userName) {
    emitDeny('git user.name 未配置，无法派生 AI 身份。请先 git config --global user.name <name>');
    return;
  }
  if (!userEmail) {
    emitDeny('git user.email 未配置，AI commit 需要真实邮箱用作 commit email。请先 git config --global user.email <email>');
    return;
  }

  // 规范化：空格 → 连字符；只保留 ASCII 字母数字/_/-
  const safeName = userName.replace(/\s+/g, '-').replace(/[^A-Za-z0-9_-]/g, '');
  if (!safeName) {
    emitDeny(`git user.name=${userName} 无法派生 ASCII AI 名字（全部非 ASCII）。请给 git 配一个 ASCII 别名：git config --global user.name <ascii-name>`);
    return;
  }

  const aiName = `${safeName}-AI`;
  const aiEmail = userEmail;

  const hasName = cmd.includes(`user.name=${aiName}`);
  const hasEmail = cmd.includes(`user.email=${aiEmail}`);

  if (hasName && hasEmail) {
    return;
  }

  emitDeny(
    `AI commit 必须同时覆盖 user.name 和 user.email。请用：git -c user.name=${aiName} -c user.email=${aiEmail} commit ...（name 按 git user.name + -AI 派生，email 直接用 git user.email）`
  );
})();
