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
| [2026-05-30-02-5仓源码调研综合报告.md](2026-05-30-02-5仓源码调研综合报告.md) | **核心报告** —— 5 仓记忆架构横向对比 + 跨平台/MCP/多 LLM/多 agent 维度 |
| [2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md](2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md) | KDev 现状 vs v3.0 的 5 层架构 vs 5 仓发现的 gap；人 vs AI 双轨设计提案 |
| [2026-05-30-04-知识图谱集成方案-借用kdev-code-graph.md](2026-05-30-04-知识图谱集成方案-借用kdev-code-graph.md) | Memory Level 1 知识图谱怎么跟现有 kdev-code-graph plugin 共用 UA 引擎 |

### 1.3 源码克隆目录（gitignore）

| 子目录 | 仓库 | URL | Stars | 大小 |
|---|---|---|---|---|
| `_repos/oh-my-claudecode/` | OMC | github.com/Yeachan-Heo/oh-my-claudecode | 25k | 65M |
| `_repos/letta/` | Letta (前 MemGPT) | github.com/letta-ai/letta | ~14k | 34M |
| `_repos/mem0/` | mem0 + OpenMemory | github.com/mem0ai/mem0 | ~25k | 50M |
| `_repos/aider/` | Aider | github.com/Aider-AI/aider | ~25k | 141M |
| `_repos/continue/` | Continue.dev | github.com/continuedev/continue | ~23k | 463M |

总磁盘 ~753MB（浅克隆 `--depth 1`）。

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
```

### 待补 clone（多 agent 维度，2026-05-30 待决）

| 仓库 | URL | 用途 |
|---|---|---|
| LangGraph | github.com/langchain-ai/langgraph | State / Messages / Long-term Store 三段分明 |
| CrewAI | github.com/crewAIInc/crewAI | 6 人公司隐喻 1:1 对应 + manager-agent 调度 |

---

## 三、.gitignore 配置

`docs/framework/04-references/_repos/` 已经被项目根 `.gitignore` 排除（确认后写入）：

```gitignore
docs/framework/04-references/_repos/
```

**分析文档可提交**（`.md`），**源码项目不提交**（`_repos/`）。

---

## 四、调研维度覆盖矩阵

| 维度 | OMC | Letta | mem0 | Aider | Continue | 待调研 |
|---|---|---|---|---|---|---|
| 记忆架构 | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| 跨平台 / MCP | ✅ | ⚠️ | ✅ | ⚠️ | ✅ | - |
| 多 LLM provider | ✅ | ✅ | ✅ | ✅ | ✅ | - |
| 多 agent 编排 | ⚠️ 浅 | ⚠️ | ❌ | ❌ | ❌ | **LangGraph / CrewAI** |
| Hook framework | ⚠️ 浅 | - | - | - | - | **OMC src/hooks/ 深扫** |
| Skill / agent 触发 | ⚠️ 浅 | - | - | - | - | **OMC 深扫** |
| 自演进 / verification | ⚠️ 浅 | - | - | - | - | **OMC verifier/learner/ralph** |

---

## 五、变更记录

| 日期 | 改动 |
|---|---|
| 2026-04-08 | 初始：BMAD 使用指南 + 参考工作流 |
| 2026-05-30 | 启动 5 仓源码调研；clone OMC/Letta/mem0/Aider/Continue；写 3 篇分析文档 |
