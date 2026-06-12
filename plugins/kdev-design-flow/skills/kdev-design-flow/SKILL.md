---
name: kdev-design-flow
description: Use when 用户明确请求"把这个需求走一遍设计流程 / 帮我从需求到设计完整跑一遍 / 走 kdev 设计流程 / 完整需求分析+原型+设计 / 需求到方案一条龙 / 一站式跑需求分析"等表达，且明确希望产出 SR 文档 + AR 用户故事 + 高保真原型 + 概要详细设计这一整套交付物时触发；**或者用户要求恢复 / 继续 / resume 之前被中断的 kdev-design-flow 流程**（典型表达："slug 是 X，用 resume 接着跑"、"之前那个 Y 的设计流跑到一半被打断了"、`/kdev-design-flow --resume <slug>`）——这种场景**仍然属于本 skill**，由 SKILL.md 的"恢复模式"段处理，**不**该让 superpowers:executing-plans 接手。**SKIP**：用户只是在探讨想法 / 在判断是否值得做（应让 superpowers:brainstorming 或 office-hours 处理）；用户只想做单点设计或只要求其中一个产物（直接调对应 skill 即可）；用户在执行**已写好的 plan.md 实现计划文件**（应让 superpowers:executing-plans 处理 —— 注意区分：执行 plan.md ≠ resume 本 skill 的 flow-state.json）。本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（ai / both / human，默认 ai = Claude 自评）。
---

# kdev-design-flow Skill

把"原始需求 → SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计"这条工程链路固化为一个可复跑的 skill，串联已有 spec-kit 和 frontend-design 插件，并嵌入 3 个评审闸门避免方向漂移。

## 调用方式

通常通过 `/kdev-design-flow` 斜杠命令触发，不是 description 自动捕获（除非用户语气非常明确）。

## 本 SKILL 的定位（接底座后）

本 SKILL 是**需求设计方法论参考**（各 Stage 的 prompt/模板、Gate 判据、合并规则），**不再自带状态机、不充当编排器**。运行时编排由 kdev-team 的**通用 `kdev-flow-driver` skill**（顶层主控执行循环）按 `req-architect`（需求架构师）员工的 `orchestration/req-architect.node-table.yml` 驱动 **kdev-core 引擎**完成；状态落 feature-first 存储 `.kdev/features/<slug>/`（含 `handoffs/req-architect/` 产物）。

- 直接跑设计流：`/kdev-flow-driver req-architect --task "<需求>"`（通用 driver 路由 req-architect）。
- 本 SKILL 被 `req-architect-*` 业务 agent 当方法论参考读（怎么写 SR / 怎么调 frontend-design / 评审判据）。

## 工作流总览

| 阶段 | 用什么 | 输入 | 输出位置 |
|------|--------|------|----------|
| Stage 1 | 内置 prompt（references/stage1-sr-prompt.md） | 用户原始需求 | `.kdev/features/<slug>/handoffs/req-architect/stage-1-sr/iter-N.md` |
| Gate 1 | 评审机制 | SR 文档 | (PASS / FAIL + 反馈) |
| Stage 2 | `Skill` 调 `spec-kit:specify` | 上一步通过的 SR 文档 | `.kdev/features/<slug>/handoffs/req-architect/stage-2-ar/iter-N.md` |
| Stage 3 | `Skill` 调 `frontend-design:frontend-design` | 上一步通过的 AR 用户故事 | `.kdev/features/<slug>/handoffs/req-architect/stage-3-prototype/iter-N/` |
| Gate 2 | 评审机制 | AR + 原型 | (PASS / FAIL + 反馈) |
| Stage 4 | `Skill` 调 `spec-kit:plan` | 上一步通过的 AR + 原型 | `.kdev/features/<slug>/handoffs/req-architect/stage-4-plan/iter-N.md` |
| Gate 3 | 评审机制 | 设计方案 | (PASS / FAIL + 反馈) |
| Merge | 见 references/output-merge-rules.md | 各阶段最终通过版本 | `docs/design-flow/<slug>/` |

## 启动顺序

每次激活，按顺序执行：

### 步骤 0：参数解析

斜杠命令 `/kdev-design-flow` 注入 `$ARGUMENTS`，需要解析：
- 必传：`feature_name`（位置参数；中文/英文均可）
- 可选：`--review=ai|both|human`（默认 `ai`）
- 可选：`--resume <slug>`（带 slug 值；存在即"恢复模式"，跳过 feature_name 的 slugify 步骤）

如果 `--resume <slug>`：跳到"恢复模式"段（见下面"恢复"节），用传入的 slug 直接定位 `flow-state.json`。

### 步骤 1：依赖检测

