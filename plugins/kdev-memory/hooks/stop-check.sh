#!/usr/bin/env bash
# kdev-memory Stop hook
# 每次 Claude 要停下时检查 .kdev/ 状态并向 Claude 注入提醒文本
#
# 四条软提醒规则（stdout，exit 0）：
#   1. 项目无 .kdev/        → 静默退出
#   2. 今天无汇总            → 提醒生成
#   3. 汇总存在但源文件更新   → 提醒追加新增条目
#   4. 执行日志今天空         → 提醒实时落盘
#
# 阻塞规则（stderr，exit 2）—— 仅当 .kdev/strict 开关存在时启用：
#   执行日志今天空 + 工作区有变更 + (变更文件 ≥ 2 OR 命中里程碑白名单)
#   → 阻止 Stop，强制 Claude 落盘后才能真正结束
#
# 里程碑白名单：specs/**/*.md、specs/**/contracts/*.{yml,yaml}、.kdev/方法论铁规.md

KDEV_DIR=".kdev"
TODAY=$(date +%F)
SUMMARY_FILE="$KDEV_DIR/每日汇总/$TODAY.md"

# 引入里程碑白名单（单一真相源）
# shellcheck source=lib/milestone.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/milestone.sh"

# 1. 未启用 .kdev/ → 静默
[ -d "$KDEV_DIR" ] || exit 0

# 读 hook 输入的 JSON，拿 stop_hook_active（避免阻塞后无限循环）
# 注意：stdin 必须带超时，否则管道未 EOF 会永久 hang（OMC issue #240 同类问题）
STOP_HOOK_ACTIVE="false"
if [ ! -t 0 ]; then
  INPUT=$(timeout 1 cat 2>/dev/null || true)
  if echo "$INPUT" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
    STOP_HOOK_ACTIVE="true"
  fi
fi

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
LOG_EMPTY_TODAY="false"
if [ -f "$KDEV_DIR/执行日志.md" ]; then
  if ! grep -q "$TODAY" "$KDEV_DIR/执行日志.md" 2>/dev/null; then
    LOG_EMPTY_TODAY="true"
    REMINDERS="${REMINDERS}[kdev-memory] 执行日志里今天没有任何条目。如果本轮完成了工作步骤，请实时追加 Step 记录到 .kdev/执行日志.md。\n"
  fi
fi

# -------- 严格模式：条件性阻塞（exit 2） --------
# 仅当项目显式 touch .kdev/strict 才启用；已在 stop_hook_active 下就跳过，避免无限循环
if [ "$STOP_HOOK_ACTIVE" = "false" ] && [ -f "$KDEV_DIR/strict" ] && [ "$LOG_EMPTY_TODAY" = "true" ]; then
  # 工作区 porcelain 输出
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    # -u 展开未跟踪目录，避免 "specs/" 折叠形态漏过白名单匹配
    PORCELAIN=$(git status --porcelain -uall 2>/dev/null)
    if [ -n "$PORCELAIN" ]; then
      # 遍历一次：统计"实质变更"数量（排除 .kdev/ 内部的自维护文件）
      # 并检测里程碑白名单命中
      SUBSTANTIVE_COUNT=0
      MILESTONE_HIT="no"
      while IFS= read -r line; do
        [ -z "$line" ] && continue
        # porcelain 格式："XY path" 或 "XY path -> newpath"（rename）
        path="${line:3}"
        path="${path##*-> }"  # rename 取 newpath
        # 去 porcelain 对含空格路径加的引号
        path="${path#\"}"; path="${path%\"}"

        # .kdev/ 内部变更通常不计入"实质工作"（避免 touch .kdev/strict 自触发）
        # 例外：.kdev/方法论铁规.md 是里程碑（由白名单函数决定）
        case "$path" in
          .kdev/*)
            if is_milestone_path "$path"; then
              MILESTONE_HIT="yes"
              SUBSTANTIVE_COUNT=$((SUBSTANTIVE_COUNT + 1))
            fi
            ;;
          *)
            SUBSTANTIVE_COUNT=$((SUBSTANTIVE_COUNT + 1))
            if is_milestone_path "$path"; then
              MILESTONE_HIT="yes"
            fi
            ;;
        esac
      done <<< "$PORCELAIN"

      if [ "$SUBSTANTIVE_COUNT" -ge 2 ] || [ "$MILESTONE_HIT" = "yes" ]; then
        CHANGE_COUNT="$SUBSTANTIVE_COUNT"
        {
          echo "[kdev-memory/strict] 检测到 .kdev/执行日志.md 今天无任何条目，但工作区有 $CHANGE_COUNT 处未提交变更（命中里程碑=$MILESTONE_HIT）。"
          echo "请先追加至少一条 Step 记录到 .kdev/执行日志.md（说明今天完成了哪些工作单元、产出物路径、模型自评），再结束本轮。"
          echo "如需临时关闭严格模式：rm .kdev/strict"
        } >&2
        exit 2
      fi
    fi
  fi
fi

# 有提醒则输出，无则静默
if [ -n "$REMINDERS" ]; then
  echo -e "$REMINDERS"
fi
