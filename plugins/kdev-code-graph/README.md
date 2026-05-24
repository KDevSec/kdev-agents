# kdev-code-graph

> 基于 [Understand-Anything](https://github.com/Lum1104/Understand-Anything) 上游 + kdev-secure-coding 安全规范覆盖层的代码知识图谱 plugin。

## 能力

| 场景 | Skill | 一句话 |
|---|---|---|
| 建图 + 灌安全规范 | `/kdev-codegraph-build` | 调 UA `/understand` + ingestor 注入 |
| 规范 ↔ 代码追溯 | `/kdev-codegraph-trace` | "这条规范在哪实现 / 这段代码涉及哪些规范" |
| 变更安全爆炸半径 | `/kdev-codegraph-impact` | "改这段代码会影响哪些规范 / 该跑哪些回归" |
| spec ↔ code 对齐审计 | `/kdev-codegraph-spec-link` | LLM 判定每条 spec 是否实现 + 两维（实现状态+同步）报告，取代 doc-sync |

## 安装

### 推荐：在 Claude Code 内 `/plugin install`

```
/plugin marketplace add KDevSec/kdev-agents
/plugin marketplace add Lum1104/Understand-Anything
/plugin install kdev-code-graph
```

UA 上游通过 `plugin.json` 的 `dependencies` 自动连带装（声明在 `allowCrossMarketplaceDependenciesOn`），所以装 kdev-code-graph 时不用单独 `/plugin install understand-anything`。

⚠️ `/plugin` 命令在 VSCode 扩展里不可用，只在 Claude Code CLI / 桌面应用 / Web App 里可用。

**前提条件：**
- Claude Code Desktop / CLI 已安装
- Python 3.11+（ingestor 是 stdlib only，零依赖；Windows 用 `py -3 --version` 验证）
- Node.js 22+（UA 上游需要）

### 本地 clone 后用脚本一行装（macOS / Linux / Windows）

```bash
git clone https://github.com/KDevSec/kdev-agents.git
cd kdev-agents
./scripts/setup-kdev-codegraph.sh   # macOS / Linux
.\scripts\setup-kdev-codegraph.ps1  # Windows PowerShell 5.1+
```

该脚本就是把上面那三条 `claude plugin` 命令按顺序跑了一遍，没有调外部分发仓库。

### Python ingestor（零安装，dev 自测）

ingestor 是 stdlib only 的 Python 工具，通过 `${CLAUDE_PLUGIN_ROOT}/ingestor/run.py` 直接调用，**不需要 venv 也不需要 pip install**。如需跑自测：

```bash
cd plugins/kdev-code-graph
./install.sh   # 跑零安装验证 + 可选 dev venv 自测
```

## 设计原则

- **不重写代码图谱引擎** — 完全复用 UA 上游
- **对 UA 0 修改** — 安全节点用 UA `concept` + `kdev:*` tag 编码
- **Contract test 当护栏** — UA 升级会自动检测白名单变化

详见 [实施计划 v2](../../docs/skills/kdev-code-graph/2026-05-10-实施计划-v2.md)。

## 目录

- [ingestor/](ingestor/README.md) — Python 灌入器
- [tests/contract/](tests/contract/) — UA schema 兼容护栏

## 升级 UA 上游

```bash
cd plugins/kdev-code-graph
python3 -m pytest tests/contract -v
# 失败 → 节点/边白名单变 → 更新 ingestor/graph_io.py；命令名变 → 更新引用该命令的 kdev skill
```