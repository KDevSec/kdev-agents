#!/usr/bin/env bash
# kdev-code-graph 安装/校验脚本

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INGESTOR_DIR="$PLUGIN_ROOT/ingestor"

step() { printf '\n\033[1;36m▶ %s\033[0m\n' "$1"; }
ok() { printf '  \033[32m✓ %s\033[0m\n' "$1"; }
warn() { printf '  \033[33m! %s\033[0m\n' "$1"; }
err() { printf '  \033[31m✗ %s\033[0m\n' "$1"; exit 1; }

step "检查 Node.js (>= 22)"
if ! command -v node >/dev/null; then
  err "未找到 node。请安装 Node.js 22+"
fi
NODE_MAJOR=$(node -p "process.versions.node.split('.')[0]")
[ "$NODE_MAJOR" -ge 22 ] || err "Node $NODE_MAJOR < 22"
ok "node $(node --version)"

step "检查 pnpm (>= 10)"
if ! command -v pnpm >/dev/null; then
  warn "pnpm 未安装；尝试用 corepack..."
  corepack enable pnpm 2>/dev/null || err "请手动安装 pnpm"
  corepack prepare pnpm@latest --activate
fi
ok "pnpm $(pnpm --version)"

step "检查 Python (>= 3.11)"
if ! command -v python3 >/dev/null; then
  err "未找到 python3"
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
ok "python $PY_VER"

step "校验 Understand-Anything plugin 是否已安装"
UA_CACHE="$HOME/.claude/plugins/cache/understand-anything"
if [ -d "$UA_CACHE" ]; then
  ok "UA 已装"
else
  warn "UA 未装。请在 Claude Code 中："
  echo "    /plugin marketplace add Lum1104/Understand-Anything"
  echo "    /plugin install understand-anything"
fi

step "安装 kdev-ingestor (editable)"
cd "$INGESTOR_DIR"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  ok "已创建 .venv"
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet -e ".[dev]"
ok "kdev-ingestor 安装完成"

step "跑 ingestor 自测"
pytest --quiet
ok "ingestor 测试通过"

step "跑 UA contract test"
cd "$PLUGIN_ROOT"
python3 -m pytest tests/contract --quiet || warn "contract test 失败——见 _ua_adapter/SKILL.md"

step "完成"
echo "下一步：cd <project>; 在 Claude Code 中跑 /kdev-graph-build"
