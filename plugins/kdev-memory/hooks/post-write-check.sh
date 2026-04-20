#!/usr/bin/env bash
# kdev-memory PostToolUse hook
# Claude 每次 Write/Edit/MultiEdit/NotebookEdit 命中里程碑白名单时注入一条软提醒：
# "刚动了里程碑文件 X，请把对应 Step 追加到 .kdev/执行日志.md"
#
# 白名单在 hooks/lib/milestone.sh 中维护（覆盖 Spec Kit、ADR、迭代/Sprint、
# 架构/PRD/设计、根目录关键文档、数据库 migration、OpenAPI/GraphQL/Proto 契约等）

KDEV_DIR=".kdev"

# 项目未启用 .kdev/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

# 读 hook JSON，拿 tool_input.file_path
# stdin 带 1 秒超时，避免管道未 EOF 永久 hang
[ -t 0 ] && exit 0
INPUT=$(timeout 1 cat 2>/dev/null || true)
[ -n "$INPUT" ] || exit 0

# 用 python3 解析（依赖 python3，不存在就静默）
command -v python3 >/dev/null 2>&1 || exit 0

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c 'import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input", {}) or {}
    print(ti.get("file_path") or ti.get("notebook_path") or "")
except Exception:
    pass' 2>/dev/null)

[ -n "$FILE_PATH" ] || exit 0

# 把绝对路径转成相对路径（便于匹配 specs/ 这种相对前缀）
REL_PATH="$FILE_PATH"
CWD=$(pwd)
case "$FILE_PATH" in
  "$CWD"/*) REL_PATH="${FILE_PATH#$CWD/}" ;;
esac

# 引入里程碑白名单
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/milestone.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/milestone.sh"

if is_milestone_path "$REL_PATH"; then
  echo "[kdev-memory] 刚动了里程碑文件 $REL_PATH —— 请把对应的 Step 追加到 .kdev/执行日志.md（说明这次变更的目的、产出、模型自评）。"
fi

exit 0
