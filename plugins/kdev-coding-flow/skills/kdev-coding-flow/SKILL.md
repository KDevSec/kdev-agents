---
name: kdev-coding-flow
description: 用 13 节点 SOP 把一个需求从 spec/plan/prototype 三件套端到端跑到部署 + E2E 全绿、产出可上线。强制 TDD、Per-Increment E2E Gate、Phase 0 环境对齐、业务关键入口金丝雀；支持 Auto Mode 完全自主；按 CLAUDE.md 二档分工派单（sonnet 编码 / opus 评审与高复杂度）。技术栈无关——主体方法论通用，项目特定规则走外置 docs/rules.md，栈通用约定（PEP8/gofmt/路由顺序等）依赖模型自带知识不内置。Use when 用户说"按 SOP 开发"、"端到端把 X 跑完"、"实施这个 plan"、"用 13 节点 SOP 跑通"、"自主完成这个需求"、"auto mode 跑完这个 feature"，或主控正面对一个含 spec.md/plan.md/prototype 三件套且已授权自主推进的实施任务。
---

# 编码阶段 13 节点 SOP（通用方法论）

把"从需求到上线"切成 13 个节点：每个节点要么是动作要么是判断点。配合 TDD、Per-Increment E2E Gate、Phase 0 环境对齐，让一个含多个 user story / feature increment、~20-30 atomic task 的复杂需求被 AI 自主跑完，主控只在 3 个判断 Gate 决策。

本 skill 是技术栈无关的方法论层。具体执行内容分三类：
- **通用编码 hygiene**（"先读已有代码风格"、"trust internal code"等）→ 模型自带 + CLAUDE.md，**不在 skill 里**
- **栈通用约定**（PEP8 / gofmt / FastAPI 路由顺序 / Express middleware 等）→ **模型自带**，不在 skill 里
- **项目特定规则**（项目命名约定 / 框架 fork bug / 版本错配 / 团队约定）→ **外置** `<repo>/docs/rules.md`，由项目维护

skill 内置 references（仅运行时派单必需的模板与示例）：
- `references/implementer-prompt-template.md` — 通用 implementer prompt 骨架（类型：派单规范）
- `references/examples/project-rules-example.md` — 项目级 rules.md 格式示例

## 适用场景

- 输入齐：`spec.md`（业务需求）+ `plan.md`（speckit-plan 或类似产出，本 SOP 视为输入）+ `prototype` 之类的 UI/接口示意
- 工作量 ~20-30 个 atomic task
- 用户授权 Auto Mode（完全自主推进）

## 三个人工判断 Gate（主控不下放）

每个 task 怎么实施可以下放 implementer；但「跑不跑这个 task」「跑完该不该推下一 phase」必须主控决策。

| Gate | 节点 | 决策内容 |
|------|------|---------|
| Gate-A 关联度 | 节点 1 | 高 / 低 → 单分支 vs worktree |
| Gate-B 复杂度 | 节点 5 | 简单 / 复杂 → 主控直接执行 vs subagent 派单 |
| Gate-C E2E 通行证 | 节点 9 (per-increment) | 100% PASS → 推下一增量；否则回流 fix |

## 13 节点流程

```
0. 项目背景对齐（首次跑 SOP / 新项目接入时一次性做，第二次起跳过）
       │
       ▼
1. 关联度自检 (Gate-A)
       │
       ├─ 高 ──────────────────────┐
       └─ 低 → 2. 新建 worktree ──┤
                                    ▼
                      3. 写 implementation-plan.md (writing-plans)
                                    │
                                    ▼
                      4. AI 评审实施计划 (plan-eng-review)（判 / 回流 #3 ≤3 次）
                                    │
                                    ▼
                      5. 任务复杂度判断 (Gate-B)
                       ├─ 简单 → 6a 主控直接执行 (executing-plans)
                       └─ 复杂 → 6b subagent 派单 (subagent-driven-development)
                                    │
                                    ▼
                      7. TDD 编码 (red→green→refactor) — 在 implementer 内
                                    │
                                    ▼
                      8. 编码完成验证 (verification-before-completion)（判 / 回流 #7）
                                    │
                                    ▼
                      9. 代码评审 + Per-Increment E2E Gate (Gate-C)（判 / 回流 #7）
                                    │
                                    ▼
                      10. 安全扫描 (kdev-secure-coding 或 /security-review)（判 / 回流 #7）
                                    │
                                    ▼
                      11. 合并到本地主分支 (finishing-a-development-branch)
                                    │
                                    ▼
                      12. 部署被测环境 + 端到端测试（含业务关键入口金丝雀）(gstack-qa)
                                    │
                                    ▼
                      13. 产出清点 + sop-execution-log + skill 提炼
```

