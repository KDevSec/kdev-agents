#!/usr/bin/env bash
# kdev-memory 自动迁移：.kdev/* → .kdev/memory/*
#
# v0.3.0 目录结构重构：所有 kdev-memory 产物搬到 .kdev/memory/ 子目录，
# 给 .kdev/ 根目录腾出来作为插件命名空间（未来其他插件可建自己的子目录，
# 如 .kdev/commit/、.kdev/triggers/ 等）。
#
# 调用时机：每个 hook 启动时调一次 kdev_memory_migrate，O(1) 检查，
# 已迁移直接返回。对新项目也做正确的事（只建目录，不搬文件）。

# 执行迁移（幂等）
# 返回值：总是 0（迁移是"尽力而为"，失败不阻断 hook）
kdev_memory_migrate() {
  local kdev_dir=".kdev"
  local new_dir=".kdev/memory"

  # 无 .kdev/ 目录 → 无需迁移（未启用工程记忆）
  [ -d "$kdev_dir" ] || return 0

  # 已有 .kdev/memory/ → 已迁移，直接返回（热路径，必须快）
  [ -d "$new_dir" ] && return 0

  # 检测是否存在 0.2.0 遗留文件
  local has_legacy=false
  local marker
  for marker in "执行日志.md" "决策日志.md" "踩坑日志.md" "当前状态.md" \
                "每日汇总" "方法论铁规.md" "改进建议.md" "strict" "checkpoints"; do
    if [ -e "$kdev_dir/$marker" ]; then
      has_legacy=true
      break
    fi
  done

  # WARN 文件也算遗留
  if ! $has_legacy; then
    if compgen -G "$kdev_dir/WARN-*.md" > /dev/null 2>&1; then
      has_legacy=true
    fi
  fi

  # 无遗留 → 只创建新目录，不搬文件
  if ! $has_legacy; then
    mkdir -p "$new_dir" 2>/dev/null || true
    return 0
  fi

  # ===== 执行迁移 =====
  mkdir -p "$new_dir" 2>/dev/null || {
    # 创建目录失败 → 放弃迁移，fallback 到双轨模式（后续 hook 应能处理）
    return 0
  }

  # 搬移列表
  local migrated=()
  local failed=()
  local item

  for item in "当前状态.md" "决策日志.md" "踩坑日志.md" "执行日志.md" \
              "每日汇总" "改进建议.md" "方法论铁规.md" "strict" "checkpoints"; do
    if [ -e "$kdev_dir/$item" ]; then
      if mv "$kdev_dir/$item" "$new_dir/$item" 2>/dev/null; then
        migrated+=("$item")
      else
        failed+=("$item")
      fi
    fi
  done

  # WARN-*.md 单独用 glob 处理
  local warn
  for warn in "$kdev_dir"/WARN-*.md; do
    [ -e "$warn" ] || continue
    local basename
    basename=$(basename "$warn")
    if mv "$warn" "$new_dir/$basename" 2>/dev/null; then
      migrated+=("$basename")
    else
      failed+=("$basename")
    fi
  done

  # 写迁移说明文件到 .kdev/ 根（不进 memory/，让用户一眼看见）
  local today
  today=$(date +%F)
  local migrated_file="$kdev_dir/MIGRATED-$today.md"

  {
    echo "# kdev-memory 目录结构迁移：$today"
    echo ""
    echo "v0.3.0 把所有 kdev-memory 产物迁到 \`.kdev/memory/\` 子目录。"
    echo ""
    echo "**为什么**：\`.kdev/\` 根目录变成插件命名空间。未来其他插件"
    echo "（kdev-commit、kdev-triggers 等）可以建自己的子目录，互不干扰。"
    echo ""
    echo "## 已迁移"
    echo ""
    if [ ${#migrated[@]} -gt 0 ]; then
      for item in "${migrated[@]}"; do
        echo "- \`.kdev/$item\` → \`.kdev/memory/$item\`"
      done
    else
      echo "_（本次无文件搬移，只建了目录）_"
    fi
    if [ ${#failed[@]} -gt 0 ]; then
      echo ""
      echo "## ⚠️ 迁移失败（保持原位置，请手动处理）"
      echo ""
      for item in "${failed[@]}"; do
        echo "- \`.kdev/$item\`（权限不足或路径冲突）"
      done
      echo ""
      echo "如果你看到这段，说明上面这几个文件没搬成。可手工 \`mv\` 过去，或向插件作者反馈。"
    fi
    echo ""
    echo "---"
    echo ""
    echo "本文件由 kdev-memory migrate hook 自动生成。处理完可随时删除。"
  } > "$migrated_file"

  return 0
}
