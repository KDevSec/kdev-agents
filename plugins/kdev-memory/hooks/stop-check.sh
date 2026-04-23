#!/usr/bin/env bash
# kdev-memory Stop hook
# 每次 Claude 要停下时检查 .kdev/ 状态并向 Claude 注入提醒文本
#
# 六条软提醒规则（stdout，exit 0）：
#   1. 项目无 .kdev/        → 静默退出
#   2. 今天无汇总            → 提醒生成
#   3. 汇总存在但源文件更新   → 提醒追加新增条目
#   4. 执行日志今天空         → 提醒实时落盘
#   5. 过去日期有条目但缺汇总 → 提醒补写（跨天会话遗漏的兜底）
#   6. 主文件跨月/跨季度       → 提醒归档切档
#
# 阻塞规则（stderr，exit 2）—— 仅当 .kdev/strict 开关存在时启用：
#   执行日志今天空 + 工作区有变更 + (变更文件 ≥ 2 OR 命中里程碑白名单)
#   → 阻止 Stop，强制 Claude 落盘后才能真正结束
#
# 里程碑白名单：specs/**/*.md、specs/**/contracts/*.{yml,yaml}、.kdev/方法论铁规.md

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/migrate.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/migrate.sh"
# shellcheck source=lib/milestone.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/milestone.sh"
# shellcheck source=lib/missing-summaries.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/missing-summaries.sh"
# shellcheck source=lib/archive-hint.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/archive-hint.sh"

# 防御性迁移：0.2.0 遗留结构自动搬到 .kdev/memory/（幂等，热路径快返回）
kdev_memory_migrate

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)
SUMMARY_FILE="$KDEV_DIR/每日汇总/$TODAY.md"

# 1. 未启用 .kdev/memory/ → 静默
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
  REMINDERS="${REMINDERS}[kdev-memory] 今天（$TODAY）还没有生成每日汇总。如果本轮是当日最后一次工作，请调用 kdev-memory skill 从 .kdev/memory/ 聚合当天记录生成汇总。\n"
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
    REMINDERS="${REMINDERS}[kdev-memory] 执行日志里今天没有任何条目。如果本轮完成了工作步骤，请实时追加 Step 记录到 .kdev/memory/执行日志.md。\n"
  fi
fi

# 5. 过去日期有条目但缺每日汇总 → 跨天会话遗漏的兜底提醒
MISSING_PAST=$(list_missing_past_summaries "$KDEV_DIR" "$TODAY")
if [ -n "$MISSING_PAST" ]; then
  REMINDERS="${REMINDERS}[kdev-memory] ⚠️ 过去日期在 .kdev/memory/ 源文件里有条目，但 每日汇总/<日期>.md 不存在：$MISSING_PAST。典型原因是跨天会话未关，SessionEnd 没触发。请调用 kdev-memory skill 按这些日期聚合源文件生成汇总——严禁回翻会话上下文；若某日源文件信息不足请在汇总里坦白标注。\n"
fi

# 6. 主文件最早条目跨月/跨季度 → 提醒切档归档
ARCHIVE_HINTS=$(collect_archive_hints "$KDEV_DIR")
if [ -n "$ARCHIVE_HINTS" ]; then
  REMINDERS="${REMINDERS}[kdev-memory] 📦 主文件已跨越归档边界，建议调用 kdev-memory skill 切档（将老条目迁到归档文件，主文件只留当前月/当前季）：\n${ARCHIVE_HINTS}\n切档步骤见 SKILL.md 的「文件切档与归档」章节。改进建议.md 不切档。\n"
fi

# 7. Step 完整度扫描（P1-6 落地）—— 今日新增 Step 但字段半残 → 软提醒
# 占位变量：strict 模式阻塞段会用
STEP_TODAY_HALF_COMPLETE=0
STEP_LINT_LIB="$SCRIPT_DIR/lib/step_completeness.py"
if [ -f "$KDEV_DIR/执行日志.md" ] && [ -f "$STEP_LINT_LIB" ] && command -v python3 >/dev/null 2>&1; then
  STEP_RESULT=$(KDEV_STEP_LIB="$STEP_LINT_LIB" python3 - "$KDEV_DIR/执行日志.md" "$TODAY" 2>/dev/null <<'PYEOF'
import sys, os, importlib.util
from pathlib import Path
lib = Path(os.environ["KDEV_STEP_LIB"])
spec = importlib.util.spec_from_file_location("step_completeness", lib)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
result = mod.run_check(Path(sys.argv[1]), sys.argv[2])
result["_today_iso"] = sys.argv[2]
hint = mod.format_hint_for_stop(result)
# 双输出：count + hint text（用 "|SEP|" 分隔避免 newline 冲突）
print(f"{result.get('today_half_complete', 0)}|SEP|{hint or ''}")
PYEOF
)
  if [ -n "$STEP_RESULT" ] && echo "$STEP_RESULT" | grep -q "|SEP|"; then
    STEP_TODAY_HALF_COMPLETE="${STEP_RESULT%%|SEP|*}"
    STEP_HINT_TEXT="${STEP_RESULT#*|SEP|}"
    if [ -n "$STEP_HINT_TEXT" ]; then
      REMINDERS="${REMINDERS}${STEP_HINT_TEXT}\n"
    fi
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
          echo "[kdev-memory/strict] 检测到 .kdev/memory/执行日志.md 今天无任何条目，但工作区有 $CHANGE_COUNT 处未提交变更（命中里程碑=$MILESTONE_HIT）。"
          echo "请先追加至少一条 Step 记录到 .kdev/memory/执行日志.md（说明今天完成了哪些工作单元、产出物路径、模型自评），再结束本轮。"
          echo "如需临时关闭严格模式：rm .kdev/memory/strict"
        } >&2
        exit 2
      fi
    fi
  fi
fi

# -------- 严格模式（Step 完整度）：今日半残 Step 阻塞 --------
# 单独判定：即使执行日志今天有条目（上一段不 block），但如果那些条目半残
# （用户评分空 / 扣分项空），strict 模式下也要 exit 2——补齐字段后才能结束
if [ "$STOP_HOOK_ACTIVE" = "false" ] && [ -f "$KDEV_DIR/strict" ] && [ "$STEP_TODAY_HALF_COMPLETE" -gt 0 ] 2>/dev/null; then
  {
    echo "[kdev-memory/strict] 今日新增 $STEP_TODAY_HALF_COMPLETE 条 Step 但字段半残（用户评分段时分戳空 / 扣分项空 等）。"
    echo "请当场采集用户评分 + 补扣分项，再结束本轮。长期漂移用 R-NNN 改进建议记录。"
    echo "如需临时关闭严格模式：rm .kdev/memory/strict"
  } >&2
  exit 2
fi

# 有提醒则输出，无则静默
if [ -n "$REMINDERS" ]; then
  echo -e "$REMINDERS"
fi
