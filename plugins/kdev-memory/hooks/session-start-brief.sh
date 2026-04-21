#!/usr/bin/env bash
# kdev-memory SessionStart hook
# 新会话启动时向 Claude 注入 .kdev/memory/ 当前状态摘要，让 Claude 一开局就知道
# 项目记忆在哪、有哪些待处理事项（WARN / checkpoint / 待决策等）。
#
# 额外职责：这是所有 hook 里最早被触发的（按会话时序），承担"自动迁移 0.2.0 → 0.3.0
# 目录结构"的主入口——旧结构的老项目升级到 0.3.0 后，第一次开会话就自动搬家。
#
# 输出格式：JSON，使用 hookSpecificOutput.additionalContext 结构化注入。
# Claude Code 会把 additionalContext 作为 SessionStart 的初始上下文读到。
#
# source 分档：
#   - startup / clear：完整摘要（~8-12 行）
#   - resume：精简到 2-3 行（Claude 已有上下文，不重复注入）
#   - compact：提醒 checkpoint 在哪，不重复注入旧内容

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/migrate.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/migrate.sh"
# shellcheck source=lib/frontmatter.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/frontmatter.sh"
# shellcheck source=lib/missing-summaries.sh
# shellcheck disable=SC1091
. "$SCRIPT_DIR/lib/missing-summaries.sh"

# 自动迁移（如果是 0.2.0 升级过来的老项目，这里完成搬家）
kdev_memory_migrate

KDEV_DIR=".kdev/memory"
TODAY=$(date +%F)

# 项目未启用 .kdev/memory/ → 静默（输出 suppressOutput，不注入任何内容）
if [ ! -d "$KDEV_DIR" ]; then
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
fi

# 消费 stdin 拿 source（防 hang，1 秒超时）
SOURCE="startup"
if [ ! -t 0 ]; then
  INPUT=$(timeout 1 cat 2>/dev/null || true)
  if [ -n "$INPUT" ] && command -v python3 >/dev/null 2>&1; then
    PARSED=$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
    d = json.load(sys.stdin)
    print(d.get("source") or "startup")
except Exception:
    print("startup")
' 2>/dev/null)
    [ -n "$PARSED" ] && SOURCE="$PARSED"
  fi
fi

# ===== 收集待处理事项 =====
WARN_FILES=""
if compgen -G "$KDEV_DIR/WARN-*.md" > /dev/null 2>&1; then
  WARN_FILES=$(ls -1 "$KDEV_DIR"/WARN-*.md 2>/dev/null | head -5)
fi

CHECKPOINT_FILES=""
if [ -d "$KDEV_DIR/checkpoints" ]; then
  CHECKPOINT_FILES=$(ls -1t "$KDEV_DIR/checkpoints"/压缩前-*.md 2>/dev/null | head -3)
fi

# ===== 收集今日进度 =====
LOG_TODAY="空"
if [ -f "$KDEV_DIR/执行日志.md" ] && grep -q "$TODAY" "$KDEV_DIR/执行日志.md" 2>/dev/null; then
  LOG_TODAY=$(grep -c "^## Step " "$KDEV_DIR/执行日志.md" 2>/dev/null || echo "有")
  LOG_TODAY="今日有 $LOG_TODAY 条 Step（含历史）"
fi

SUMMARY_TODAY_STATUS="未生成"
[ -f "$KDEV_DIR/每日汇总/$TODAY.md" ] && SUMMARY_TODAY_STATUS="已生成"

# 过去日期有条目但缺每日汇总（跨天会话遗漏的兜底）
MISSING_PAST_SUMMARIES=$(list_missing_past_summaries "$KDEV_DIR" "$TODAY")

# ===== 读当前状态 frontmatter =====
STATE_PHASE=$(read_state_field "phase")
STATE_ITERATION=$(read_state_field "iteration")
STATE_CURRENT_STEP=$(read_state_field "current_step")
STATE_LAST_UPDATED=$(read_state_field "last_updated")
STATE_PENDING=$(read_state_field "pending_decisions")
STATE_UNRESOLVED=$(read_state_field "unresolved_gotchas")

# ===== 最近 Step / Q / G（从文件尾部提取）=====
RECENT_STEP=""
if [ -f "$KDEV_DIR/执行日志.md" ]; then
  RECENT_STEP=$(grep "^## Step " "$KDEV_DIR/执行日志.md" 2>/dev/null | tail -1)
fi
RECENT_Q=""
if [ -f "$KDEV_DIR/决策日志.md" ]; then
  RECENT_Q=$(grep "^## Q-" "$KDEV_DIR/决策日志.md" 2>/dev/null | tail -1)
fi
RECENT_G=""
if [ -f "$KDEV_DIR/踩坑日志.md" ]; then
  RECENT_G=$(grep "^## G-" "$KDEV_DIR/踩坑日志.md" 2>/dev/null | tail -1)
fi

