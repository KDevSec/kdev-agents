#!/usr/bin/env bash
# Block git commit from any AI agent when AI identity override is missing.
# Fires as a PreToolUse/Bash hook. Reads hook JSON on stdin, inspects
# tool_input.command. Human terminal commits are unaffected
# (hook only runs inside agent sessions).
#
# AI_EMAIL 运行时从 git config user.name 动态派生——
# 尊重 git 的 local > global > system 优先级，
# 团队成员换名字 / 不同项目用不同身份都能自动适配。
set -euo pipefail

cmd=$(jq -r '.tool_input.command // ""')

# Not a git commit invocation → allow silently
if ! printf '%s' "$cmd" | grep -qE '(^|[;&|[:space:]])git([[:space:]]+-c[[:space:]]+[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'; then
  exit 0
fi

# 派生 AI 身份：取当前 git user.name（遵守 local > global 优先级），加 -AI 后缀
USER_NAME=$(git config user.name 2>/dev/null || true)

# 无 git 身份 → 让用户先配置
if [ -z "$USER_NAME" ]; then
  jq -n '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: "git user.name 未配置，无法派生 AI 身份。请先 git config --global user.name <name>"
    }
  }'
  exit 0
fi

# 规范化：空格 → 连字符；只保留 ASCII 字母数字/_/-。非 ASCII 直接报错
SAFE_NAME=$(printf '%s' "$USER_NAME" | tr ' ' '-' | tr -cd 'A-Za-z0-9_-')
if [ -z "$SAFE_NAME" ]; then
  jq -n --arg raw "$USER_NAME" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("git user.name=" + $raw + " 无法派生 email-safe AI 名字（全部非 ASCII）。请给 git 配一个 ASCII 别名：git config --global user.name <ascii-name>")
    }
  }'
  exit 0
fi

AI_NAME="${SAFE_NAME}-AI"
AI_EMAIL="${AI_NAME}@noreply.local"

# Has required email override → allow
if printf '%s' "$cmd" | grep -qF "user.email=$AI_EMAIL"; then
  exit 0
fi

jq -n --arg name "$AI_NAME" --arg email "$AI_EMAIL" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("AI commit 必须覆盖身份。请用：git -c user.name=" + $name + " -c user.email=" + $email + " commit ...（AI 身份按 git user.name + -AI 派生）")
  }
}'
