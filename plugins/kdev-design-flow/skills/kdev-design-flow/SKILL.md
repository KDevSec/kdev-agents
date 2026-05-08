---
name: kdev-design-flow
description: Use when 用户明确请求"把这个需求走一遍设计流程 / 帮我从需求到设计完整跑一遍 / 走 kdev 设计流程 / 完整需求分析+原型+设计 / 需求到方案一条龙 / 一站式跑需求分析"等表达，且明确希望产出 SR 文档 + AR 用户故事 + 高保真原型 + 概要详细设计这一整套交付物时触发；**或者用户要求恢复 / 继续 / resume 之前被中断的 kdev-design-flow 流程**（典型表达："slug 是 X，用 resume 接着跑"、"之前那个 Y 的设计流跑到一半被打断了"、`/kdev-design-flow --resume <slug>`）——这种场景**仍然属于本 skill**，由 SKILL.md 的"恢复模式"段处理，**不**该让 superpowers:executing-plans 接手。**SKIP**：用户只是在探讨想法 / 在判断是否值得做（应让 superpowers:brainstorming 或 office-hours 处理）；用户只想做单点设计或只要求其中一个产物（直接调对应 skill 即可）；用户在执行**已写好的 plan.md 实现计划文件**（应让 superpowers:executing-plans 处理 —— 注意区分：执行 plan.md ≠ resume 本 skill 的 flow-state.json）。本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（ai / both / human，默认 ai = Claude 自评）。
---

# kdev-design-flow Skill

把"原始需求 → SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计"这条工程链路固化为一个可复跑的 skill，串联已有 spec-kit 和 frontend-design 插件，并嵌入 3 个评审闸门避免方向漂移。

## 调用方式

通常通过 `/kdev-design-flow` 斜杠命令触发，不是 description 自动捕获（除非用户语气非常明确）。

## 工作流总览

| 阶段 | 用什么 | 输入 | 输出位置 |
|------|--------|------|----------|
| Stage 1 | 内置 prompt（references/stage1-sr-prompt.md） | 用户原始需求 | `.kdev/design-flow/<slug>/stage-1-sr/iter-N.md` |
| Gate 1 | 评审机制 | SR 文档 | (PASS / FAIL + 反馈) |
| Stage 2 | `Skill` 调 `spec-kit:specify` | 上一步通过的 SR 文档 | `.kdev/design-flow/<slug>/stage-2-ar/iter-N.md` |
| Stage 3 | `Skill` 调 `frontend-design:frontend-design` | 上一步通过的 AR 用户故事 | `.kdev/design-flow/<slug>/stage-3-prototype/iter-N/` |
| Gate 2 | 评审机制 | AR + 原型 | (PASS / FAIL + 反馈) |
| Stage 4 | `Skill` 调 `spec-kit:plan` | 上一步通过的 AR + 原型 | `.kdev/design-flow/<slug>/stage-4-plan/iter-N.md` |
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

### 步骤 2：初始化状态

```bash
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from lib.slug import slugify
from lib.flow_state import init_state
slug = slugify('${feature_name}')
init_state(Path.cwd(), slug, review_mode='${review_mode}', feature_name='${feature_name}')
print(slug)
"
```

记录返回的 `slug`，后续所有路径用它。

### 步骤 3：自动 .gitignore

检查仓库根 `.gitignore`：

