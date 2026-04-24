#!/usr/bin/env bash
# migrate-v0.7.sh —— kdev-memory v0.7 软迁移
# 把已经被 git tracked 的 .kdev/ 转成本地过程目录
# - .gitignore append .kdev/（由 init-gitignore.sh 负责）
# - git rm --cached -r .kdev/（移出 index，保留历史 commit）
# - 用户手动 commit 这次改动

set -eu

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "[kdev-memory] 当前不在 git 仓库，无需迁移"
  exit 0
fi

if [ ! -d ".kdev" ]; then
  echo "[kdev-memory] 当前无 .kdev/ 目录，跳过"
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. append .gitignore
bash "$SCRIPT_DIR/init-gitignore.sh"

# 2. 查 .kdev/ 是否被 tracked
if git ls-files --error-unmatch .kdev/ >/dev/null 2>&1; then
  echo "[kdev-memory] .kdev/ 当前被 git tracked，移出 index（保留历史 commit）..."
  git rm -r --cached .kdev/ > /dev/null 2>&1
  echo "[kdev-memory] 完成。请 git diff --cached 核对，再 commit："
  echo ""
  echo "  git commit -m 'chore: .kdev/ 转为本地过程目录（kdev-memory v0.7 立场反转）'"
  echo ""
else
  echo "[kdev-memory] .kdev/ 未被 git tracked，无需迁移"
fi

echo ""
echo "[kdev-memory] v0.7 软迁移完成。docs/ 下的团队级产物保持不变。"
echo "后续沉淀过程→产物用 /kdev-memory-promote；周总结用 /kdev-memory-weekly。"
