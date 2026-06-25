# framework/04-references — 外部参考资料

> 这个目录用来放**外部参考**：开源仓库浅克隆 + BMAD 等第三方框架使用指南 + 自己写的对比分析。
> 模式参考 `docs/skills/kdev-code-graph/references/`：源码项目 gitignore，分析文档可提交。

---

## 一、目录索引

### 1.1 第三方框架指南

| 文档 | 说明 |
|---|---|
| [2026-04-08-01-BMAD使用指南.md](2026-04-08-01-BMAD使用指南.md) | BMAD 框架使用 |
| [参考工作流.md](参考工作流.md) | "人主导规则，AI 主导执行" 5 阶段迭代流程 |

### 1.2 开源仓库源码调研（2026-05-30 启动）

针对 KDev 记忆系统 + 数字员工架构设计需要，调研 5+ 个具有代表性的开源记忆/agent 框架：

| 文档 | 主题 |
|---|---|
| [2026-05-30-02-5仓源码调研综合报告.md](2026-05-30-02-5仓源码调研综合报告.md) | **核心报告（第一轮）**—— 5 仓记忆架构横向对比 + 跨平台/MCP/多 LLM/多 agent 维度 |
| [2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md](2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md) | KDev 现状 vs v3.0 的 5 层架构 vs 5 仓发现的 gap；人 vs AI 双轨设计提案 |
| [2026-05-30-04-知识图谱集成方案-借用kdev-code-graph.md](2026-05-30-04-知识图谱集成方案-借用kdev-code-graph.md) | Memory Level 1 知识图谱怎么跟现有 kdev-code-graph plugin 共用 UA 引擎 |
| [2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md](2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md) | **第二轮深扫**——多 agent 共享记忆 + 自演进/重试/升级 + 跨 IDE 模型 + 数字员工架构最终建议 |
| [2026-05-30-06-kdev-memory-vs-OMC源码层对比.md](2026-05-30-06-kdev-memory-vs-OMC源码层对比.md) | **源码层实地对比** —— kdev-memory（Python+markdown）vs OMC（TS+混合）；5 项强烈推荐借鉴 + 3 项可选 + 5 项不借 |
| [2026-06-05-07-OMC架构借鉴点-kdev-core编排底座.md](2026-06-05-07-OMC架构借鉴点-kdev-core编排底座.md) | **架构概念级借鉴** —— OMC Notepad / 6 类 JSON / Team Pipeline → kdev-core 编排底座（从整体架构正文剥离的调研档案）|
| [2026-06-05-08-BMAD-Agent体系借鉴点-员工编排prompt骨架.md](2026-06-05-08-BMAD-Agent体系借鉴点-员工编排prompt骨架.md) | **单 agent 创作层借鉴** —— BMAD persona 骨架 / Capabilities 路由表 / outcome-driven 剪枝 / 三形态梯度 → 员工编排 prompt 模板（只借创作层，不借集群编排）|
| [2026-06-05-09-CrewAI架构借鉴点-员工记忆Scope+委派+事件总线.md](2026-06-05-09-CrewAI架构借鉴点-员工记忆Scope+委派+事件总线.md) | **多员工记忆拓扑借鉴** —— MemoryScope 路径前缀（shared+staff 两级 scope）/ Process 模式旋钮 / agents-as-tools 委派 / Event Bus 事件 taxonomy（从 05 抽 CrewAI 段独立成档）|

### 1.3 源码克隆目录（gitignore）

| 子目录 | 仓库 | URL | Stars | 大小 | 调研轮次 |
|---|---|---|---|---|---|
| `_repos/oh-my-claudecode/` | OMC | github.com/Yeachan-Heo/oh-my-claudecode | 25k | 65M | 第一轮 + 第二轮（编排 + 自演进深扫） |
| `_repos/letta/` | Letta (前 MemGPT) | github.com/letta-ai/letta | ~14k | 34M | 第一轮 |
| `_repos/mem0/` | mem0 + OpenMemory | github.com/mem0ai/mem0 | ~25k | 50M | 第一轮 + 第二轮（OpenMemory MCP 深扫） |
| `_repos/aider/` | Aider | github.com/Aider-AI/aider | ~25k | 141M | 第一轮 |
| `_repos/continue/` | Continue.dev | github.com/continuedev/continue | ~23k | 463M | 第一轮 + 第二轮（跨 IDE 三层深扫） |
| `_repos/langgraph/` | LangGraph | github.com/langchain-ai/langgraph | ~14k | 19M | 第二轮新增（多 agent State/Store） |
| `_repos/crewAI/` | CrewAI | github.com/crewAIInc/crewAI | ~30k | 361M | 第二轮新增（6 员工 crew 模型） |

