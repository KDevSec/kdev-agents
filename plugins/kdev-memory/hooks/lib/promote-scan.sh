#!/usr/bin/env bash
# promote-scan.sh —— kdev-memory v0.7
# 扫描 .kdev/memory/ 的沉淀候选，输出 Brief P1 hint（或 P0 当距 .last-promote > 30 天）
# 约束：
#   - 无 python3 依赖（纯 shell + grep/awk）
#   - 幂等、只读（不写任何文件）
#   - 返回文本：P1 hint（"📝 建议沉淀：..."）或空字符串

# shellcheck disable=SC2155

scan_promote_candidates() {
  local kdev_dir="$1"
  local today="$2"
  [ -d "$kdev_dir" ] || return 0

  local flush="$kdev_dir/.last-promote"
  local days_since_promote="never"
  local flush_ts=0
  local today_ts
  # Use end-of-day so day-boundary arithmetic is inclusive of today's full 24 hours
  today_ts=$(date -d "$today 23:59:59" +%s 2>/dev/null || date +%s)

  if [ -f "$flush" ]; then
    flush_ts=$(stat -c %Y "$flush" 2>/dev/null || stat -f %m "$flush" 2>/dev/null)
    if [ -n "$flush_ts" ] && [ "$flush_ts" -gt 0 ]; then
      days_since_promote=$(( (today_ts - flush_ts) / 86400 ))
    fi
  fi

  # 统计 pending 条目
  # 粗口径：改进建议里的 ## R-/## 建议 N/## #N 条目数 - 已标 promote_status: done 条目数
  local improvements_md="$kdev_dir/改进建议.md"
  local rule_md="$kdev_dir/conventions.md"
  local gotchas_md="$kdev_dir/踩坑日志.md"

  local r_total=0 r_done=0 r_pending=0
  if [ -f "$improvements_md" ]; then
    r_total=$(grep -c "^## " "$improvements_md" 2>/dev/null; true)
    r_done=$(grep -c "^promote_status:[[:space:]]*done" "$improvements_md" 2>/dev/null; true)
    r_total=${r_total:-0}
    r_done=${r_done:-0}
    r_pending=$(( r_total - r_done ))
  fi

  # conventions R-NNN（若存在）
  local rule_pending=0
  if [ -f "$rule_md" ]; then
    local rule_total rule_done
    rule_total=$(grep -c "^### R-[0-9]" "$rule_md" 2>/dev/null; true)
    rule_done=$(grep -c "^promote_status:[[:space:]]*done" "$rule_md" 2>/dev/null; true)
    rule_total=${rule_total:-0}
    rule_done=${rule_done:-0}
    rule_pending=$(( rule_total - rule_done ))
  fi

  # G-NNN
  local g_pending=0
  if [ -f "$gotchas_md" ]; then
    local g_total g_done
    g_total=$(grep -c "^## G-" "$gotchas_md" 2>/dev/null; true)
    g_done=$(grep -c "^promote_status:[[:space:]]*done" "$gotchas_md" 2>/dev/null; true)
    g_total=${g_total:-0}
    g_done=${g_done:-0}
    g_pending=$(( g_total - g_done ))
  fi

  # 触发条件（任一命中）
  local trigger_reason=""
  local escalate_p0="no"

  # 时间触发
  if [ "$days_since_promote" != "never" ] && [ "$days_since_promote" -gt 7 ]; then
    trigger_reason="距上次沉淀 $days_since_promote 天"
    if [ "$days_since_promote" -gt 30 ]; then
      escalate_p0="yes"
    fi
  fi

  # 增量触发
  if [ "$r_pending" -ge 3 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}改进建议 $r_pending 条 pending"
  fi
  if [ "$rule_pending" -ge 2 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}R-NNN 规则 $rule_pending 条 pending"
  fi
  if [ "$g_pending" -ge 5 ]; then
    trigger_reason="${trigger_reason:+$trigger_reason；}踩坑 $g_pending 条 pending"
  fi

  [ -z "$trigger_reason" ] && return 0
  [ "$r_pending" -eq 0 ] && [ "$rule_pending" -eq 0 ] && [ "$g_pending" -eq 0 ] && return 0

  # 输出 P1 hint（或 P0 升级版）
  if [ "$escalate_p0" = "yes" ]; then
    cat <<EOF
  - 🔴 长期未沉淀（$days_since_promote 天）：团队已长期未获本项目过程结晶
    · 改进建议 pending: $r_pending；R-NNN: $rule_pending；G-NNN: $g_pending
    · 执行 /kdev-memory-promote 查看沉淀候选并更新 .last-promote
EOF
  else
    cat <<EOF
  - 📝 建议沉淀（$trigger_reason）：
    · 执行 /kdev-memory-promote 查看沉淀候选并写入 docs/ 产物通道
EOF
  fi
}
