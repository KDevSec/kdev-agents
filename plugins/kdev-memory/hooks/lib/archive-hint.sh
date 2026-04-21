#!/usr/bin/env bash
# 归档提醒逻辑：检查主文件最早条目是否跨月/跨季度
#
# 切档规则（见 SKILL.md "文件切档与归档"章节）：
#   执行日志.md   → 按月切   （执行日志-YYYY-MM.md）
#   踩坑日志.md   → 按季度切（踩坑日志-YYYYQN.md）
#   决策日志.md   → 按季度切（决策日志-YYYYQN.md）
#   改进建议.md   → 不切档
#
# 判断规则：主文件里最早一条日期 < 当月/当季 → 提醒切档
# 不用定行数阈值——用日期自然判断更直观。

# 从 YYYY-MM-DD 算季度号 YYYYQN
date_to_quarter() {
  local d="$1"
  local year="${d:0:4}"
  local month="${d:5:2}"
  # 去 leading-zero 避免被当 octal（bash < 4.0 的历史坑）
  local m=$((10#$month))
  local q=$(( (m - 1) / 3 + 1 ))
  echo "${year}Q${q}"
}

# 提取文件里最早的 `日期：YYYY-MM-DD`（按字典序，日期格式保证等价于时间序）
earliest_date_in_file() {
  local path="$1"
  [ -f "$path" ] || { echo ""; return; }
  # 用 grep + sort | head -1，不依赖 awk 数组
  grep -oE '(日期|date)[：:][ ]*[0-9]{4}-[0-9]{2}-[0-9]{2}' "$path" 2>/dev/null \
    | sed -E 's/^(日期|date)[：:][ ]*//' \
    | sort | head -n 1
}

# 检查某文件是否需要按月归档
# 返回：空=不需要；非空=提醒文本
check_monthly_archive_hint() {
  local path="$1"
  local label="$2"
  local earliest; earliest=$(earliest_date_in_file "$path")
  [ -z "$earliest" ] && return
  local earliest_month="${earliest:0:7}"  # YYYY-MM
  local current_month; current_month=$(date +%Y-%m)
  if [ "$earliest_month" != "$current_month" ]; then
    echo "${label}（最早条目 ${earliest}，跨月到 ${current_month}）→ 建议切 ${earliest_month} 及更早条目到 归档/${label%.md}-${earliest_month}.md"
  fi
}

# 检查某文件是否需要按季度归档
check_quarterly_archive_hint() {
  local path="$1"
  local label="$2"
  local earliest; earliest=$(earliest_date_in_file "$path")
  [ -z "$earliest" ] && return
  local earliest_q; earliest_q=$(date_to_quarter "$earliest")
  local today; today=$(date +%Y-%m-%d)
  local current_q; current_q=$(date_to_quarter "$today")
  if [ "$earliest_q" != "$current_q" ]; then
    echo "${label}（最早条目 ${earliest}，跨季到 ${current_q}）→ 建议切 ${earliest_q} 及更早条目到 归档/${label%.md}-${earliest_q}.md"
  fi
}

# 聚合：扫 .kdev/memory/ 三个主文件，返回归档提醒（无则空）
collect_archive_hints() {
  local kdev_dir="$1"
  local hints=""
  local line

  line=$(check_monthly_archive_hint "$kdev_dir/执行日志.md" "执行日志.md")
  [ -n "$line" ] && hints="${hints}  - ${line}\n"

  line=$(check_quarterly_archive_hint "$kdev_dir/踩坑日志.md" "踩坑日志.md")
  [ -n "$line" ] && hints="${hints}  - ${line}\n"

  line=$(check_quarterly_archive_hint "$kdev_dir/决策日志.md" "决策日志.md")
  [ -n "$line" ] && hints="${hints}  - ${line}\n"

  printf '%b' "$hints"
}
