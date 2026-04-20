#!/usr/bin/env bash
# kdev-memory frontmatter 解析公共库
# 被 session-start-brief.sh 通过 source 引用
#
# 从 .kdev/当前状态.md 的 YAML frontmatter 提取结构化字段：
#   phase / iteration / current_step / last_updated / pending_decisions / unresolved_gotchas
#
# 实现选择：优先 python3（稳）；降级到纯 bash 简单解析（不保证完整 YAML 合规）。

# 读 .kdev/当前状态.md 的 frontmatter 字段
# 用法：read_state_field <field_name>
# 若文件不存在 / 无 frontmatter / 字段缺失 → 返回空字符串
read_state_field() {
  local field="$1"
  local state_file=".kdev/当前状态.md"

  [ -f "$state_file" ] || { echo ""; return 0; }

  # 优先 python3（处理 list / multiline 更稳）
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$state_file" "$field" <<'PYEOF' 2>/dev/null || echo ""
import sys, re
path, field = sys.argv[1], sys.argv[2]
try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not m:
        sys.exit(0)
    fm = m.group(1)
    for line in fm.split('\n'):
        line = line.rstrip()
        if line.startswith(f'{field}:'):
            val = line[len(field)+1:].strip()
            # 去两端引号
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            print(val)
            sys.exit(0)
except Exception:
    pass
PYEOF
    return 0
  fi

  # bash fallback：只能处理单行标量字段
  awk -v f="$field" '
    BEGIN { in_fm = 0; line = 0 }
    /^---$/ {
      line++
      if (line == 1) { in_fm = 1; next }
      if (line == 2) { exit }
    }
    in_fm && $0 ~ "^"f":" {
      val = substr($0, length(f) + 2)
      sub(/^[[:space:]]+/, "", val)
      sub(/[[:space:]]+$/, "", val)
      gsub(/^"|"$/, "", val)
      gsub(/^'"'"'|'"'"'$/, "", val)
      print val
      exit
    }
  ' "$state_file"
}

# 判断 .kdev/当前状态.md 是否带 frontmatter
has_state_frontmatter() {
  local state_file=".kdev/当前状态.md"
  [ -f "$state_file" ] || return 1
  head -1 "$state_file" | grep -q '^---$'
}
