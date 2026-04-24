#!/usr/bin/env bash
# init-gitignore.sh —— kdev-memory v0.7
# 立场反转：.kdev/ 默认本地过程目录；init 时自动 append .kdev/ 到项目 .gitignore
# 环境变量 KDEV_GIT_TRACK=1 → 跳过（单人项目可选托管模式）

set -eu

if [ "${KDEV_GIT_TRACK:-0}" = "1" ]; then
  echo "[kdev-memory] KDEV_GIT_TRACK=1，跳过 .gitignore 修改（单人托管模式）"
  exit 0
fi

GITIGNORE=".gitignore"
MARK_LINE=".kdev/"
MARK_COMMENT="# kdev-memory v0.7: 本地过程目录，不 git 托管（产物请沉淀到 docs/）"

if [ ! -f "$GITIGNORE" ]; then
  {
    echo "$MARK_COMMENT"
    echo "$MARK_LINE"
  } > "$GITIGNORE"
  echo "[kdev-memory] 新建 .gitignore 并加入 $MARK_LINE"
  exit 0
fi

# 已有 .gitignore：只在缺 .kdev/ 行时追加（幂等）
if grep -qxF "$MARK_LINE" "$GITIGNORE"; then
  echo "[kdev-memory] .gitignore 已有 $MARK_LINE，跳过"
  exit 0
fi

{
  echo ""
  echo "$MARK_COMMENT"
  echo "$MARK_LINE"
} >> "$GITIGNORE"
echo "[kdev-memory] 追加 $MARK_LINE 到 .gitignore"
exit 0
