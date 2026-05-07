# kdev-design-flow v0.1 设计文档

**日期**：2026-05-07
**作者**：1qljc + Claude
**状态**：设计已与用户对齐，待写实现计划

---

## 1. 背景与目标

把"原始需求 → 需求文档 → 用户故事 → 高保真原型 → 实现方案"这条工程流程固化成一个 Claude Code skill，让 AI 沿着标准链路推进，并在每个关键阶段嵌入评审闸门，避免方向漂移。

设计参考的流程图（用户提供）：

```
原始需求 → 初步需求分析并完善 → SR级需求文档 →[评审 #1]→
进一步需求分析（用户故事 AR级）→ 原型设计 → 高保真原型 →[评审 #2]→
实现方案设计 → 概要设计 + 详细设计 →[评审 #3]→ 输出
```

### 1.1 v0.1 目标

- 串联已有 skill（`superpowers:brainstorming`、`spec-kit:specify`、`frontend-design:frontend-design`、`spec-kit:plan`）成一条编排流水线
- 在 3 个评审闸门嵌入 AI/人工/混合三档可选的评审机制
- 中间产物与最终交付物分目录落盘，最终交付物 git 跟踪、中间产物本地保留

### 1.2 v0.1 显式不做（演进到 v1.0/B 方案再做）

- 评分历史累计、"数字员工塑造"反馈学习闭环
- 多 feature 并行
- Stage 跳过 / 自定义 Stage 顺序
- 评审 prompt 个性化配置

---

## 2. 需求决策记录

记录与用户对齐过的关键决策（避免后续遗忘）：

| # | 决策点 | 选定方案 | 理由 |
|---|--------|---------|------|
| 1 | 形态 | 先做轻量编排 skill（A），后续演进到完整 plugin（B） | 工作量可控，先验证流程跑通再加评分闭环 |
| 2 | spec-kit 缺口 | 声明 spec-kit 为前置依赖（A） | spec-kit 是 GitHub 官方维护的成熟产物，避免重复造轮子 |
| 3 | 触发模型 | 斜杠命令 + 极窄 description（C） | 主入口明确，自然语言兜底但不抢 brainstorming/office-hours 的场景 |
| 4 | 评审闸门 | 三档可选：ai / both / human，默认 ai（Claude 自评，无外部模型依赖） | v0.1 极简，B 方案再升级真二号意见 |
| 5 | "3" 循环 | 解读为"每个闸门最多重试 3 次" | 来自图中循环标注 |
| 6 | 产物落盘 | 中间过程进 `.kdev/design-flow/`（gitignored）；最终交付物进 `docs/design-flow/` （git 跟踪） | 公开/内部分离 |
| 7 | Stage 1 | 用轻量 prompt 自己写，不调 spec-kit.specify | 图里 SR 阶段是"快速分析"，不该上重型 skill |

---

## 3. 方案

### 3.1 包封装

- 插件名：`kdev-design-flow`
- 仓库位置：`plugins/kdev-design-flow/`（与 `kdev-memory`、`kdev-secure-coding` 平级）
- 内部结构：

```
plugins/kdev-design-flow/
├── plugin.json                          # version + metadata
├── CHANGELOG.md
├── README.md
└── skills/
    └── kdev-design-flow/
        ├── SKILL.md                     # 主入口
        └── references/
            ├── stage1-sr-prompt.md      # SR 级需求分析的 prompt 模板
            ├── stage1-sr-template.md    # SR 文档结构模板
            ├── review-gate-prompt.md    # 通用评审 prompt 模板（Claude 自评 + human 共用）
            └── output-merge-rules.md    # 中间产物如何合并到最终交付物的规则
```

### 3.2 触发模型

**斜杠命令**：
```
/kdev-design-flow [feature-name]
/kdev-design-flow --resume [feature-slug]
/kdev-design-flow --review=ai|both|human [feature-name]   # 默认 ai
```

`feature-name` 由用户给一个自然语言名字，skill 内部 slug 化（中文转拼音 + 连字符）。

**description 兜底**（写在 SKILL.md frontmatter）：