检查 `Skill` 工具列表中是否存在：
- `spec-kit:specify`
- `spec-kit:plan`

任一缺失 → 立即中断，向用户输出：

```
❌ kdev-design-flow 需要 spec-kit 插件，但当前环境未安装。
请先运行：
    claude plugin install spec-kit
然后重新触发 /kdev-design-flow。
```

`frontend-design` 缺失 → 警告但允许用户选择是否继续（Stage 3 没它会跳到"手动占位"模式）。

### 步骤 2：初始化状态（接 kdev-core 引擎）

> 接底座后状态由 kdev-core 引擎管，不再用本 skill 自带的 flow_state。slug 仍由 `lib.slug.slugify(feature_name)` 生成（kdev-core 的 slug 由调用方直传）。

```bash
python3 -c "import sys; sys.path.insert(0,'${CLAUDE_PLUGIN_ROOT}'); from lib.slug import slugify; print(slugify('${feature_name}'))"
```

拿到 slug 后，由通用 kdev-flow-driver / req-architect 编排调 kdev-core 立项：

```bash
python3 -m kdev_core init design-flow <slug> --display-name "${feature_name}" --review-mode ${review_mode} --initial-node n0-clarify
```

节点机 / gate 推进 / 回流 / blocked 升人全由 kdev-core 引擎承载，见 `req-architect.node-table.yml`。记录返回的 `slug`，后续所有路径用它。

### 步骤 3：自动 .gitignore

> 接底座后运行时状态落 kdev-core 的 feature-first 存储 `.kdev/features/`，gitignore 也对齐到这里。

检查仓库根 `.gitignore`：

```bash
grep -qE "^/?\.kdev/features/?$" .gitignore || echo "/.kdev/features/" >> .gitignore
```

如果改了 `.gitignore`，提示用户"已自动追加 .gitignore（建议本次提交带上）"，但**不自动 commit**——交给用户决定何时提交。

### 步骤 4：进入主循环

按 Stage 1 → Gate 1 → Stage 2 → Stage 3 → Gate 2 → Stage 4 → Gate 3 → Merge 顺序执行。

---

## Stage 1: 初步需求分析

每次进入 Stage 1（包括 iter > 1 重试）：

1. Read `references/stage1-sr-prompt.md`
2. Read `references/stage1-sr-template.md`
3. 把模板中的 `{{user_input}}` / `{{slug}}` / `{{iter}}` / `{{feature_name}}` / `{{date}}` 占位符填好
4. 按 prompt 指示产出 SR 文档
5. Write 到 `.kdev/features/<slug>/handoffs/req-architect/stage-1-sr/iter-<iter>.md`
6. 进入 Gate 1

---

## 评审闸门通用机器（适用于 Gate 1/2/3）

> 接底座后**状态机不在本 SKILL 自跑**：当前在哪个节点 / 哪个 Gate / 第几次回流，都由 kdev-core 引擎据 `req-architect.node-table.yml` 维护；本段是**评审判据方法论**（怎么判 PASS/FAIL），由 req-architect agent 自评时用，结论通过编排的 `record-gate` 回报引擎，引擎据 node-table 的 `on_pass`/`on_reflow` 推进或回流。

每次到一个 Gate：

1. 从引擎状态拿 `review_mode`（立项时定，由 kdev-core 维护；本段的 `current_stage`/`current_iter` 上下文同样由引擎提供，本 SKILL 不再自增）
2. Read `references/review-gate-prompt.md`
3. 找到本 stage 对应的"成功标准"段
4. 把待评审产物（上一步的输出文件）读进来
5. 按 `review_mode` 分支：

### 5a. `--review=ai`（默认）

- Claude **自身**按 prompt 输出 VERDICT + UNCHECKED_CRITERIA + ISSUES + REVISIONS
- 把这段输出保存到 `.kdev/features/<slug>/handoffs/req-architect/stage-<N>/iter-<iter>-review.md`
- 把结论 `{"stage": N, "iter": iter, "verdict": "PASS"|"FAIL", "reviewer": "claude-self"}` 通过编排 `record-gate` 回报 kdev-core 引擎（历史落引擎 events，不再由本 SKILL 写 `flow-state.json`）

### 5b. `--review=both`

- 先按 5a 跑一遍 Claude 自评
- 然后用 `AskUserQuestion` 弹窗：
  - 问题: "Claude 自评结论：{{verdict}}。{{issues_summary if FAIL}}。你是否同意？"
  - 选项: "同意 Claude 判断" / "我有不同意见（手填）"
- 用户最终结论覆盖 Claude 的，写到 review.md，结论以 `reviewer: "claude-self+human"` 或 `reviewer: "human-override"` 通过 `record-gate` 回报引擎

