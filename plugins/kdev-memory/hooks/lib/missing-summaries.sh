#!/usr/bin/env bash
# kdev-memory: 扫描"过去日期有条目但缺对应每日汇总"的共享库
#
# 为什么独立成 lib：Stop hook 的"今天无汇总"规则只看今天，无法覆盖跨天会话
# 场景（晚上 23:55 干到次日 01:30 不关会话 → SessionEnd 不触发 → 昨天汇总被
# 遗漏）。这个函数给 Stop 和 SessionStart hook 共用，用纯文件扫描的方式
# 发现被遗漏的过去日期。
#
# 数据源：.kdev/memory/{执行日志,决策日志,踩坑日志,改进建议}.md 里的
# "日期：YYYY-MM-DD" 行（skill 定义的标准格式，中文全角冒号）。
# 判据：日期严格早于今天 且 .kdev/memory/每日汇总/<date>.md 不存在。

# 列出缺失的过去每日汇总
# 参数：
#   $1 - .kdev/memory 目录路径（默认 .kdev/memory）
#   $2 - 今日日期 YYYY-MM-DD（默认 date +%F）
# 输出：stdout，空格分隔的 YYYY-MM-DD（升序，最多 5 个最近的）；无缺失则空输出
list_missing_past_summaries() {
  local kdev_dir="${1:-.kdev/memory}"
  local today="${2:-$(date +%F)}"

  [ -d "$kdev_dir" ] || return 0

  local dates_raw
  dates_raw=$(
    for src in "$kdev_dir/执行日志.md" "$kdev_dir/决策日志.md" \
               "$kdev_dir/踩坑日志.md" "$kdev_dir/改进建议.md"; do
      [ -f "$src" ] && grep -oE '日期：[0-9]{4}-[0-9]{2}-[0-9]{2}' "$src" 2>/dev/null
    done | sed 's/^日期：//' | sort -u
  )

  [ -z "$dates_raw" ] && return 0

  local missing=""
  while IFS= read -r d; do
    [ -z "$d" ] && continue
    # YYYY-MM-DD 在 bash [[ < ]] 下是字典序比较，对该格式与数值序一致
    if [[ "$d" < "$today" ]] && [ ! -f "$kdev_dir/每日汇总/$d.md" ]; then
      missing="$missing $d"
    fi
  done <<< "$dates_raw"

  # 去重 + 截最近 5 个（升序）
  echo "$missing" | tr ' ' '\n' | grep -v '^$' | sort -u | tail -5 | tr '\n' ' ' | sed 's/ *$//'
}
