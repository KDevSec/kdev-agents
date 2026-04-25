#!/usr/bin/env bash
# weekly.sh —— kdev-memory v0.7.2
# 手动触发滚动 7 天周总结（today-6 ~ today），thin wrapper around weekly.py
# 调用：bash weekly.sh [--from YYYY-MM-DD] [--to YYYY-MM-DD]
#
# v0.7.2：把聚合逻辑从内嵌 heredoc 拆到独立的 weekly.py，避免 Windows
# Git-Bash 下 `python3 - <<EOF` heredoc stdin 在 subprocess 调用时失败的限制。

set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEEKLY_PY="$SCRIPT_DIR/weekly.py"

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)
DATE_FROM=""
DATE_TO=""

while [ $# -gt 0 ]; do
  case "$1" in
    --from) DATE_FROM="$2"; shift 2 ;;
    --to)   DATE_TO="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[ -z "$DATE_TO"   ] && DATE_TO="$TODAY"
[ -z "$DATE_FROM" ] && DATE_FROM=$(date -d "$DATE_TO - 6 days" +%F 2>/dev/null || date -v-6d +%F 2>/dev/null || echo "$TODAY")

if [ ! -d "$KDEV_DIR" ]; then
  echo "[kdev-memory] 当前项目无 $KDEV_DIR，无法生成周总结"
  exit 0
fi

cat <<HEAD
（默认汇总过去 7 天 $DATE_FROM ~ $DATE_TO；可用 \`--from YYYY-MM-DD --to YYYY-MM-DD\` 指定范围）

HEAD

command -v python3 >/dev/null 2>&1 || { echo "[kdev-memory] weekly.sh 需要 python3"; exit 1; }
[ -f "$WEEKLY_PY" ] || { echo "[kdev-memory] 找不到 $WEEKLY_PY"; exit 1; }

python3 "$WEEKLY_PY" "$KDEV_DIR" "$DATE_FROM" "$DATE_TO"