## 节点细则

### 节点 0（前置）项目背景对齐

> **何时做**：首次跑 SOP / 新项目接入时一次性做。第二次起，rules.md 已存在 + 工具链已确认 → 直接跳到节点 1。

正式动手前主控必须做几件事：

1. **和开发者确认栈与工具链**：用什么语言/框架、依赖管理用什么、测试框架用什么、本地服务（DB/Redis/队列）跑哪。**不要凭目录结构猜**，明确问。

2. **确认项目规则的起源（首次跑 SOP 时一次性做）**：
   - 问 user：本项目是否基于某个开源项目 / 模板？（RuoYi / Spring Initializr / Next.js template / shadcn-ui / AntDesign 后台模板等都常见）
   - 如有 GitHub URL **且** `<repo>/docs/rules.md` 不存在或为空 → **派 sonnet subagent 蒸馏**（不在主控做，避免污染上下文）：
     ```
     Agent({
       model: "sonnet",
       prompt: "WebFetch <github_url> 的 README / CONTRIBUTING.md / docs/ 关键页面 / 风格指南。
                蒸馏与编码相关的规范条目（命名 / 错误处理 / 测试组织 / 依赖管理 / commit 格式 /
                框架特有约定等），分类整理后写入 <repo>/docs/rules.md，控制 30-50 条以内。
                完成后回报：rules.md 路径 + 条目数 + 主要分类。"
     })
     ```
   - 第二次跑 SOP 起跳过这一步（rules.md 已存在）
   - 如 user 说「无开源底座、纯新项目」→ 起一个空骨架 rules.md（含「跑过程中追加项目特定踩坑」一行说明）即可

3. **要求 implementer 用项目级工具链**：禁止系统全局命令（裸 `python3` / `npm install` / 全局 `go install` / 系统 `mvn` 等）。具体命令模型自己会，主控只在 implementer prompt「约束 1」写一句"用项目级解释器/工具链 + 锁版本"。

4. **如有外部服务**：派单前 `ss -tlnp | grep ":<port> "` 探测端口冲突，端口选非常用段（避开 3306/5432/6379/8080 等）。

5. **可选 LSP server 检测**（首次跑 SOP 时一次性做，完全 optional）：
   - 检测本栈对应 LSP server 是否已装（`pyright` / `typescript-language-server` / `gopls` / `rust-analyzer` 等）
   - 已装 → 节点 8 自动加一项「LSP diagnostics」补充信号
   - 未装且 Auto Mode 关闭 → 提示 user：「检测到本栈 LSP server 未安装，是否安装？（推荐，提升类型/结构校验信号；拒绝也不影响 SOP）」，同意则主控执行对应安装命令（pip/npm/go install/rustup 等，模型自己会）
   - 未装且 Auto Mode 开启 → 输出 1 行提示但**不阻塞流程**，跳过此步继续，节点 13 收尾时 sop-execution-log 记一笔「LSP 未安装，建议下次手动安装」

派单细节参 `references/implementer-prompt-template.md`。

### 节点 1 关联度自检（Gate-A）

读 spec / plan / prototype，自评本需求与已有功能的关联度：
- **高**（链式依赖、共享 schema/目录/seed/鉴权）→ 跳节点 2，单分支顺序开发
- **低**（独立子系统）→ 节点 2 开 worktree

### 节点 2 新建 worktree

调 `Skill: superpowers:using-git-worktrees`。如果当前已在 git worktree（`.git` 是链接文件而非目录），跳过。

### 节点 3 写 implementation-plan.md

调 `Skill: superpowers:writing-plans`。**强制保存路径** = `specs/<feature>/implementation-plan.md`（不要写到 plan.md，那是上游输入会被覆盖）。

