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

### 通过 Claude Code marketplace（推荐）

```
/plugin marketplace add KDevSec/kdev-agents
/plugin marketplace add Lum1104/Understand-Anything
/plugin install kdev-code-graph
```

UA 会作为依赖自动安装（通过 plugin.json `dependencies` 字段）。

### 准备 Python ingestor

`/plugin install` 装完 plugin 文件后，还需要准备 Python ingestor 环境（创建 venv + 安装 kdev-ingestor）：

```bash
cd ~/.claude/plugins/cache/kdev-agents/kdev-code-graph/<version>
./install.sh
```

或在本地开发场景下直接：

```bash
cd plugins/kdev-code-graph
./install.sh
```

> 注：未来 ingestor 可能改造为零安装（stdlib only），届时这一步可省略。

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
