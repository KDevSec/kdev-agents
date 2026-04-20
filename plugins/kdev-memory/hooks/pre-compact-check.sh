#!/usr/bin/env bash
# kdev-memory PreCompact hook
# 会话即将被压缩时触发（auto 或 manual）。此时 Claude 仍有完整上下文。
#
# 设计定位：压缩是高风险事件——早期的 Step/决策/踩坑细节压缩后就丢了。
# 如果 .kdev/ 里没落盘，永远找不回。所以这个 hook 的主要价值是**写盘**，
# 不是"提醒 Claude"（压缩场景下 Claude 读提醒的概率低）。
#
# 行为：
#   1. 总是写一个 .kdev/checkpoints/压缩前-YYYY-MM-DD-HHMMSS.md
#      内容 = 今日执行/决策/踩坑/改进当前状态的原文复制 + 工作区 porcelain
#   2. 如果执行日志今天空 + 工作区有变更，checkpoint 里加"⚠️ 未落盘"显眼区块
#   3. 顺手清理 7 天前的旧 checkpoint（retention）
#   4. stdout 软提醒（bonus，不依赖 Claude 一定读到）

KDEV_DIR=".kdev"
CHECKPOINT_DIR="$KDEV_DIR/checkpoints"
TODAY=$(date +%F)
TIMESTAMP=$(date +%F-%H%M%S)

# 项目未启用 .kdev/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

# 引入公共库
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/checkpoint.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/checkpoint.sh"

# 消费 stdin（防止 hang）；PreCompact 的 trigger 字段可选用于日志
# 最多读 100KB，1 秒超时
INPUT=""
if [ ! -t 0 ]; then
  INPUT=$(timeout 1 cat 2>/dev/null || true)
fi
TRIGGER="auto"
if echo "$INPUT" | grep -q '"trigger"[[:space:]]*:[[:space:]]*"manual"'; then
  TRIGGER="manual"
fi

mkdir -p "$CHECKPOINT_DIR"
CHECKPOINT_FILE="$CHECKPOINT_DIR/压缩前-$TIMESTAMP.md"

# 判断"是否未落盘"
LOG_EMPTY_TODAY="false"
if [ -f "$KDEV_DIR/执行日志.md" ]; then
  grep -q "$TODAY" "$KDEV_DIR/执行日志.md" 2>/dev/null || LOG_EMPTY_TODAY="true"
else
  LOG_EMPTY_TODAY="true"
fi

WORKING_TREE_DIRTY=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  WORKING_TREE_DIRTY=$(git status --porcelain -uall 2>/dev/null)
fi

# 写 checkpoint
{
  echo "# 压缩前快照 — $TIMESTAMP"
  echo ""
  echo "**触发方式**：$TRIGGER （auto=自动压缩 / manual=用户 /compact）"
  echo "**生成时机**：PreCompact hook，会话即将被压缩"
  echo "**主要用途**：压缩后 Claude 上下文会丢失细节，此文件保留原始信号。"
  echo ""

  if [ "$LOG_EMPTY_TODAY" = "true" ] && [ -n "$WORKING_TREE_DIRTY" ]; then
    echo "## ⚠️ 未落盘警告"
    echo ""
    echo "**执行日志今天（$TODAY）无任何条目**，但工作区存在未提交变更。"
    echo "说明本会话的工作单元（Step）未实时落盘。请压缩后优先："
    echo ""
    echo "1. 读本文件的"工作区快照"区块"
    echo "2. 回忆对应的 Step，追加到 \`$KDEV_DIR/执行日志.md\`"
    echo "3. 补记完成后删除本 checkpoint"
    echo ""
  fi

  echo "## 工作区快照（git status --porcelain）"
  echo ""
  echo '```'
  if [ -n "$WORKING_TREE_DIRTY" ]; then
    echo "$WORKING_TREE_DIRTY"
  else
    echo "(工作区干净)"
  fi
  echo '```'
  echo ""

  for src in "执行日志.md" "决策日志.md" "踩坑日志.md" "改进建议.md" "当前状态.md"; do
    srcfile="$KDEV_DIR/$src"
    if [ -f "$srcfile" ]; then
      echo "## 📋 $src 原文（压缩前快照）"
      echo ""
      echo '```markdown'
      cat "$srcfile"
      echo '```'
      echo ""
    fi
  done

  todayfile="$KDEV_DIR/每日汇总/$TODAY.md"
  if [ -f "$todayfile" ]; then
    echo "## 📅 今日汇总（$TODAY）原文"
    echo ""
    echo '```markdown'
    cat "$todayfile"
    echo '```'
    echo ""
  fi

  echo "---"
  echo ""
  echo "_本文件由 kdev-memory PreCompact hook 自动生成。_"
  echo "_retention：7 天后自动清理，如需长期保留请手工 mv 出 checkpoints/ 目录。_"
} > "$CHECKPOINT_FILE"

# retention：清理 7 天前的 checkpoint
prune_old_checkpoints "$CHECKPOINT_DIR" 7

# 软提醒（bonus）
echo "[kdev-memory] 会话即将压缩。已写 checkpoint：$CHECKPOINT_FILE"
echo "[kdev-memory] 压缩后若需回忆细节，可 Read 此文件。如本会话有 Step/决策/踩坑未落盘，请**现在就**追加到 .kdev/ 对应文件。"

exit 0