要求：
- 多 phase 结构（典型：Phase 0 环境/骨架 → Phase 1 数据层/基础设施 → Phase 2-N 每个 increment 一个 phase → Phase N+1 集成）
- 每 task 含: Files / RED / GREEN / REFACTOR / COMMIT 5 步
- 每条 spec 验收标准 / FR / SC 映射到 task（self-review 矩阵）
- 复杂任务标注（schema 迁移/跨模块状态/鉴权 → 升档 opus）

### 节点 4 plan eng review

调 `Skill: gstack-plan-eng-review`（如缺则 fallback 到 `superpowers:requesting-code-review`）。

**Auto Mode 适配**（重要）：
- 跳过 onboarding / 遥测 / 路由 / vendoring / office-hours / outside-voice 等弹问
- review section 内的 AskUserQuestion 改为内联呈现 + 按 recommended 自动落实 refinement
- refinement inline 应用到 plan 文件
- 把 review report footer 写到 plan 末尾

回流：plan 不通过 → 反馈写回 plan → 重写。同一 plan 最多回流 3 次，第 4 次仍不过停下报告。

### 节点 5 任务复杂度判断（Gate-B）

判据（命中任 2 即复杂）：
- 多文件协调（>10 文件）
- 跨模块状态（>3 个核心实体强引用）
- 数据模型变动（schema 迁移 / 索引调整 / 约束变更）
- 鉴权 / 权限 / 安全相关
- 状态机 / 跨服务事务 / 分布式一致性

简单 → 6a；复杂 → 6b（强烈建议复杂任务必须 6b，主会话上下文承担不下）。

### 节点 6b subagent 派单

调 `Skill: superpowers:subagent-driven-development`。

**派单二档分工**（参全局 CLAUDE.md）：

| 任务类型 | 模型 |
|---------|------|
| routine 业务代码 / 前端 / E2E / 测试 fix | `Agent({model:"sonnet"})` |
| schema 迁移 / 跨模块状态协调 / 鉴权 / 完全新架构 | `Agent({model:"opus"})` |
| spec/quality reviewer | `Agent({model:"opus"})` 或内建 superpowers:code-reviewer |

**Bundle 策略**（紧耦合的兄弟模块合并派单，降低派单成本）：

通用原则：「同一抽象层、紧耦合、变更倾向同步」的兄弟模块合并到一个 implementer。

后端 MVC 项目示例：
- DAO + 实体定义 + 输入/输出 schema → 1 implementer
- Service 层复杂业务 → 1 implementer
- Controller / Handler + 集成测试 → 1 implementer
- Frontend 页面 + 该页面对应 E2E → 1 implementer

CLI 工具示例：
- 命令解析 + 输入验证 → 1 implementer
- 核心业务逻辑 + 单元测试 → 1 implementer
- 输出格式化 + 集成测试 → 1 implementer

**单次派单上限**（命中任一即应单独派，避免 token 上限切断写一半）：
- 写入文件数 > 6
- 测试用例数 > 15
- 命中「升档 opus」任一项

每 implementer prompt 必须含三段约束（环境 + TDD + 项目规则），完整模板参 `references/implementer-prompt-template.md`。**注意**：约束 3「项目规则」只指 implementer 读外置 `<repo>/docs/rules.md`，**不要在 prompt 里重复栈通用 gotcha**（FastAPI 路由顺序、`npm ci` 等模型自带知道）。

### 节点 7 TDD 编码

每个 implementer 内部强制 RED → GREEN → REFACTOR → COMMIT。主控不直接写代码。调 `Skill: superpowers:test-driven-development`。

### 节点 8 编码完成验证

调 `Skill: superpowers:verification-before-completion`。按以下顺序验证：

1. **语法/类型** — 跑项目级 typechecker（`mypy` / `tsc` / `cargo check` / `go vet` 等）
2. **Lint/Style** — 跑项目 linter（`flake8` / `eslint` / `golangci-lint` 等）
3. **单元/集成测试** — 全量 PASS 才算"完成"
4. **可选：LSP diagnostics**（如节点 0 检测到 LSP server 已装）— 作为类型/引用层面的额外快查信号，**不能替代**实际跑测试，缺失也不阻塞

### 节点 9 代码评审 + Per-Increment E2E Gate（Gate-C）