总磁盘 ~1.1GB（浅克隆 `--depth 1`）。

### 1.4 退役插件历史备份（2026-06-25 归档）

从 `plugins/` 退役、整树搬入 `_retired-plugins/` 作冻结历史备份（已从 `.claude-plugin/marketplace.json` 注销，不再作为活跃插件安装）。代码冻结，内部对 `plugins/...` 的相对/绝对路径引用为搬迁前状态，不再维护。

| 子目录 | 原路径 | 说明 |
|---|---|---|
| `_retired-plugins/kdev-core/` | `plugins/kdev-core` | 数字员工编排底座（R1 状态/R2 流转/R3 关卡）：feature-first 存储 + events.jsonl 流水 |
| `_retired-plugins/kdev-hud/` | `plugins/kdev-hud` | 数字员工观测层（纯只读）：把 kdev-core feature-first 账本渲染成命令行状态栏 + 自包含网页仪表盘 |
| `_retired-plugins/kdev-team/` | `plugins/kdev-team` | KDev 数字员工集群：编排+业务 agent + per-员工 node-table + staff.yml 花名册 |

> 与 `_repos/`（gitignore 的外部源码克隆）不同，`_retired-plugins/` 是**自有代码的历史快照，纳入版本控制**。

---

## 二、克隆命令（重新建立环境用）

### Linux / macOS

```bash
mkdir -p docs/framework/04-references/_repos
cd docs/framework/04-references/_repos

git clone --depth 1 https://github.com/Yeachan-Heo/oh-my-claudecode.git
git clone --depth 1 https://github.com/letta-ai/letta.git
git clone --depth 1 https://github.com/mem0ai/mem0.git
git clone --depth 1 https://github.com/Aider-AI/aider.git
git clone --depth 1 https://github.com/continuedev/continue.git
git clone --depth 1 https://github.com/langchain-ai/langgraph.git
git clone --depth 1 https://github.com/crewAIInc/crewAI.git
```

---

## 三、.gitignore 配置

`docs/framework/04-references/_repos/` 已经被项目根 `.gitignore` 排除（确认后写入）：

```gitignore
docs/framework/04-references/_repos/
```

**分析文档可提交**（`.md`），**源码项目不提交**（`_repos/`）。

---

## 四、调研维度覆盖矩阵

| 维度 | OMC | Letta | mem0 | Aider | Continue | LangGraph | CrewAI |
|---|---|---|---|---|---|---|---|
| 记忆架构 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 跨平台 / MCP | ✅ | ⚠️ | ✅深 | ⚠️ | ✅深 | - | - |
| 多 LLM provider | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 多 agent 编排 | ✅深 | ⚠️ | ❌ | ❌ | ❌ | ✅深 | ✅深 |
| Hook / 关键字触发 | ✅深 | - | - | - | - | - | - |
| 自演进 / verification | ✅深 | - | - | - | - | ⚠️ retry | - |
| 多 agent 共享 long-term memory | ❌ | ❌ | - | - | - | ✅ Store namespace | ✅ MemoryScope |
| 跨 IDE 三层 | - | - | - | - | ✅深 | - | - |

**深扫 = 第二轮（2026-05-30）**。剩余覆盖盲点已无关键 blocker。

---

## 五、变更记录

| 日期 | 改动 |
|---|---|
| 2026-04-08 | 初始：BMAD 使用指南 + 参考工作流 |
| 2026-05-30 | 第一轮：clone OMC/Letta/mem0/Aider/Continue + 5 仓综合报告 + 双轨提案 + 知识图谱集成方案 |
| 2026-05-30 | 第二轮：clone LangGraph/CrewAI + 6 深扫 agent（OMC 编排 / OMC 自演进 / Continue 跨 IDE / OpenMemory MCP / LangGraph 多 agent / CrewAI 6-crew）+ 补遗 doc + 数字员工架构最终建议 |
| 2026-06-05 | 从整体架构正文剥离 OMC 架构借鉴对照 → 独立参考档案（2026-06-05-07）|
| 2026-06-25 | 退役插件归档：`plugins/{kdev-core,kdev-hud,kdev-team}` 整树搬入 `_retired-plugins/`，同步从 marketplace.json 注销 3 条注册 |
