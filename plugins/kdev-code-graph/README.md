# kdev-code-graph

> 基于 [Understand-Anything](https://github.com/Lum1104/Understand-Anything) 上游 + kdev-secure-coding 安全规范覆盖层的代码知识图谱 plugin。

## 能力

| 场景 | Skill | 一句话 |
|---|---|---|
| 建图 + 灌安全规范 | `/kdev-codegraph-build` | 调 UA `/understand` + ingestor 注入 |
| 规范 ↔ 代码追溯 | `/kdev-codegraph-trace` | "这条规范在哪实现 / 这段代码涉及哪些规范" |
| 变更安全爆炸半径 | `/kdev-codegraph-impact` | "改这段代码会影响哪些规范 / 该跑哪些回归" |
| 文档代码同步审计 | `/kdev-codegraph-doc-sync` | 四级状态报告（同步/需更新/缺实现/缺文档） |

## 安装

### 一键安装（推荐）

```bash
curl -sSL https://raw.githubusercontent.com/KDevSec/kdev-agents/main/scripts/setup-kdev-codegraph.sh | bash
```

该脚本完成 3 件事：add 两个 marketplace + install kdev-code-graph（UA 通过 plugin.json `dependencies` 自动连带装）。

> 安全考虑：`curl | bash` 是反模式。建议先 `curl -sSL .../setup-kdev-codegraph.sh | less` 看脚本内容再跑。

### 本地 clone 后

```bash
git clone git@github.com:KDevSec/kdev-agents.git
cd kdev-agents
./scripts/setup-kdev-codegraph.sh
```

### Python ingestor（零安装）

ingestor 是 stdlib only 的 Python 工具，通过 `${CLAUDE_PLUGIN_ROOT}/ingestor/run.py` 直接调用，**不需要 venv 也不需要 pip install**。`/kdev-codegraph-build` skill 已经按这个路径调。

如需跑 ingestor 自测（开发场景）：

```bash
cd plugins/kdev-code-graph
./install.sh   # 会跑零安装验证 + 可选 dev venv 自测
```

### 在 Claude Code 内手动安装（不用脚本）

```
/plugin marketplace add KDevSec/kdev-agents
/plugin marketplace add Lum1104/Understand-Anything
/plugin install kdev-code-graph
```

⚠️ `/plugin` 命令在 VSCode 扩展里不可用，只在 Claude Code CLI / 桌面应用 / Web App 里可用。

## 设计原则

- **不重写代码图谱引擎** — 完全复用 UA 上游
- **对 UA 0 修改** — 安全节点用 UA `concept` + `kdev:*` tag 编码
- **Contract test 当护栏** — UA 升级会自动检测白名单变化

详见 [实施计划 v2](../../docs/skills/kdev-code-graph/2026-05-10-实施计划-v2.md)。

## 目录

- [skills/_ua_adapter](skills/_ua_adapter/SKILL.md) — UA 命令调用协议
- [ingestor/](ingestor/README.md) — Python 灌入器
- [tests/contract/](tests/contract/) — UA schema 兼容护栏

## 升级 UA 上游

```bash
cd plugins/kdev-code-graph
python3 -m pytest tests/contract -v
# 失败 → 看 skills/_ua_adapter/SKILL.md "升级 UA 上游" 章节
```
