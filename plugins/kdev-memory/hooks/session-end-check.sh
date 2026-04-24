#!/usr/bin/env bash
# kdev-memory SessionEnd hook (v0.7)
# 会话真正结束时的兜底：用 mtime 比对替代 git status
# 检测 .kdev/memory/ 下有无比 .last-flush 更新的文件 → 若有则写 WARN
# v0.7 立场反转后 .kdev/ 默认 gitignore，git status 拿不到 .kdev/ 变化，必须换机制

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/migrate.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/migrate.sh"

# 防御性迁移：0.2.0 遗留结构自动搬到 .kdev/memory/
kdev_memory_migrate

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)
LOG_FILE="$KDEV_DIR/执行日志.md"
FLUSH_FILE="$KDEV_DIR/.last-flush"
WARN_FILE="$KDEV_DIR/WARN-未记录-$TODAY.md"

# 项目未启用 .kdev/memory/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

# 执行日志今天已有条目 → 无需警告
if [ -f "$LOG_FILE" ] && grep -q "$TODAY" "$LOG_FILE" 2>/dev/null; then
  exit 0
fi

# 检测 .kdev/memory/ 下有无比 .last-flush 更新的文件（不依赖 git）
CHANGED_FILES=""
if [ -f "$FLUSH_FILE" ]; then
  CHANGED_FILES=$(find "$KDEV_DIR" -type f \
    -newer "$FLUSH_FILE" \
    ! -name ".last-flush" \
    ! -name "WARN-未记录-*" \
    ! -path "*/checkpoints/*" \
    ! -path "*/state/*" \
    2>/dev/null | head -20)
else
  # 无 .last-flush → 回退到 v0.6 行为：git 仓库下用 git status 检测 .kdev/memory/ 路径
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    PORCELAIN=$(git status --porcelain -uall 2>/dev/null | grep "\.kdev/memory/" || true)
    [ -n "$PORCELAIN" ] && CHANGED_FILES="$PORCELAIN"
  fi
fi

[ -n "$CHANGED_FILES" ] || exit 0

# 写 WARN 文件（覆盖同日旧警告，保持最新）
{
  echo "# ⚠️ 未记录警告：$TODAY"
  echo ""
  echo "会话结束时检测到：**执行日志 ($LOG_FILE) 今天无任何条目**，但 \`.kdev/memory/\` 有未落盘的变更。"
  echo ""
  echo "下次进入项目时："
  echo "1. 回忆这些变更对应的工作单元（Step），追加到 $LOG_FILE"
  echo "2. 如有关键决策/踩坑/改进信号，补记到对应的 Q/G/R 日志"
  echo "3. 补记完成后 \`touch $FLUSH_FILE\` 重置并 \`rm $WARN_FILE\`"
  echo ""
  echo "## 比 .last-flush 更新的文件"
  echo ""
  echo '```'
  echo "$CHANGED_FILES"
  echo '```'
  echo ""
  echo "_本文件由 kdev-memory SessionEnd hook (v0.7) 自动生成。_"
} > "$WARN_FILE"

exit 0
