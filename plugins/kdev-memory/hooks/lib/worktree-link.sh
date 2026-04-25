#!/usr/bin/env bash
# worktree-link.sh —— kdev-memory v0.7.1
# secondary worktree 启动时自动 symlink .kdev → 主 worktree 的 .kdev/
# 让所有 worktree 共享同一份记忆（单一真相源）。
#
# 平台兼容：
#   - Linux / macOS：ln -s
#   - Windows (git-bash / MSYS)：cmd //c mklink /J（NTFS junction，目录链接，无需管理员权限）
#
# 跳过条件：当前是主 worktree / 本地已有 .kdev/ / 主 worktree 也无 .kdev/

worktree_link_kdev() {
  command -v git >/dev/null 2>&1 || return 0
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0

  local common_dir cur_dir
  common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || return 0
  cur_dir=$(git rev-parse --git-dir 2>/dev/null) || return 0

  # 路径正规化（容忍相对/绝对差异）
  local common_real cur_real
  common_real=$(cd "$common_dir" 2>/dev/null && pwd) || common_real="$common_dir"
  cur_real=$(cd "$cur_dir" 2>/dev/null && pwd) || cur_real="$cur_dir"

  # 主 worktree：common == cur，跳过
  [ "$common_real" = "$cur_real" ] && return 0

  # 已有本地 .kdev/（包括已是 symlink/junction）→ 幂等跳过
  [ -e .kdev ] && return 0

  # 主 worktree 根目录 = 主 .git 的父目录
  local main_root
  main_root=$(dirname "$common_real")
  [ -d "$main_root/.kdev" ] || return 0  # 主 worktree 也没 .kdev → 不强建

  case "$(uname -s 2>/dev/null)" in
    Linux*|Darwin*|FreeBSD*)
      if ln -s "$main_root/.kdev" .kdev 2>/dev/null; then
        echo "[kdev-memory] secondary worktree → 已自动 symlink .kdev → $main_root/.kdev"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      # Git-Bash on Windows：用 NTFS junction（目录连接），无需管理员权限
      local target_win main_win
      if command -v cygpath >/dev/null 2>&1; then
        target_win=$(cygpath -w "$(pwd)/.kdev" 2>/dev/null)
        main_win=$(cygpath -w "$main_root/.kdev" 2>/dev/null)
      else
        target_win="$(pwd)/.kdev"
        main_win="$main_root/.kdev"
      fi
      if cmd //c "mklink /J \"$target_win\" \"$main_win\"" >/dev/null 2>&1; then
        echo "[kdev-memory] secondary worktree → 已自动 junction .kdev → $main_root/.kdev"
      else
        echo "[kdev-memory] WARN: 创建 worktree junction 失败（Windows）"
        echo "  手动方案：cmd /c mklink /J \"$target_win\" \"$main_win\""
      fi
      ;;
    *)
      echo "[kdev-memory] 未识别平台 $(uname -s 2>/dev/null)，跳过 worktree 自动 link"
      ;;
  esac
}