```bash
grep -qE "^/?\.kdev/design-flow/?$" .gitignore || echo "/.kdev/design-flow/" >> .gitignore
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
5. Write 到 `.kdev/design-flow/<slug>/stage-1-sr/iter-<iter>.md`
6. 进入 Gate 1

---

## 评审闸门通用机器（适用于 Gate 1/2/3）

每次到一个 Gate：

1. 从 `flow-state.json` 读 `review_mode`、`current_stage`、`current_iter`
2. Read `references/review-gate-prompt.md`
3. 找到本 stage 对应的"成功标准"段
4. 把待评审产物（上一步的输出文件）读进来
5. 按 `review_mode` 分支：

### 5a. `--review=ai`（默认）

- Claude **自身**按 prompt 输出 VERDICT + UNCHECKED_CRITERIA + ISSUES + REVISIONS
- 把这段输出保存到 `.kdev/design-flow/<slug>/stage-<N>/iter-<iter>-review.md`
- 在 `flow-state.json` 的 `history` 数组追加：
  `{"stage": N, "iter": iter, "verdict": "PASS"|"FAIL", "reviewer": "claude-self"}`

### 5b. `--review=both`

- 先按 5a 跑一遍 Claude 自评
- 然后用 `AskUserQuestion` 弹窗：
  - 问题: "Claude 自评结论：{{verdict}}。{{issues_summary if FAIL}}。你是否同意？"
  - 选项: "同意 Claude 判断" / "我有不同意见（手填）"
- 用户最终结论覆盖 Claude 的，写到 review.md，记录 `reviewer: "claude-self+human"` 或 `reviewer: "human-override"`

### 5c. `--review=human`

- 直接用 `AskUserQuestion` 让用户判 PASS/FAIL + 给反馈
- 写到 review.md，记录 `reviewer: "human"`

### 5d. PASS 后行为

- 在 `flow-state.json` 设 `current_stage += 1`, `current_iter = 1`
- 继续下一 Stage

### 5e. FAIL 后行为

- 在 `flow-state.json` 设 `current_iter += 1`
- 如果 `current_iter > 3`：进入"中断"分支
- 否则：回到当前 Stage，重新跑（新 iter 会读上一轮的 review.md 作为反馈）

### 5f. 中断（3 次仍 FAIL）

- 在 `flow-state.json` 设 `status = "aborted"`, `aborted_at = now`, `aborted_reason = "review failed 3 times at gate <N>"`
- Write `.kdev/design-flow/<slug>/aborted.md`：

```markdown
# Aborted: {{feature_name}}

**Slug:** {{slug}}
**Aborted at:** {{date}} (Gate {{N}})
**Reason:** review FAILed 3 times in a row

## 最后一轮的 review

(粘贴 iter-3-review.md 的全文)

## 三次迭代的产物

- iter-1: `.kdev/design-flow/{{slug}}/stage-{{N}}/iter-1.md`
- iter-2: ...
- iter-3: ...

## 接下来怎么办

1. 读三次 review，找到 Claude 始终绕不过去的那条 criterion
2. 决定：是降低标准（修改 review-gate-prompt.md 里的 criterion）、还是手动接管这个 stage、还是终止 feature
3. 决定后用 `/kdev-design-flow --resume {{slug}}` 继续（注意先把 flow-state 里 status 改回 in_progress）
```

- 通知用户中断 + 给出 aborted.md 路径，停止流程。

---

## Stage 2: 进一步需求分析（spec-kit:specify）

1. Read 上一步通过的 SR 文档：`.kdev/design-flow/<slug>/stage-1-sr/iter-<last_pass>.md`
2. 调 `Skill` 工具，name=`spec-kit:specify`，提示词模板：

```
我有一份 SR 级需求文档（已通过初步评审），请按 spec-kit:specify 流程把它细化成 AR 级用户故事。

输入 SR 文档：
<<<
{{paste sr doc content}}
>>>

输出落盘路径建议（spec-kit 自己决定即可）：
.kdev/design-flow/<slug>/stage-2-ar/iter-<iter>.md

约束：
- 用户故事覆盖每个 SR
- 每个 user story 包含 acceptance criteria
- 不要重复 SR 文档里已经有的"显式不做"清单
```

3. spec-kit:specify 完成后，确认产物文件存在于 `.kdev/design-flow/<slug>/stage-2-ar/iter-<iter>.md`。如果落到了别的位置（spec-kit 默认路径），用 `mv` 移过来。
4. **此处不评审**——Stage 2 + Stage 3 共用 Gate 2，等 Stage 3 跑完一起评。

## Stage 3: 原型设计（frontend-design）

1. Read 上一步的 AR 用户故事
2. 调 `Skill` 工具，name=`frontend-design:frontend-design`，提示词模板：

```
为下面这组用户故事设计一个高保真原型（HTML/CSS/必要的 JS），目标是评审用，不是生产用。