调 `Skill: superpowers:requesting-code-review` 或 `coderabbit:code-reviewer`。

**Review 颗粒度（4-shot 模型，实测覆盖关键质量信号）**：
1. 节点 4 plan-eng-review × 1
2. Phase 末 mini spec review × 1（仅检查 spec 偏差）
3. 全部 task 完成后 final code review × 1（覆盖完整 diff）
4. 节点 10 安全扫描 × 1

per-task 跑双 reviewer（spec + quality）在 ~25 task 下需 ~50 次派单，成本不可承受，实测删除后质量未下降。

**Per-Increment E2E Gate 严格执行**：每个增量（user story / feature / sub-task，视 spec 风格而定）必须 100% E2E 通过才推进下一增量，未过则回流到节点 7 fix。这条 Gate 捕获单元测试全绿但用户感知失败的 bug（典型：异常类 `__init__` 不调 super 导致 `str(exc)` 永远空，`pytest.raises(match=)` 永远 FALSE，单元测试看似 PASS 实际未验证业务）。

### 节点 10 安全扫描

按你的栈选 skill：
- Python → `Skill: kdev-secure-coding:python-security-coding`
- 其他栈 → 对应栈安全 skill 或 fallback 到 `/security-review`

按 skill 内 8 类自检清单逐条核对。

### 节点 11 合并主分支

调 `Skill: superpowers:finishing-a-development-branch`。

**注意**：如果"主分支"在另一 worktree 已被使用，`git checkout` 会失败：
- 优先尝试 `git push . HEAD:<main-branch>`（fast-forward 内部 ref 更新，不动其他 worktree）
- 如果 non-fast-forward（已分叉）→ 不强制覆盖（违反「NEVER force push to main」），把当前分支文档化为「稳定结果分支」

### 节点 12 部署 + 端到端测试（含业务关键入口金丝雀）

按部署手册起本地被测环境。

**E2E 套件强制有 ≥1 条「业务关键入口金丝雀」用例**：

「业务关键入口」指用户使用产品的第一公里——任何用户必经的入口路径。这条用例必须**真走完整 UI / CLI 流程**，不能用任何 helper 跳过中间步骤。

具体形态视产品而定：
- Web 应用 → 真打开登录页，fill 用户名 / 密码，点登录按钮，断言进入主页
- CLI 工具 → 真敲 `your-cli init` 或 `your-cli login`，断言生成预期文件 / 输出
- API SDK / 库 → 真起 client → 调最常用入口 → 断言响应
- 数据管线 → 真投一条新数据进 source → 断言 sink 收到

理由：其他 E2E 为加速会用 `LoginHelper.login()` 走 API + 灌 storage_state、用 mock client、跳过初始化等。这种加速会让「业务最关键路径本身的退化」（如登录页 captcha 接口 500、登录页静态资源 404、CLI init 路径变更等）测试永远不暴露。spec 的 Acceptance Scenario 也应显式列入「用户能从入口正常进入」。

如 Per-Increment E2E（含金丝雀）已 100% PASS，可跳过额外的 gstack-qa（已直接覆盖 spec 的 acceptance scenarios）。

### 节点 13 产出清点 + skill 提炼

确认产出清单齐全：
1. 单元测试代码（unit + integration）
2. 业务代码（后端 + 前端 / CLI / SDK 视产品而定）
3. 可运行的被测项目（部署 + 测试通过）
4. 安装/部署手册（含 FAQ）
5. SOP 执行日志（落到 `specs/<feature>/sop-execution-log.md`）
6. **项目规则文件更新**：把本次发现的「模型不知道的项目特定踩坑」追加到 `<repo>/docs/rules.md`（栈通用 gotcha 不要写进去）
7. 实践总结 markdown（如有跨阶段心得需要沉淀）
8. SKILL 草稿提炼（如本次 SOP 暴露了通用经验值得做新 skill）

## Implementer 派单要点

完整 prompt 模板参 `references/implementer-prompt-template.md`。要点：

三段约束**必须**全部包含：
1. **环境**：用项目级工具链 + 锁版本（一句话，不展开具体栈命令）
2. **TDD**：调 `superpowers:test-driven-development` 走 red-green-refactor
3. **项目规则**：implementer 自行 Read `<repo>/docs/rules.md` 与 `<repo>/specs/<feature>/rules.md`（如存在）