# ===== 按 source 分档拼 brief =====
build_brief() {
  local mode="$1"
  local brief=""

  case "$mode" in
    resume)
      brief+="项目有 .kdev/ 工程记忆。本次会话是 resume（Claude 已有前文上下文）。\n"
      if [ -n "$WARN_FILES" ] || [ -n "$CHECKPOINT_FILES" ] || [ -n "$MISSING_PAST_SUMMARIES" ]; then
        brief+="⚠️ 待处理：\n"
        [ -n "$WARN_FILES" ] && brief+="- WARN 文件：\n$(echo "$WARN_FILES" | sed 's|^|  - |')\n"
        [ -n "$CHECKPOINT_FILES" ] && brief+="- Checkpoint 文件：\n$(echo "$CHECKPOINT_FILES" | sed 's|^|  - |')\n"
        [ -n "$MISSING_PAST_SUMMARIES" ] && brief+="- 缺失的过去每日汇总（跨天会话遗漏）：$MISSING_PAST_SUMMARIES\n"
      fi
      ;;

    compact)
      brief+="项目有 .kdev/ 工程记忆。刚从压缩中恢复。\n"
      if [ -n "$CHECKPOINT_FILES" ]; then
        brief+="📦 压缩前 checkpoint（可回读细节）：\n"
        brief+="$(echo "$CHECKPOINT_FILES" | sed 's|^|  - |')\n"
      fi
      [ -n "$WARN_FILES" ] && brief+="⚠️ 未处理的 WARN：\n$(echo "$WARN_FILES" | sed 's|^|  - |')\n"
      [ -n "$MISSING_PAST_SUMMARIES" ] && brief+="⚠️ 缺失的过去每日汇总：$MISSING_PAST_SUMMARIES\n"
      ;;

    *)
      # startup / clear / 默认
      brief+="项目有 .kdev/ 工程记忆。当前状态（$TODAY）：\n\n"

      if [ -n "$WARN_FILES" ] || [ -n "$CHECKPOINT_FILES" ] || [ -n "$MISSING_PAST_SUMMARIES" ]; then
        brief+="⚠️ **待处理（优先看）**：\n"
        [ -n "$WARN_FILES" ] && brief+="$(echo "$WARN_FILES" | sed 's|^|- |')\n"
        [ -n "$CHECKPOINT_FILES" ] && brief+="$(echo "$CHECKPOINT_FILES" | sed 's|^|- |')\n"
        [ -n "$MISSING_PAST_SUMMARIES" ] && brief+="- 过去日期缺每日汇总（跨天会话遗漏）：$MISSING_PAST_SUMMARIES —— 请调用 kdev-memory skill 按日聚合源文件补写，严禁回翻会话上下文\n"
        brief+="\n"
      fi

      brief+="📊 **今日进度**：\n"
      brief+="- 执行日志：$LOG_TODAY\n"
      brief+="- 每日汇总：$SUMMARY_TODAY_STATUS\n"

      if [ -n "$STATE_PHASE" ] || [ -n "$STATE_ITERATION" ] || [ -n "$STATE_CURRENT_STEP" ]; then
        brief+="\n🎯 **项目状态（来自 当前状态.md frontmatter）**：\n"
        [ -n "$STATE_PHASE" ] && brief+="- phase: $STATE_PHASE\n"
        [ -n "$STATE_ITERATION" ] && brief+="- iteration: $STATE_ITERATION\n"
        [ -n "$STATE_CURRENT_STEP" ] && brief+="- current_step: $STATE_CURRENT_STEP\n"
        [ -n "$STATE_LAST_UPDATED" ] && brief+="- last_updated: $STATE_LAST_UPDATED\n"
        [ -n "$STATE_PENDING" ] && brief+="- pending_decisions: $STATE_PENDING\n"
        [ -n "$STATE_UNRESOLVED" ] && brief+="- unresolved_gotchas: $STATE_UNRESOLVED\n"
      fi

      if [ -n "$RECENT_STEP" ] || [ -n "$RECENT_Q" ] || [ -n "$RECENT_G" ]; then
        brief+="\n📝 **最近条目**：\n"
        [ -n "$RECENT_STEP" ] && brief+="- $RECENT_STEP\n"
        [ -n "$RECENT_Q" ] && brief+="- $RECENT_Q\n"
        [ -n "$RECENT_G" ] && brief+="- $RECENT_G\n"
      fi

      brief+="\n💡 **建议**：如需详细上下文，Read .kdev/memory/当前状态.md 和最近的 .kdev/memory/每日汇总/*.md。"
      ;;
  esac

  printf '%b' "$brief"
}

BRIEF=$(build_brief "$SOURCE")

if [ -z "$BRIEF" ]; then
  echo '{"continue":true,"suppressOutput":true}'
  exit 0
fi

# 包进 <kdev-memory-brief> tag，用 JSON 结构化注入
FULL="<kdev-memory-brief>
$BRIEF
</kdev-memory-brief>"

# 用 python3 组装 JSON（避免 shell 转义字符串里的换行 / 双引号问题）
if command -v python3 >/dev/null 2>&1; then
  python3 - "$FULL" <<'PYEOF'
import sys, json
ctx = sys.argv[1]
print(json.dumps({
    "continue": True,
    "suppressOutput": True,
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": ctx,
    },
}, ensure_ascii=False))
PYEOF
else
  # 没 python3 的降级：直接 stdout 裸打印（Claude 也能看到，只是不结构化）
  echo "$FULL"
fi

exit 0
