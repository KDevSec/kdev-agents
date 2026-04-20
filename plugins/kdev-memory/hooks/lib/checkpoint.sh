#!/usr/bin/env bash
# kdev-memory checkpoint 公共库
# 被 pre-compact-check.sh 通过 source 引用
#
# 提供 checkpoint retention 逻辑，避免 .kdev/checkpoints/ 无限膨胀。

# 清理指定目录下超过 N 天的 checkpoint 文件
# 用法：prune_old_checkpoints <dir> <days>
prune_old_checkpoints() {
  local dir="$1"
  local days="${2:-7}"

  [ -d "$dir" ] || return 0

  # -mtime +N 表示最后修改时间超过 N 天
  # 只清理 .md 文件，避免误删其他
  find "$dir" -maxdepth 1 -type f -name '压缩前-*.md' -mtime "+$days" -delete 2>/dev/null || true
}