### 5c. `--review=human`

- 直接用 `AskUserQuestion` 让用户判 PASS/FAIL + 给反馈
- 写到 review.md，结论以 `reviewer: "human"` 通过 `record-gate` 回报引擎

### 5d. PASS 后果（引擎承载）

- 编排 `record-gate` 报 PASS，引擎据 node-table 的 `on_pass` 推进到下一节点（不再由本 SKILL 在 `flow-state.json` 自增 `current_stage`）
- 继续下一 Stage

### 5e. FAIL 后果（引擎承载）

- 编排 `record-gate` 报 FAIL，引擎据 node-table 的 `on_reflow` 回流到当前 Stage 重跑（不再由本 SKILL 自增 `current_iter`）
- 新一轮会读上一轮的 review.md 作为反馈

### 5f. 连续 FAIL 达上限（引擎 escalate 升人）

- 连续 FAIL 达 3 次，引擎不再回流，自动 `escalate` 把节点标 `status=blocked` 升人（这是引擎的 review-gate cap 行为，不是本 SKILL 写 `aborted.md`）
- req-architect agent 此时该向用户汇报阻塞点：
  - 哪个 Gate / 哪条 criterion 始终绕不过去（读三次 review 找）
  - 候选处置：降低标准（改 `review-gate-prompt.md` 里的 criterion）、人工接管这个 stage、或终止 feature
  - 决定后由通用 kdev-flow-driver 走 `python3 -m kdev_core unblock` 解除 blocked 再续跑

---

## Stage 2: 进一步需求分析（spec-kit:specify）

1. Read 上一步通过的 SR 文档：`.kdev/features/<slug>/handoffs/req-architect/stage-1-sr/iter-<last_pass>.md`
2. 调 `Skill` 工具，name=`spec-kit:specify`，提示词模板：

```
我有一份 SR 级需求文档（已通过初步评审），请按 spec-kit:specify 流程把它细化成 AR 级用户故事。

输入 SR 文档：
<<<
{{paste sr doc content}}
>>>

输出落盘路径建议（spec-kit 自己决定即可）：
.kdev/features/<slug>/handoffs/req-architect/stage-2-ar/iter-<iter>.md

约束：
- 用户故事覆盖每个 SR
- 每个 user story 包含 acceptance criteria
- 不要重复 SR 文档里已经有的"显式不做"清单
```

3. spec-kit:specify 完成后，确认产物文件存在于 `.kdev/features/<slug>/handoffs/req-architect/stage-2-ar/iter-<iter>.md`。如果落到了别的位置（spec-kit 默认路径），用 `mv` 移过来。
4. **此处不评审**——Stage 2 + Stage 3 共用 Gate 2，等 Stage 3 跑完一起评。

## Stage 3: 原型设计（frontend-design）

> ⚠️ **反发散原则**：本 stage 容易"发散"——frontend-design 是通用前端设计 skill，不知道项目宪法。
> **MUST** 在调它之前把项目宪法里的前端规范 + 设计系统参考显式注入到 prompt 中；
> 不要假定 frontend-design 会自己去翻 `.specify/memory/constitution.md`。

### 步骤 0：抽取项目宪法 UI 约束（**不可跳过**）

1. **探测宪法文件**：检查 `.specify/memory/constitution.md` 是否存在
   - 存在 → Read 全文，提取所有提及以下关键词的段落（含上下文）：
     `前端 / 视觉 / 原型 / UI / UED / token / 栅格 / 字号 / 字阶 / 行高 / 间距 / 颜色 / 对比度 / 字体 / 画板 / 8px / 24 列 / hex / px`
   - 不存在 → `{{constitution_ui_block}}` 填入"⚠️ 本仓库未声明 `.specify/memory/constitution.md`，无项目级前端宪法约束。frontend-design 按通用 Web 设计最佳实践输出即可，但 Gate 2 评审将以宪法不存在为前提，不会扣分。"

2. **探测设计系统参考目录**（用 glob 扫，全部相对仓库根）：
   - `references/*ued*/`、`references/*UED*/`、`references/04-ued*/`
   - `references/*design-system*/`、`references/*design-tokens*/`、`docs/design-system/`
   - 任何在宪法中被显式引用为"前端实现唯一权威来源"的路径
   - 命中的所有目录路径列表 → 填入 `{{design_system_refs_block}}`，并明确告诉 frontend-design **Read 这些目录里的 AGENTS.md / README.md / tokens 文件后再动笔**
   - 都没命中 → `{{design_system_refs_block}}` 填入"（项目无独立设计系统目录；以宪法 UI 约束段为准）"