**关键原则**：约束 3 只指外置文件路径，**不要在 prompt 里 inline 任何栈通用知识**（FastAPI 路由顺序 / npm ci / async 错误吞没等模型自带知道，重复浪费 prompt 空间且不增加可靠性）。

## 项目规则文件（外置）

每个项目应有一份 `<repo>/docs/rules.md`，由主控 / 团队持续维护。**只记录模型不知道的内容**：

- 编码规范的项目特定约定（"DAO 方法名前缀必须 find_/save_"）
- 框架行为的项目特定用法（"用 ResponseUtil.success() 不直接返回 dict"）
- 测试组织的项目约定（"service 层覆盖率 ≥ 90%"）
- 依赖与版本的项目特定 lock 原因（"Pillow 必须 12.x，10.x 拒收 pathlib.Path"）
- 项目特定行为（框架 fork 的 bug、内部库的隐式契约）

格式参考：`references/examples/project-rules-example.md`

新项目第一次跑 SOP 时这份文件可能很空。每跑完一个 task / phase，把当次发现的项目特定踩坑追加进去；下次派单就能避坑。

## Auto Mode 适配

skill 必须支持"完全自主"模式：
- 跳过所有 onboarding 弹问（telemetry / routing / lake intro / outside-voice 等）
- review skill 内的逐 issue AskUserQuestion 改为内联决策 + 按 recommended option 自动落实 refinement
- 失败时输出 BLOCKED 报告而非死循环
- 派单只在 `Agent({model:...})` 参数指定模型，**不打扰用户切 `/model`**

## 实测案例参考基线（Python / FastAPI / Vue / Playwright）

某项目 23 task / 4 User Story / ~13k LOC 跑完 SOP 的实测数据：
- implementer 派单 21 次（含 5 次 fix）
- reviewer 派单 ~3 次（spec / final code review）
- 主控 commit 数 23（含 fix 与 docs）
- 测试覆盖：176（139 单元/集成 + 37 E2E），100% PASS / 0 安全风险
- review 4-shot 总计：1 plan-eng + 1 phase-end spec + 1 final code + 1 security
- 项目级 rules.md 累积约 15 条（项目特定的，不是栈通用）

不同项目的绝对数据会差很多（语言不同、复杂度不同、测试基础设施不同），但「派单数 ≈ task 数 × 1.0~1.3」「review 4 次足够」「Per-Increment E2E Gate 必走」这几个比值/规律应保持。

## 必读 references（按 skill 名调用，不要拼绝对路径）

- TDD discipline → `Skill: superpowers:test-driven-development`
- 实施计划 → `Skill: superpowers:writing-plans`
- 派单 → `Skill: superpowers:subagent-driven-development`
- worktree → `Skill: superpowers:using-git-worktrees`
- plan review → `Skill: gstack-plan-eng-review`
- 完成验证 → `Skill: superpowers:verification-before-completion`
- 代码评审 → `Skill: superpowers:requesting-code-review` 或 `coderabbit:code-reviewer`
- 安全扫描 → `Skill: kdev-secure-coding:python-security-coding`（其他栈选对应 skill）
- 合并 → `Skill: superpowers:finishing-a-development-branch`
- 部署测试 → `Skill: gstack-qa`

（skill 内附 references 见文件顶部，不在此重复列出。）

## 触发示例

> "按 SOP 把 specs/001-X 跑通"
> "用 13 节点 SOP 自主完成这个需求"
> "实施这个 plan，端到端"
> "auto mode 跑完这个 feature"

## 接 kdev-core 底座（员工编排在 kdev-team）

本 SOP 的 13 节点编排由**开发工程师**员工执行，定义在 `plugins/kdev-team/`：
- 编排 agent `dev-engineer-orchestrator` 读 `kdev-team/orchestration/dev-engineer.node-table.yml`、用 kdev-core CLI 驱动引擎、按节点派 `dev-engineer-*` 业务 agent。
- 本 SKILL = **方法论 + skill 调用要求/模板参考**（agent 参考），**不充当编排器**（守 Q-008：编排=agent 按 node-table 调度）。
