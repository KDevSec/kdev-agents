# Node→Agent 路由表

每个 action 节点需要派哪个业务 agent（subagent_type），以及派单时需要传什么上下文。

本表适用于 `dev-engineer`（开发工程师）员工的 coding-flow。未来其他员工（如 req-architect）会有自己的路由表。

## 路由映射

| 节点 id | 节点名称 | subagent_type | agent 中文名 | 干什么 | 需传的上下文 |
|---|---|---|---|---|---|
| n0-env | 项目背景对齐 | `dev-engineer-env` | 开发工程师·环境准备 | clone 仓库、栈版本对齐、蒸馏 UED materials → rules.md | repo_url, materials_path（含 AGENTS.md / design-tokens.json / ued-v6.css）, workspace 路径 |
| n2-worktree | 新建 worktree | `dev-engineer-env` | 开发工程师·环境准备 | 在 worktree 里做（关联度低时走此分支） | repo_url, workspace 路径, 分支名 |
| n3-plan | 写 implementation-plan | `dev-engineer-plan` | 开发工程师·实施计划 | 写 PLAN.md：任务拆解、TDD 序列、验收标准 | 任务描述, gate_a_verdict（high/low）, 考题或 spec 文件路径, workspace 路径 |
| n6a-impl-inline | 主控直接实现 | **不派 agent** | — | 主控自己写代码（simple 任务时走此分支） | 任务描述, PLAN.md 路径, workspace 路径 |
| n6b-impl-subagent | subagent 派单实现(含TDD) | `dev-engineer-frontend` | 开发工程师·前端实现 | 改 src：视觉改造（token 对齐 + 页面逐页走查） | 任务描述, PLAN.md 路径, rules.md 路径, prototype 图路径, 当前 increment 范围（如"T0+T1"）, workspace 路径, src 项目路径 |
| n11-merge | 合并主分支 | `dev-engineer-deploy` | 开发工程师·部署上线 | 合并分支 + 起测试环境 + release notes | 分支名, workspace 路径, 项目路径 |

## Gate 节点不派 agent

Gate 节点由编排器（你）自行判断，不派业务 agent。具体判据见 `gate-decision-logic.md`。

但以下 gate 节点涉及验证/验收工作，需要先派 agent 做检查再判断：

| Gate 节点 | 检查方式 | 说明 |
|---|---|---|---|
| n8-verify (g-verify) | dev-engineer-frontend 自检 | frontend agent 完成后自跑 build+lint+UED grep，编排器读结果判 PASS/FAIL |
| n9b-e2e (g-e2e) | `dev-engineer-e2e` 派单 | 派 e2e agent 做视觉 diff + 功能冒烟，等结果后判 PASS/FAIL |
| n12-deploy (g-deploy) | `dev-engineer-deploy` + e2e 检查 | deploy agent 起环境后，e2e agent 做金丝雀冒烟 |

注意：这些 gate 的"检查"部分确实需要派 agent，但"判断"部分由编排器做。流程是：先派 agent 收证据 → 读证据 → 编排器判 verdict → record-gate。

## n6a vs n6b 的选择

- g-complexity 判 `simple` → n6a（主控直接实现，不派 subagent）
- g-complexity 判 `complex` → n6b（派 dev-engineer-frontend subagent）

绝大多数视觉改造任务判 `complex`，走 n6b。

## 单上下文构造要点

派 agent 时 prompt 要包含以下要素（按 agent 需求选取）：

1. **身份声明**："你是 XX·YY（dev-engineer-ZZ），当前在 coding-flow 的 nX 节点"
2. **任务描述**：`--task` 参数的内容，或从文件读取的考题/需求描述
3. **节点目标**：从 node-table 和 agent 人设文档提取的职责描述
4. **前序产物**：env.md / rules.md / PLAN.md 的路径（已经产出的话）
5. **约束材料**：AGENTS.md / design-tokens.json / 原型图 的路径
6. **工作目录**：workspace + 项目路径
7. **当前范围**：特别是 frontend agent，明确"这一轮做哪个 increment"

详见 SKILL.md §4 上下文构造模板。