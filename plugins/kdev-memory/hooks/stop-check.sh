#!/usr/bin/env bash
# kdev-memory Stop hook
# 每次 Claude 要停下时检查 .kdev/ 状态并向 Claude 注入提醒文本
# 规则：
#   1. 项目无 .kdev/        → 静默退出
#   2. 今天无汇总            → 提醒生成
#   3. 汇总存在但源文件更新   → 提醒追加新增条目
#   4. 执行日志今天空         → 提醒实时落盘

KDEV_DIR=".kdev"
TODAY=$(date +%F)
SUMMARY_FILE="$KDEV_DIR/每日汇总/$TODAY.md"

# 1. 未启用 .kdev/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

REMINDERS=""

# 2. 今天无汇总 → 提醒生成
if [ ! -f "$SUMMARY_FILE" ]; then
  REMINDERS="${REMINDERS}[kdev-memory] 今天（$TODAY）还没有生成每日汇总。如果本轮是当日最后一次工作，请调用 kdev-memory skill 从 .kdev/ 聚合当天记录生成汇总。\n"
else
  # 3. 汇总存在 → 检查源文件是否有后续更新未并入
  STALE_SOURCES=""
  for src in "$KDEV_DIR/执行日志.md" "$KDEV_DIR/决策日志.md" "$KDEV_DIR/踩坑日志.md" "$KDEV_DIR/改进建议.md"; do
    if [ -f "$src" ] && [ "$src" -nt "$SUMMARY_FILE" ]; then
      STALE_SOURCES="$STALE_SOURCES $(basename "$src")"
    fi
  done
  if [ -n "$STALE_SOURCES" ]; then
    REMINDERS="${REMINDERS}[kdev-memory] 今天的每日汇总（$SUMMARY_FILE）生成后，这些源文件又有新活动：$STALE_SOURCES。若本轮是最后一次会话，请将新增条目追加到汇总末尾（不要覆盖已有内容）。\n"
  fi
fi

# 4. 执行日志今天空 → 提醒实时落盘
if [ -f "$KDEV_DIR/执行日志.md" ]; then
  if ! grep -q "$TODAY" "$KDEV_DIR/执行日志.md" 2>/dev/null; then
    REMINDERS="${REMINDERS}[kdev-memory] 执行日志里今天没有任何条目。如果本轮完成了工作步骤，请实时追加 Step 记录到 .kdev/执行日志.md。\n"
  fi
fi

# 有提醒则输出，无则静默
if [ -n "$REMINDERS" ]; then
  echo -e "$REMINDERS"
fi
