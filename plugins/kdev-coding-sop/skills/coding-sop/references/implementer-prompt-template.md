# Implementer Prompt 派单卡片

派 sonnet implementer 跑一个 task / bundle 时使用。结构是 **3 段必填 + 1 段固定文本**——派单时只填前 3 段，固定段照搬。

## 派单流程

1. 主控按当前 task 写「任务 / 输入 / 本次 task 范围」3 段
2. 拼接「固定段」（永不变，照搬即可）
3. 整体作为 prompt 传给 `Agent({model:"sonnet", prompt: <整段>})`

---

## 必填段（每次派单不同）

```
任务：<简洁描述本次 implementer 负责的 task / bundle>

输入：
- spec: <path-to-spec, e.g., specs/<feature>/spec.md>
- 实施计划: <path-to-implementation-plan, e.g., specs/<feature>/implementation-plan.md>

本次 task 范围：
<从 implementation-plan.md 里抄具体 task 段落，包括 Files / RED / GREEN / REFACTOR / COMMIT 5 步>
```

---

## 固定段（照搬，永不修改）

```
约束 1 - 环境（项目级工具链强制）：
- 用项目级解释器/工具链（venv / node_modules / go.mod / cargo / maven 等），具体由你按本项目栈选择
- 禁止系统全局命令（裸 python3 / npm install / 全局 go install / 系统 mvn 等会绕开锁定版本）
- 依赖装到项目级路径，所有命令通过项目级 binary 调用
- 如发现项目级解释器/依赖未就绪，先按本栈惯例（venv + pip / npm ci / go mod download / cargo build --locked / mvn dependency:resolve）建好再开始

约束 2 - TDD 强制：
Before writing any production code, use the Skill tool to invoke
`superpowers:test-driven-development` and follow its red-green-refactor
discipline strictly. Each commit must include both the failing test and
the implementation that makes it pass.

约束 3 - 项目规则与默认兜底（按以下优先级处理）：

1. <repo>/docs/rules.md（如存在则 Read 并严格遵守）
2. <repo>/specs/<feature>/rules.md（feature 临时规则，如存在则 Read 并遵守）

如以上文件不存在或未覆盖某场景：
- 遵守 CLAUDE.md 全局约定
- 兜底用栈通用最佳实践（PEP8 / gofmt / 框架 idiom 等模型训练自带知识）
- **不要随意读相邻代码去模仿**——相邻文件可能是历史遗留 / 例外处理，与 rules 冲突时以 rules 为准
- 如有真实不确定（rules 没说、栈通用最佳实践模糊），**停下来问主控**，不要凭"项目里看着别人这么写"就跟着写

外置规则与栈通用约定冲突时优先外置规则。

输出：
- 改动文件清单（仓库相对路径）
- 测试输出（含 PASS/FAIL 数；新增了哪些 test case）
- commit hash 与消息
```

---

## 完整示例（拼好后长这样）

```
任务：实现用户列表 CRUD REST 接口（GET/POST/PUT/DELETE /users）+ Postgres 持久化 + 单元测试

输入：
- spec: specs/001-user-mgmt/spec.md（FR-1 ~ FR-5）
- 实施计划: specs/001-user-mgmt/implementation-plan.md

本次 task 范围：
Phase 2 Task 2.1（User CRUD 接口）：
- Files: src/db/users.dao.ts, src/routes/users.router.ts, tests/unit/users.dao.test.ts
- RED: 写 5 个失败测试覆盖 CRUD 5 个端点
- GREEN: 实现 DAO + Router 让测试通过
- REFACTOR: 抽 query builder
- COMMIT: 「feat(users): CRUD endpoints + DAO」

约束 1 - 环境（项目级工具链强制）：
- 用项目级解释器/工具链（venv / node_modules / go.mod / cargo / maven 等），具体由你按本项目栈选择
- 禁止系统全局命令（裸 python3 / npm install / 全局 go install / 系统 mvn 等会绕开锁定版本）
- 依赖装到项目级路径，所有命令通过项目级 binary 调用
- 如发现项目级解释器/依赖未就绪，先按本栈惯例（venv + pip / npm ci / go mod download / cargo build --locked / mvn dependency:resolve）建好再开始

约束 2 - TDD 强制：
Before writing any production code, use the Skill tool to invoke
`superpowers:test-driven-development` and follow its red-green-refactor
discipline strictly. Each commit must include both the failing test and
the implementation that makes it pass.

约束 3 - 项目规则与默认兜底（按以下优先级处理）：

1. <repo>/docs/rules.md（如存在则 Read 并严格遵守）
2. <repo>/specs/<feature>/rules.md（feature 临时规则，如存在则 Read 并遵守）

如以上文件不存在或未覆盖某场景：
- 遵守 CLAUDE.md 全局约定
- 兜底用栈通用最佳实践（PEP8 / gofmt / 框架 idiom 等模型训练自带知识）
- 不要随意读相邻代码去模仿——相邻文件可能是历史遗留 / 例外处理，与 rules 冲突时以 rules 为准
- 如有真实不确定，停下来问主控，不要凭"项目里看着别人这么写"就跟着写

外置规则与栈通用约定冲突时优先外置规则。

输出：
- 改动文件清单（仓库相对路径）
- 测试输出（含 PASS/FAIL 数；新增了哪些 test case）
- commit hash 与消息
```

---

## 设计原则（为什么固定段长这样）

- **不在 prompt 里 inline 栈通用知识**（FastAPI 路由顺序 / `npm ci` / async await 等模型自带知道，重复浪费 prompt 空间且不增加可靠性）
- **项目特定规则强制走外置文件**（`<repo>/docs/rules.md`），不在 prompt 里 inline，避免 prompt 与外置文件 drift
- **3 段约束顺序固定**：环境（最先确保能跑） → TDD（写代码方法论） → 项目规则（项目特定约束），先决条件链清晰

## 派单时常忘的细节

1. **模型选档**（不在 prompt 里，在外层 `Agent({...})` 调用里）：
   - routine 业务代码 / 前端 / E2E / 测试 fix → `Agent({model:"sonnet"})`
   - schema 迁移 / 跨模块状态 / 鉴权 / 完全新架构 → `Agent({model:"opus"})`

2. **Bundle 边界**（参主体 SKILL.md 节点 6b 单次派单上限）：
   - 写入文件 > 6 / 测试 > 15 / 命中升档 opus 任一 → 单独派
   - 「本次 task 范围」段必须写清边界，避免 implementer 自由发挥扩散到隔壁模块

3. **项目级 rules.md 维护**：
   - 每个项目 `<repo>/docs/rules.md` 由主控 / 团队持续维护
   - 只记录模型不知道的内容（项目特定 fork bug、版本锁定原因、内部约定等）
   - 栈通用 gotcha 不要写进去（浪费空间）
   - 格式参考：`references/examples/project-rules-example.md`
