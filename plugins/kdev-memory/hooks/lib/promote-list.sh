#!/usr/bin/env bash
# promote-list.sh —— 给 /kdev-memory-promote command 调用
# 列出 .kdev/memory/ 下所有 promote_status != done 的条目

set -eu

KDEV_DIR=".kdev/memory"
if [ ! -d "$KDEV_DIR" ]; then
  echo "[kdev-memory] 当前项目无 .kdev/memory/，无候选可沉淀。"
  exit 0
fi

FLUSH="$KDEV_DIR/.last-promote"
TODAY=$(date +%F)
DAYS="never"
if [ -f "$FLUSH" ]; then
  FT=$(stat -c %Y "$FLUSH" 2>/dev/null || stat -f %m "$FLUSH" 2>/dev/null || echo 0)
  if [ "$FT" -gt 0 ] 2>/dev/null; then
    DAYS=$(( ( $(date +%s) - FT ) / 86400 ))
  fi
fi

echo "# /kdev-memory-promote 候选列表"
echo ""
echo "- 扫描时间：$TODAY"
echo "- 距上次沉淀：$DAYS 天"
echo ""

# 扫各来源
for src in "改进建议.md:建议" "conventions.md:R-NNN 规则" "决策日志.md:Q-NNN" "踩坑日志.md:G-NNN" "执行日志.md:Step"; do
  f="${src%%:*}"
  label="${src##*:}"
  [ -f "$KDEV_DIR/$f" ] || continue
  echo "## $label（$KDEV_DIR/$f）"
  echo ""

  # 用 awk 扫描 ## 标题 + 紧随的 promote_status 字段，跳过 done/skipped
  awk '
    /^## / {
      if (title != "" && status != "done" && status != "skipped") {
        printf "- %s  [%s]\n", title, (status == "" ? "pending" : status)
      }
      title = $0
      status = ""
    }
    /^promote_status:[[:space:]]*done/ { status = "done" }
    /^promote_status:[[:space:]]*skipped/ { status = "skipped" }
    /^promote_status:[[:space:]]*pending/ { status = "pending" }
    END {
      if (title != "" && status != "done" && status != "skipped") {
        printf "- %s  [%s]\n", title, (status == "" ? "pending" : status)
      }
    }
  ' "$KDEV_DIR/$f" | head -30
  echo ""
done

echo "---"
echo ""
echo "## 推荐沉淀去向"
echo ""
cat <<'TABLE'
| 来源 | 推荐 docs/ 去向 |
|---|---|
| 改进建议.md | docs/05-报告/实战总结-<项目名>.md 反思章节 |
| conventions.md §11 R-NNN | docs/08-开发规范.md |
| 决策日志.md Q-NNN | docs/04-架构/ADR-NNN.md |
| 踩坑日志.md G-NNN 高频类 | docs/04-架构/踩坑索引.md |
| 执行日志.md Step 4.5+ | docs/05-报告/实战项目总结.md |
TABLE