3. **抽取"前端实现唯一权威来源"路径**（若宪法显式声明，如 `references/04-ued6.0/`），追加进 `{{design_system_refs_block}}`，标注"⚠️ 宪法已声明此目录为唯一权威来源，原型 MUST 与其一致"。

### 步骤 1：填充并调用 frontend-design

1. Read `references/stage3-prototype-prompt.md`
2. 把模板中的 `{{ar_content}}` / `{{constitution_ui_block}}` / `{{design_system_refs_block}}` / `{{slug}}` / `{{iter}}` / `{{prev_iter}}` 占位符**全部填好**（不允许保留空占位符发给 frontend-design）
3. 调 `Skill` 工具，name=`frontend-design:frontend-design`，把**填充完的 prompt 全文**作为 args 传入
4. frontend-design 完成后，确认产物在 `.kdev/features/<slug>/handoffs/req-architect/stage-3-prototype/iter-<iter>/`，至少有 `index.html` + `self-check.md`。如果不在，用 `mv` 移过来；如果 `self-check.md` 缺失，在 Gate 2 评审输出里标 `stage3_selfcheck_missing: true`（由引擎 events 记录），Gate 2 评审会据此扣分但不阻断。
5. **进入 Gate 2**（共评 AR + 原型；评审 prompt 把 stage-2-ar 和 stage-3-prototype 的产物 + 步骤 0 抽出的宪法约束块都喂进去）

## Stage 4: 实现方案设计（spec-kit:plan）

1. Read Stage 2 的 AR 文档 + Stage 3 的原型 README/index.html
2. 调 `Skill` 工具，name=`spec-kit:plan`，提示词模板：

```
为下面这组 AR 用户故事 + 高保真原型，做完整的实现方案设计（概要 + 详细）。

用户故事：
<<<
{{paste ar}}
>>>

原型路径：
.kdev/features/<slug>/handoffs/req-architect/stage-3-prototype/iter-<last_pass>/

输出要求：
- 概要设计：架构图（Mermaid 也行）/ 模块划分 / 数据流
- 详细设计：关键接口签名 / 数据模型（schema）/ 关键算法或状态机
- 实现风险 ≥ 3 项 + 缓解
- 输出落盘到 `.kdev/features/<slug>/handoffs/req-architect/stage-4-plan/iter-<iter>.md`
```

3. spec-kit:plan 完成后，确认产物文件位置正确。
4. **进入 Gate 3**

## 通过 Gate 3 后：产物合并

1. Read `references/output-merge-rules.md`
2. 严格按规则执行（包括幂等性检查、`status = completed` 标记）
3. 完成后用一段中文向用户汇报：
   - 流程总耗时（从 kdev-core 引擎 events 的起止时间算）
   - 三个 Gate 各自跑了多少 iter（从引擎 events 聚合）
   - 最终交付物路径（`docs/design-flow/<slug>/`）

## 恢复模式（`--resume <slug>`）

接底座后断点续跑由 kdev-core 引擎承载：`python3 -m kdev_core resume design-flow <slug>`。

0. **先确认流程存在**——若引擎抛 `FlowStateError`（`no flow-state.json at .kdev/features/<slug>/`），向用户输出（**不要继续执行**）：

   ```
   ❌ 找不到 slug "<slug>" 的流程记录。
   预期路径：.kdev/features/<slug>/flow-state.json
   
   请检查：
   - slug 拼写是否正确（参考 .kdev/features/ 下的子目录名）
   - 是否在错误的工作目录下执行（应在项目根目录）
   
   如要新建流程，去掉 --resume 并提供 feature_name：
     /kdev-design-flow <feature_name>
   ```

   提示用户后停止本次调用。

1. resume 成功 → 由通用 kdev-flow-driver 从引擎给的 `current_node` 接着跑：
   - 正常进行中：引擎直接给回当前节点，driver 接着编排
   - `status == "blocked"`（review-gate 连续 FAIL 升人后的状态）：先按上面 5f 的处置向用户对齐，再 `python3 -m kdev_core unblock` 解除后续跑
   - `status == "completed"`：提示用户"该流程已完成，最终交付物在 docs/design-flow/<slug>/。如需重跑请新建（换 slug）"，然后停止

## 显式不做的事（v0.1）

- ❌ 不会主动去删 `.kdev/features/<slug>/`（即使流程完成）——保留迭代历史是 B 方案的训练数据
- ❌ 不会跨会话续跑评审中的 `AskUserQuestion`（所以 `both`/`human` 模式中途断会话，需要 `--resume` 重新进入这一 Gate）
- ❌ 不支持自定义 stage 顺序、跳过 stage、并行多 feature