> 当用户明确请求"把这个需求走一遍设计流程 / 帮我从需求到设计完整跑一遍 / 走 kdev 设计流程 / 完整需求分析+原型+设计"等表达，且明确希望产出 SR 文档 / AR 用户故事 / 高保真原型 / 概要详细设计这一整套交付物时触发。**不**触发于：用户只是探讨一个想法、只想做单点设计、或还在判断是否值得做（应让 superpowers:brainstorming 或 office-hours 处理）。

### 3.3 流程编排

5 个 Stage，3 个评审闸门：

| Stage | 用什么 | 输入 | 输出 |
|-------|--------|------|------|
| 1. 初步需求分析 | 内置轻量 prompt（不调 skill） | 用户原始需求 | SR 级需求文档（`.kdev/design-flow/<slug>/stage-1-sr/iter-N.md`） |
| Gate #1 | 评审机制（见 3.4） | SR 文档 | 通过 / 反馈 |
| 2. 进一步需求分析 | `Skill` 调 `spec-kit:specify` | SR 文档 + 原始需求 | AR 级用户故事（`.kdev/design-flow/<slug>/stage-2-ar/iter-N.md`） |
| 3. 原型设计 | `Skill` 调 `frontend-design:frontend-design` | AR 用户故事 | 高保真原型 HTML（`.kdev/design-flow/<slug>/stage-3-prototype/iter-N/`） |
| Gate #2 | 评审机制 | AR + 原型 | 通过 / 反馈 |
| 4. 实现方案设计 | `Skill` 调 `spec-kit:plan` | AR + 原型 | 概要 + 详细设计（`.kdev/design-flow/<slug>/stage-4-plan/iter-N.md`） |
| Gate #3 | 评审机制 | 设计方案 | 通过 / 反馈 |

通过最后一个闸门后，skill 触发"产物合并"步骤，把通过的中间版本合并/复制到 `docs/design-flow/<slug>/` 作为最终交付。

### 3.4 评审闸门

**三档**：

| 模式 | 行为 |
|------|------|
| `--review=ai`（默认） | Claude 切换到评审 prompt，按 `references/` 里写死的硬性清单逐条对照产物，输出 PASS/FAIL + 不通过点。无外部模型依赖。 |
| `--review=both` | 先做 Claude 自评，把评审结论 + 建议作为预填内容用 `AskUserQuestion` 呈现给用户，用户最终拍板。 |
| `--review=human` | 直接用 `AskUserQuestion` 弹"通过 / 不通过 + 反馈"，跳过 AI 评审。 |

**评审 prompt 通用模板**（`references/review-gate-prompt.md`）：

```
你正在评审 [Stage 名] 阶段的产出。

[Stage 名] 的成功标准：
- ...
- ...

产物原文：
<<<
[insert artifact]
>>>

请按照成功标准给出：
1. PASS / FAIL
2. 如果 FAIL，列出具体不通过点（不超过 5 条，按优先级排序）
3. 如果 FAIL，给出修改建议（可被下一轮迭代直接采纳）
```

每个 Stage 的"成功标准"在 `references/` 里写死（不开放配置，v0.1 简化）。

**重试**：每个闸门最多 3 次。第 3 次仍 FAIL → 中断流程，落盘 `aborted.md`，让用户手动接管。

### 3.5 产物落盘

**中间过程目录（gitignored）**：

```
.kdev/design-flow/<feature-slug>/
├── flow-state.json              # {current_stage, current_iter, review_mode, ...}
├── stage-1-sr/
│   ├── iter-1.md                # 第一次产出
│   ├── iter-1-review.md         # Claude 自评 / 用户评审记录
│   ├── iter-2.md                # 第二次产出（如果不通过）
│   └── iter-2-review.md
├── stage-2-ar/
│   └── ...
├── stage-3-prototype/
│   └── iter-1/                  # frontend-design 产出整个目录
│       ├── index.html
│       └── ...
├── stage-4-plan/
│   └── ...
└── aborted.md                   # 仅当 3 次仍 FAIL 时存在
```

**最终交付目录（git 跟踪）**：

```
docs/design-flow/<feature-slug>/
├── 01-requirements.md           # SR + AR 合并
├── 02-prototype/                # 从 stage-3 通过版本复制
│   └── index.html
└── 03-design.md                 # 概要 + 详细设计合并
```

