#!/usr/bin/env bash
# kdev-memory UserPromptSubmit hook
# 用户每次发 prompt 时，扫 .kdev/memory/ 里的 triggers 字段，匹配命中就注入
# <kdev-memory-recall> 提示给 Claude。渐进式披露（只给编号+标题+路径）。
#
# 本脚本是薄壳，核心逻辑在 hooks/lib/trigger-match.py。原因：
#   - triggers 扫描 / 去重 / 格式化涉及多文件、JSON 状态、regex，bash 写起来绕
#   - python3 写 200 行清晰，bash 写 400 行还 buggy
#
# 前置：python3（Claude Code 环境几乎都有）。无 python3 就静默失败。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/migrate.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/migrate.sh"

# 防御性迁移（UserPromptSubmit 可能早于 SessionStart 在某些边缘场景下触发）
kdev_memory_migrate

# 无 python3 → 静默退出，让 Claude Code 继续处理 prompt
command -v python3 >/dev/null 2>&1 || {
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
}

# stdin 带 1 秒超时，防 hang
[ -t 0 ] && { echo '{"continue":true,"suppressOutput":true}'; exit 0; }
INPUT=$(timeout 1 cat 2>/dev/null || true)
if [ -z "$INPUT" ]; then
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
fi

# 把 input 原样传给 python 核心
printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/lib/trigger-match.py"
