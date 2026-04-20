#!/usr/bin/env bash
# kdev-memory SessionEnd hook
# 会话真正结束时的兜底：若今天 .kdev/执行日志.md 无条目但工作区有变更
# → 写一个显眼的 .kdev/WARN-未记录-YYYY-MM-DD.md 文件，列出当天被动过的文件
# 下次打开项目时，CLAUDE.md 触发规则段会让 Claude 看到 WARN-* 并提醒用户补记

KDEV_DIR=".kdev"
TODAY=$(date +%F)
LOG_FILE="$KDEV_DIR/执行日志.md"
WARN_FILE="$KDEV_DIR/WARN-未记录-$TODAY.md"

# 项目未启用 .kdev/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

# 执行日志今天已有条目 → 无需警告
if [ -f "$LOG_FILE" ] && grep -q "$TODAY" "$LOG_FILE" 2>/dev/null; then
  exit 0
fi

# 没有 git 仓库 → 无法判断变更，静默
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || exit 0

PORCELAIN=$(git status --porcelain -uall 2>/dev/null)
[ -n "$PORCELAIN" ] || exit 0

# 写 WARN 文件（覆盖同日旧警告，保持最新）
{
  echo "# ⚠️ 未记录警告：$TODAY"
  echo ""
  echo "会话结束时检测到：**执行日志 ($LOG_FILE) 今天无任何条目**，但工作区存在以下未提交变更。"
  echo ""
  echo "说明今天的工作未被实时落盘到工程记忆。请在下次进入项目时："
  echo ""
  echo "1. 回忆这些变更对应的工作单元（Step），追加到 $LOG_FILE"
  echo "2. 如有关键决策/踩坑/改进信号，补记到对应的 Q/G/R 日志"
  echo "3. 补记完成后删除本文件（\`rm $WARN_FILE\`）"
  echo ""
  echo "## 会话结束时的工作区变更快照"
  echo ""
  echo '```'
  echo "$PORCELAIN"
  echo '```'
  echo ""
  echo "_本文件由 kdev-memory SessionEnd hook 自动生成。_"
} > "$WARN_FILE"

exit 0