合并规则写在 `references/output-merge-rules.md`，v0.1 简单合并：把通过的最后一版 SR 和 AR 拼接、加大标题分节。

**自动 .gitignore**：skill 启动时检查仓库根 `.gitignore`，如果没有 `.kdev/design-flow/` 这一行就 append 它（写之前先用 grep 确认幂等）。

### 3.6 故障与中断

| 场景 | 行为 |
|------|------|
| spec-kit 未安装 | 启动时硬性中断，打印 `claude plugin install spec-kit` 安装命令 |
| Stage 中 Skill 调用失败 | 落盘当前 `flow-state.json`，提示用户 `--resume` 重试 |
| 用户中途 Ctrl+C | 同上 |
| 评审 3 次仍 FAIL | 写 `aborted.md`，附评审历史，提示用户手动接管 |
| `--resume` 调起 | 读 `flow-state.json`，从最近未完成的 stage 继续 |

### 3.7 与已有 skill 的关系

- `superpowers:brainstorming`：**不直接调用**，但 SR 阶段的 prompt 会借鉴它的"逐步澄清"思路（精简版）
- `spec-kit:specify`：Stage 2 直接 `Skill` 调
- `frontend-design:frontend-design`：Stage 3 直接 `Skill` 调
- `spec-kit:plan`：Stage 4 直接 `Skill` 调
- `kdev-memory`：可选——如果用户已经在用 kdev-memory，skill 完成时把关键决策落到 `.kdev/memory/` 决策日志（v0.1 仅检测存在性，不强制依赖）

> **关于 AI 评审者**：v0.1 的 AI 评审 = Claude 自评（同一会话切换 prompt），不引入 codex / 其他外部模型，避免给 v0.1 偷加依赖。B 方案再升级成真二号意见（codex / 真人 / 其他模型可选）。

---

## 4. 验收标准（v0.1）

- 在一个安装了 `spec-kit` 的项目上，`/kdev-design-flow 用户登录功能` 能完整跑完 5 个 Stage、3 个评审闸门，最终在 `docs/design-flow/yong-hu-deng-lu-gong-neng/` 下生成 3 份交付物
- 中间产物完整落在 `.kdev/design-flow/yong-hu-deng-lu-gong-neng/`，并已被 `.gitignore` 排除
- 三档 `--review` 模式（ai / both / human）都能跑通，默认 `ai` 时无任何弹窗打扰
- 评审第 3 次仍 FAIL 时正确中断 + 落盘 `aborted.md`
- `--resume` 能从中断的 stage 继续，不丢前面已通过的产物
- spec-kit 未安装时启动直接中断 + 给出安装命令

---

## 5. 风险与开放问题

| 风险 | 缓解 |
|------|------|
| `Skill` 工具能否真正以编程方式调用其他 skill 并拿回结构化输出？ | 写实现计划阶段需要先做 spike：跑一个最小例子，确认 `Skill` 调用 `spec-kit:specify` 能拿到产物文件路径 |
| **Claude 自评的自我确认偏差** —— 同一个 LLM 既写产物又评审，可能放过自己写的弱点 | 评审 prompt 写成硬性清单逐条对照（`references/review-gate-prompt.md`），不留自由发挥空间；B 方案引入真二号意见根治 |
| Claude 评审产出的格式不稳定 | 评审 prompt 要求严格 `PASS` / `FAIL` + 列表格式，解析失败时退化为 human 模式让用户拍板 |
| frontend-design 输出的目录结构未必稳定 | Stage 3 落盘时整目录复制，不解析内部结构 |
| 中文 feature 名 slug 化质量 | v0.1 简单 hashlib + 时间戳兜底，避免拼音库依赖 |

---

## 6. 后续演进路径（B 方案预留）

v0.1 的产物（`flow-state.json`、`iter-N-review.md`）已为 v1.0 评分闭环留好钩子：

- 每次评审记录已包含结构化 PASS/FAIL + 不通过点列表，可直接喂训练/统计
- `flow-state.json` 累计每个 feature 的迭代次数，可作"AI 一次通过率"指标的原始数据
- `.kdev/design-flow/` 跟 `kdev-memory` 的 `.kdev/memory/` 同栏，未来合并成统一"工程记忆"体系
