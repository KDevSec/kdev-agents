#!/usr/bin/env bash
# kdev-code-graph one-click install script (macOS / Linux)
#
# Usage:
#   ./scripts/setup-kdev-codegraph.sh                                    # after local clone
#   curl -sSL https://raw.githubusercontent.com/KDevSec/kdev-agents/main/scripts/setup-kdev-codegraph.sh | bash
#
# Windows alternative (PowerShell):
#   iwr -useb https://raw.githubusercontent.com/KDevSec/kdev-agents/main/scripts/setup-kdev-codegraph.ps1 | iex
#
# Private repo alternative (raw URL not accessible):
#   gh repo clone KDevSec/kdev-agents --depth 1 && cd kdev-agents && ./scripts/setup-kdev-codegraph.sh
#
# Performs 3 steps:
#   1. add KDevSec/kdev-agents marketplace
#   2. add Lum1104/Understand-Anything marketplace (UA dependency)
#   3. install kdev-code-graph (UA auto-installed via plugin.json dependencies)

set -euo pipefail

step() { printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }
ok() { printf '  \033[32m✓ %s\033[0m\n' "$1"; }
warn() { printf '  \033[33m! %s\033[0m\n' "$1"; }
err() { printf '  \033[31m✗ %s\033[0m\n' "$1"; exit 1; }

step "检查 claude CLI 是否可用"
if ! command -v claude >/dev/null; then
  err "未找到 claude CLI。请先安装 Claude Code（https://claude.com/claude-code）"
fi
ok "claude $(claude --version 2>&1 | head -1)"

step "添加 KDevSec/kdev-agents marketplace"
claude plugin marketplace add KDevSec/kdev-agents
ok "kdev-agents marketplace 已添加"

step "添加 Lum1104/Understand-Anything marketplace (UA 依赖)"
claude plugin marketplace add Lum1104/Understand-Anything
ok "understand-anything marketplace 已添加"

step "安装 kdev-code-graph（UA 自动连带）"
claude plugin install kdev-code-graph
ok "kdev-code-graph 已安装"

step "完成"
echo ""
echo "下一步："
echo "  1. 重启 Claude Code 会话以加载 plugin"
echo "  2. 在目标项目下跑 /kdev-codegraph-build 建图"
echo "  3. 如需 Python ingestor（灌入安全规范），请额外跑："
echo "     cd ~/.claude/plugins/cache/kdev-agents/kdev-code-graph/<version> && ./install.sh"
