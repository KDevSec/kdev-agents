# kdev-coding-flow

编码阶段 SOP skill 集合 —— 把「从需求到上线」的端到端实施流程沉淀为可复用的方法论 skill，让 Claude 能在 Auto Mode 下自主跑完一个 spec/plan/prototype 三件套定义的复杂需求。

## 工作模式

技术栈无关的方法论层 + 项目级外置规则的双层设计：

- **Layer 1 · 通用方法论**（在 SKILL.md）：13 节点 SOP / 3 个人工判断 Gate / Bundle 策略 / 4-shot review 模型 / Auto Mode 适配。所有项目共用，永不变。
- **Layer 2 · 项目特定规则**（外置 `<repo>/docs/rules.md`）：项目命名约定 / 框架 fork bug / 版本错配 / 团队约定。每项目自维护，跑过程中持续积累。

栈通用约定（PEP8 / gofmt / FastAPI 路由顺序 / Express middleware 等）依赖**模型自带知识**，skill 不重复内置（避免造轮子 + 训练截止后追不上）。

## 触发模型

- **A · description 触发（主路径）**：用户说「按 SOP 跑」「端到端把 X 跑完」「实施这个 plan」「auto mode 跑完这个 feature」时，Claude 自动调用本 skill
- **B · 输入完备触发**：当主控面对一个含 `spec.md` + `plan.md` + `prototype` 三件套且已授权自主推进的实施任务时，主动启用

## 当前包含的 skill

| skill | 覆盖范围 | 状态 |
|-------|---------|------|
| [kdev-coding-flow](skills/kdev-coding-flow/SKILL.md) | 13 节点 SOP（关联度 / worktree / writing-plans / plan-review / 复杂度 / 派单 / TDD / 验证 / code review + E2E Gate / 安全扫描 / 合并 / 部署 + 金丝雀 / 收尾） + 3 人工 Gate + 4-shot review | ✅ v0.1.0 |

## 斜杠命令

| 命令 | 作用 |
|------|------|
| [`/kdev-coding-flow`](commands/kdev-coding-flow.md) | 显式触发本 skill；接受 `<specs-dir-or-feature-name>` + 可选 `--auto` / `--bundle-strategy` |

## 配套外置规范

skill 本身只放派单模板与示例，**蒸馏经验落项目 docs/**（不属 skill）：

- `docs/AI_Coding_SOP_编码开发阶段决策判据.md` — Gate / 派单分工 / Bundle / 4-shot review / 回流上限速查
- `docs/AI_Coding_SOP_编码开发阶段质量纪律.md` — 环境对齐 / TDD / 验证 / E2E Gate / 金丝雀 / 通用禁令 / Auto Mode 纪律速查

## 实测产能基线（Python / FastAPI / Vue / Playwright 项目）

23 task / 4 User Story / ~13k LOC 跑完 SOP：
- implementer 派单 21 次（含 5 次 fix）
- reviewer 派单 ~3 次
- 主控 commit 数 23
- 测试覆盖 176 条（139 单元/集成 + 37 E2E），100% PASS / 0 安全风险

不同栈/项目绝对数据会差很多，但「派单数 ≈ task 数 × 1.0~1.3」「review 4 次足够」「Per-Increment E2E Gate 必走」这几个比值/规律应保持。

## Eval baseline

`evals/iteration-baseline/` 含 2 轮 cross-stack eval 实测（Node + Express / Go CLI / Rust SDK 各 1 个 prompt），iter-2 极简版与 iter-1 通用化版均 100% pass，证明栈通用知识无需 skill 内置。

## 触发示例

> "按 SOP 把 specs/001-X 跑通"
> "用 13 节点 SOP 自主完成这个需求"
> "实施这个 plan，端到端"
> "auto mode 跑完这个 feature"