用户故事：
<<<
{{paste ar content}}
>>>

约束：
- 可在浏览器直接打开（单 HTML 文件或带 index.html 的目录）
- 涵盖核心交互路径（不需要每个 edge case 都画）
- 视觉语言要和产品语境匹配（不要是默认浏览器原生灰色按钮）
- 不要内嵌真实凭证 / 内部 URL / 敏感数据
- 输出落盘到 `.kdev/design-flow/<slug>/stage-3-prototype/iter-<iter>/`
```

3. frontend-design 完成后，确认产物在 `.kdev/design-flow/<slug>/stage-3-prototype/iter-<iter>/`，至少有 `index.html`。如果不在，用 `mv` 移过来。
4. **进入 Gate 2**（共评 AR + 原型；评审 prompt 把 stage-2-ar 和 stage-3-prototype 的产物都喂进去）

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
.kdev/design-flow/<slug>/stage-3-prototype/iter-<last_pass>/

输出要求：
- 概要设计：架构图（Mermaid 也行）/ 模块划分 / 数据流
- 详细设计：关键接口签名 / 数据模型（schema）/ 关键算法或状态机
- 实现风险 ≥ 3 项 + 缓解
- 输出落盘到 `.kdev/design-flow/<slug>/stage-4-plan/iter-<iter>.md`
```

3. spec-kit:plan 完成后，确认产物文件位置正确。
4. **进入 Gate 3**

## 通过 Gate 3 后：产物合并

1. Read `references/output-merge-rules.md`
2. 严格按规则执行（包括幂等性检查、`status = completed` 标记）
3. 完成后用一段中文向用户汇报：
   - 流程总耗时（用 `created_at` - `completed_at` 计算）
   - 三个 Gate 各自跑了多少 iter（从 history 聚合）
   - 最终交付物路径（`docs/design-flow/<slug>/`）

## 恢复模式（`--resume <slug>`）

如果用户带 `--resume <slug>`：

0. **先确认 flow-state.json 存在**——尝试 `read_state(workspace, slug)`。如果抛 `FlowStateError`（文件不存在），向用户输出（**不要继续执行**）：

   ```
   ❌ 找不到 slug "<slug>" 的流程记录。
   预期路径：.kdev/design-flow/<slug>/flow-state.json
   
   请检查：
   - slug 拼写是否正确（参考 .kdev/design-flow/ 下的子目录名）
   - 是否在错误的工作目录下执行（应在项目根目录）
   
   如要新建流程，去掉 --resume 并提供 feature_name：
     /kdev-design-flow <feature_name>
   ```

   提示用户后停止本次调用。

1. Read `flow-state.json`（已确认存在），按 `status` 分支：
   - `status == "in_progress"`：正常继续——读 `current_stage` + `current_iter`，跳到主循环对应位置接着跑
   - `status == "aborted"`：提示用户"流程被标记为 aborted，先手动改 flow-state.json 里 status 字段（aborted → in_progress）才能继续"，然后停止
   - `status == "completed"`：提示用户"该流程已完成，最终交付物在 docs/design-flow/<slug>/。如需重跑，请先删除或重命名 flow-state.json"，然后停止

## 显式不做的事（v0.1）

- ❌ 不会主动去删 `.kdev/design-flow/<slug>/`（即使流程完成）——保留迭代历史是 B 方案的训练数据
- ❌ 不会跨会话续跑评审中的 `AskUserQuestion`（所以 `both`/`human` 模式中途断会话，需要 `--resume` 重新进入这一 Gate）
- ❌ 不支持自定义 stage 顺序、跳过 stage、并行多 feature

