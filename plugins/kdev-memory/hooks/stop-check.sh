#!/usr/bin/env bash
# kdev-memory Stop hook
# 每次 Claude 要停下时检查：项目是否启用 .kdev/ + 今天是否已有每日汇总
# 输出文本会被注入 Claude 上下文，提醒它落盘

KDEV_DIR=".kdev"
TODAY=$(date +%F)
SUMMARY_FILE="$KDEV_DIR/每日汇总/$TODAY.md"

# 不在启用 .kdev/ 的项目里则静默退出
[ -d "$KDEV_DIR" ] || exit 0

REMINDERS=""

# 检查今天是否有每日汇总
if [ ! -f "$SUMMARY_FILE" ]; then
  REMINDERS="${REMINDERS}[kdev-memory] 今天（$TODAY）还没有生成每日汇总。如果本轮是当日最后一次工作，请调用 kdev-memory skill 从 .kdev/ 聚合当天记录生成汇总。\n"
fi

# 检查执行日志今天是否有新条目（粗略判断：文件里是否包含今天日期）
if [ -f "$KDEV_DIR/执行日志.md" ]; then
  if ! grep -q "$TODAY" "$KDEV_DIR/执行日志.md" 2>/dev/null; then
    REMINDERS="${REMINDERS}[kdev-memory] 执行日志里今天没有任何条目。如果本轮完成了工作步骤，请实时追加 Step 记录到 .kdev/执行日志.md。\n"
  fi
fi

# 有提醒则输出，无则静默
if [ -n "$REMINDERS" ]; then
  echo -e "$REMINDERS"
fi
