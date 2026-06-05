# CrewAI 架构借鉴点 — 员工记忆 Scope + 委派 + 事件总线（参考资料）

| 项 | 值 |
|---|---|
| 文档性质 | **参考资料 / 调研依据**（从 [05 数字员工架构补遗](./2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md) 抽 CrewAI 段独立成档，对齐 OMC `07` / BMAD `08` 逐框架借鉴点档案）|
| 日期 | 2026-06-05 |
| 范围 | CrewAI 作为**多 agent 共享记忆 + 委派 + 事件**范本对 kdev-staff / kdev-core 的借鉴；**不引入 Python CrewAI 运行时依赖** |
| 关联 | [员工能力专项 v1.5](../01-design/2026-05-28-01-KDev数字员工架构-员工能力专项-v1.5.md) · [整体架构](../01-design/2026-05-28-02-KDev-staff-整体架构-v0.1.md) · [05 数字员工架构补遗](./2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md)（CrewAI 原始深扫出处，§2.1/§2.3/§3.2/§七）|
| 源码位置 | `_repos/crewAI/`（gitignore，不提交；调研轮次：第二轮 2026-05-30「6 员工 crew 模型」深扫）|

---

## 0. 定位

CrewAI 是 KDev「6 人 AI 公司」隐喻**概念上 1:1 对齐**的同类框架（crew = 公司、agent = 员工、manager-agent = CEO、Process = 编排模式），所以它的价值在**多员工怎么共享/隔离记忆 + CEO 怎么委派 + 怎么审计事件**这三块——恰好补 OMC（编排底座）和 BMAD（单 agent 创作）都没覆盖的「多员工记忆拓扑」。

**借鉴边界**：只借**设计范式**（MemoryScope 路径前缀 / Process 模式 / agents-as-tools 委派 / Event Bus 事件分类），**不引入 CrewAI Python 运行时**——守 KDev markdown 主存哲学，记忆查询包成 thin layer over markdown grep。

---

## 1. Unified Memory + MemoryScope → 员工记忆拓扑（最优范式 ⭐⭐⭐⭐⭐）

CrewAI 的关键设计：**不是物理隔离 silos，而是同一个 store 的层级路径前缀**做隔离。

```python
Crew(memory=True)
  └── Agent1.memory = MemoryScope(root_path=f"/crew/{cid}/agent/{aid1}")
  └── Agent2.memory = MemoryScope(root_path=f"/crew/{cid}/agent/{aid2}")
  └── 团队共享 view = root_path="/crew/{cid}/"
```

引用：`_repos/crewAI/src/crewai/memory/memory_scope.py:38-76` + `_repos/crewAI/src/crewai/memory/storage/backend.py:11-180`

**对比 LangGraph**：LangGraph 用 tuple namespace（`("team_xyz","shared")`）更结构化便于切后端；CrewAI 用字符串路径前缀更贴文件系统。二者本质都是「同一 store + 命名空间隔离」。**KDev 倾向路径前缀**（跟 `.kdev/memory/` markdown 文件树天然对齐）。

### 1.1 KDev 落地（v0.x 就上）

```
.kdev/memory/
├── shared/                  ← 全员工共享 view（root="/shared"）
│   ├── 决策日志.md
│   ├── 踩坑日志.md
│   └── ...
└── staff/                   ← per-员工 scope
    ├── ceo/                 ← scope="/staff/ceo"（pending-decisions / stage-summary）
    ├── 需求架构师/          ← scope="/staff/req-architect"
    ├── 开发工程师/          ← scope="/staff/dev-engineer"
    ├── 测试工程师/          ← scope="/staff/test-engineer"
    ├── 评审专家/            ← scope="/staff/reviewer"
    └── cqo/                 ← scope="/staff/cqo"
```

查询 API（KDev thin layer over markdown grep，**不引 Python 运行时**）：

```python
recall(scope="/shared", query=...)              # 全员工可见
recall(scope="/staff/dev-engineer", query=...)  # 开发工程师私有 + /shared 自动合并
recall(scope="/staff/*", query=...)             # CEO/CQO 跨员工查询
```

> 跟 kdev-memory 现状的关系：现有 `.kdev/memory/` 已是 markdown 主存，加 `shared/` + `staff/<员工>/` 两级目录即套上 scope 模式，零运行时引入。

---

## 2. Process 编排模式 → KDev 模式选择补充（⭐⭐⭐ 中）

```python
class Process(Enum):
    sequential   = "sequential"     # 任务顺序执行
    hierarchical = "hierarchical"   # Manager-Agent 调度
    # consensual                    # 民主投票（TODO，未实现）
```

引用：`_repos/crewAI/src/crewai/process.py:1-12`

**对 KDev 启示**：v1.5 主用 **hierarchical**（CEO=manager 派单），但 **sequential** 也有场景（线性 deploy pipeline 等无需 CEO 中枢决策的链）。可在 flow-config 里给员工编排留「sequential / hierarchical」模式旋钮，而非写死 hierarchical。

---

## 3. AgentTools delegation（agents-as-tools）→ CEO 委派语义（⭐⭐⭐⭐）

CrewAI 让 CEO 调员工**用 function call（agents-as-tools），而非 messaging**。

**对 KDev 启示**：对齐 v1.5「CEO 派单 = `Agent({subagent_type:"需求架构师-编排"})`」——委派是函数调用语义（一跳、有返回值），不是消息总线投递。员工间协作（§3.5 的 3 跳发函）同理可走「编排能力互相当 tool 调」而非异步 messaging，降低状态协调复杂度。

---

## 4. Event Bus 20+ 事件类 → CQO 审计 + HUD 事件订阅（⭐⭐⭐⭐）

CrewAI 有 20+ 事件类的 in-memory pub/sub Event Bus。

**对 KDev 启示**：CQO 元监督（§4 模式 d 常驻后台监听「每条事件都抽查」）+ HUD 实时事件订阅都需要一个**事件分类体系**。CrewAI 的 20+ 事件类是现成的事件 taxonomy 参考（agent 开始/结束、task 完成、工具调用、记忆读写等）。

**待决（见 §5）**：CrewAI 是 in-memory pub/sub，OMC 是 file-based `events.log`——KDev 选哪种、怎么融合。

---

## 5. 承接的未决问题（来自 05 §九，CrewAI 相关）

| # | 问题 | 取向 |
|---|---|---|
| 1 | **MemoryScope 路径前缀 vs LangGraph tuple namespace** | KDev 倾向路径前缀（贴文件系统）；tuple 更便于未来切后端，暂不取 |
| 2 | **CrewAI Event Bus（in-memory pub/sub）vs OMC events.log（file-based）怎么融合** | KDev 默认 file-based（可审计、跨 session 持久、markdown 哲学）；in-memory 订阅留给 HUD 实时层 |
| 3 | **多员工并发执行时 `.kdev/memory/` 文件锁** | CrewAI 有 `test_crew_thread_safety.py` 范本；KDev hook 并发写**必须**处理（关联 G-001/G-002 commit hook 并发） |

---

## 6. 借鉴边界

| | 借 | 不借 |
|---|---|---|
| 范式 | MemoryScope 路径前缀隔离 / shared+staff 两级 scope / Process 模式旋钮 / agents-as-tools 委派 / Event Bus 事件 taxonomy | —— |
| 运行时 | 无（记忆查询包成 markdown grep thin layer） | CrewAI Python 运行时 / in-memory store / LLM-backed memory provider |
| 取舍 | file-based 持久优先 | in-memory pub/sub 作主事件源（仅留 HUD 实时层）|
