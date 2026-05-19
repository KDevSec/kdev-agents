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

step "校验依赖 plugin: Understand-Anything (UA)"
UA_CACHE="$HOME/.claude/plugins/cache/understand-anything"
if [ -d "$UA_CACHE" ]; then
  ok "UA 已装"
else
  warn "UA 未装"
  echo ""
  echo "  正常情况下 UA 会作为 kdev-code-graph 的依赖自动安装"
  echo "  （通过 plugin.json dependencies + marketplace allowCrossMarketplaceDependenciesOn）"
  echo ""
  echo "  如果你是本地开发 / 未通过 /plugin install 安装，请手动加 UA marketplace："
  echo "    /plugin marketplace add Lum1104/Understand-Anything"
  echo "    /plugin install understand-anything"
fi

step "kdev-ingestor 零安装验证"
if python3 "$INGESTOR_DIR/run.py" --help >/dev/null 2>&1; then
  ok "ingestor 可零安装运行（python3 run.py ...）"
else
  err "ingestor 零安装路径失败 — 检查 $INGESTOR_DIR/run.py 是否存在"
fi

step "（可选）安装 dev venv 跑测试"
if [ -d "$INGESTOR_DIR/.venv" ]; then
  cd "$INGESTOR_DIR"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pytest --quiet
  ok "ingestor 测试通过（dev venv）"
  cd "$PLUGIN_ROOT"
else
  warn "未安装 dev venv — 生产用不需要。若需跑测试："
  echo "    cd $INGESTOR_DIR && python3 -m venv .venv && source .venv/bin/activate && pip install -e \".[dev]\" && pytest"
fi

step "跑 UA contract test"
cd "$PLUGIN_ROOT"
python3 -m pytest tests/contract --quiet || warn "contract test 失败——节点/边白名单可能已变，检查 ingestor/graph_io.py"

step "完成"
echo "下一步：cd <project>; 在 Claude Code 中跑 /kdev-codegraph-build"
