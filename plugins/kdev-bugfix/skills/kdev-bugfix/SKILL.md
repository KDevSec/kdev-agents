---
name: kdev-bugfix
description: Bug 修复 8 步流程：禅道拉取 / 直接对话 → openspec proposal/design/specs/tasks → 根因投资（Iron Law） → RED 回归测试 → GREEN 最小修复 → 验证闸门 → 评审闸门（AI/multi/human/both） → kdev-commit → 禅道 active→resolved 回写。autodetect `<repo>/openspec/` 决定模式；`ZENTAO_API_URL` + 认证（session-auth 主路径 / PAT 可选）触发禅道源。强制纪律：根因未定不许下笔；先 RED 再 GREEN；type-check + lint + 测试 + openspec validate 全绿；任一 reviewer FAIL 即 FAIL。P0 / 鉴权 / 跨模块 / 数据迁移 / 文件>3 强制升级 multi。`--dry-run` 跑完 8 步但不动持久状态（演练 / 教学 / wet-test 评估）。Use when 用户说"修个 bug"、"X 报错了"、"线上挂了"、"崩了"、"复现 / hotfix / 拉禅道 bug XXX / issue #N / dry-run / 演练一下"，或描述具体故障症状（500 / stack trace / 数据不对 / 退化 / 偶发）。Skip：新增功能（kdev-coding-flow）；探讨是否值得做（superpowers:brainstorming）；大规模重构。
---

# kdev-bugfix skill

## 这个 skill 负责什么

**一件事**：把"用户报了一个 bug"或"禅道里有条 bug 要修"翻成可复跑、可审计的修复链路，落产物 + 可选 bug-tracker 状态同步。

**双源 intake**：
- 禅道拉取：`/kdev-bugfix --from-zentao <id>` 或"拉禅道 bug 12345"
- 直接对话：用户口头描述 / 贴 stack trace

**不管**：新增需求（→ kdev-coding-flow）/ commit 身份（→ kdev-commit）/ 安全规则细节（→ kdev-secure-coding）/ 大规模重构。

## 核心原则（违反任一即停）

1. 根因未定 → 不许下笔修（委派 `superpowers:systematic-debugging`）
2. 先 RED 再 GREEN，测试**真的失败**才算 RED 成立
3. 最小变更，不顺手重构周围代码
4. 验证闸门全绿：type-check + lint + 测试 + `openspec validate`（OpenSpec 模式）
5. 评审闸门 PASS：默认 AI 自评；安全/跨模块/数据迁移类强制升 multi
6. 根因留档到 design.md `Root_Cause`（或纯模式 fix.md）

## 双轨产物布局

```
检查 <repo>/openspec/
  ├── 存在  → OpenSpec 模式：openspec/changes/<bug-id>/{proposal.md, design.md, [specs/], tasks.md}
  └── 不存在 → 纯模式：docs/bugfix/<bug-id>/{bug-report.md, fix.md}
```

flag 覆盖：`--openspec`（强制开 + auto init）/ `--no-openspec`（强制纯模式）

## `--dry-run` 模式

`--dry-run` 让 8 步**完整跑一遍但不动持久状态**——不写产物、不动 src/、不动 git、不动禅道。

详见 [dry-run-mode.md](references/dry-run-mode.md)。每步行为差异速查：

| 步骤 | 真跑 | dry-run |
|------|------|---------|
| 1 Intake | 拉禅道 / 判模式 / 严重度 | 全部照常（只读，不污染）|
| 2 Proposal | `openspec new change` + 写 proposal.md | 不写文件；inline 显示 proposal.md 完整内容 + 输出 `🔵 DRY-RUN \| step 2: 将创建 ...` |
| 3 复现 + 根因 | 跑复现 + systematic-debugging | 照常（只读不污染） |
| 4 Design + RED | design.md + 回归测试 + 实测失败 | inline 显示 design.md；回归测试**不写不实测**，print 测试内容 + 预期失败原因 |
| 5 Tasks + GREEN + 闸门 | 写 tasks.md + 改 src + 跑闸门 | tasks.md inline；src 改动用 unified diff print；闸门跳过 |
| 6 评审 | 评 design + diff | 评 plan（design.md 修复方案 + tasks 完整性），prompt 末尾追加 `dry-run plan-review` 提示 |
| 7 Validate + Commit | `openspec validate` + `kdev-commit` | 都跳过；commit message 用代码块 print |
| 8 后置 | 禅道 PUT resolve | 不调；print 完整 curl（token redacted）|

**底线保证**：不写产物 / 不动 src / 不动 git / 不 commit / 不调禅道写接口。

**重要警告**：dry-run **跳过 RED 实测**，失去"watch it fail"保证——真跑前不要把 dry-run 结论当成"方案可行"的最终证据。

## 8 步主流程

```
1. Intake & Triage  ──┐  禅道拉取 / 直接对话；生成 bug-id；判模式 + 严重度 + bug_source
                      │
2. Proposal           │  openspec new change → proposal.md（禅道源 seed 字段）
                      │
3. 复现 + 根因         │  Iron Law：根因不明禁止进 4
                      │
4. Design + RED       │  design.md 落根因 → 回归测试 RED
                      │
5. Tasks + GREEN + 闸门│  tasks.md → 最小修复 + verification-before-completion
                      │
6. 评审闸门            │  AI / multi / human / both；任一 FAIL 回 5
                      │
7. Validate + Commit  │  openspec validate → kdev-commit
                      │
8. 后置动作            │  bug_source=zentao → 禅道 active→resolved
                      ─┘
```

### 步骤 1 · Intake & Triage

**1.1 判 bug_source**

| 触发 | bug_source |
|------|-----------|
| `--from-zentao <id>` 或"拉禅道 bug XXX" | `zentao` |
| 其他 | `direct` |

**禅道源**（详见 [zentao-integration.md §0-§1](references/zentao-integration.md)）：

```bash
# 配置：<repo>/.kdev/zentao.env（gitignored）
# 关键变量：ZENTAO_API_URL / ZENTAO_INSECURE_TLS / ZENTAO_AUTH_MODE
# 第一次跑必跑 §0 启动探测（URL 路径前缀 + 认证生效）
# 探测失败立即停下让用户修配置，不假装走 direct 模式

# bug 字段映射详见 §1，关键陷阱：
#   优先级字段是 .pri 不是 .priority（22.x 字段命名陷阱）
#   user 字段嵌套在 .profile.* 下不是顶层
```

**1.2 生成 bug-id**

- 禅道源：默认 `zentao-<id>`
- 直接源：用户给了就用；从症状生成 kebab-case slug
- 校验：`^[a-z0-9][a-z0-9-]{2,60}$`

**1.3 判模式 + 严重度（Gate-A）**

| 严重度 | 触发 | 走法 |
|--------|------|------|
| P0 | 线上挂 / 数据损坏 / 安全漏洞 / 全量影响 / **禅道 .severity=1** | hotfix 快路径 |
| P1 | 核心功能局部失效 / 性能严重退化 / **.severity=2-3** | 全流程 |
| P2 | 边缘 case / UI 小问题 / 低频偶发 / **.severity=4** | 全流程 |

报告 `<bug-id>` + bug_source + 模式 + 严重度，确认后继续。

### 步骤 2 · 创建容器 + Proposal

```bash
# OpenSpec 模式
openspec new change <bug-id> --description "<Symptom 一句话>"
openspec instructions proposal --change <bug-id>
```

按 upstream prompt + [fields-proposal.md](references/fields-proposal.md) 填 proposal.md（Why / What Changes / Capabilities + Bug Context 扩展段）。

**禅道源**：步骤 1.1 抓到的字段自动 seed 进 Bug Context；frontmatter 加 `bug_source: zentao` + `zentao_bug_id` 等元数据。

**纯模式**：跳过 `openspec` 命令，`mkdir -p docs/bugfix/<bug-id>` 后按 [fields-pure-mode.md §A](references/fields-pure-mode.md) 写 bug-report.md。

**信息不全就停下问用户**——禅道 steps 字段经常含糊，不要硬填。

### 步骤 3 · 复现 + 根因投资

**3.1 复现**：按 Steps_to_Reproduce 走，成功记 Actual_Behavior；失败**不假修**，返用户要详情（禅道源则在禅道下 comment）。

**3.2 根因投资**：委派 `Skill: superpowers:systematic-debugging`。**Iron Law**：根因不明禁止进步骤 4。判据（满足至少 2 条）：

- 能精确指出"哪行代码 + 哪个条件 + 为什么 trigger"
- 能解释为什么本地复现/不复现、为什么只在 X 环境出
- 能预测"如果改 Y，会不会触发同类问题"

口头根因结论给用户确认后**才**进 4。

### 步骤 4 · Design + RED

**4.1 design.md**：`openspec instructions design --change <bug-id>` 拿 upstream prompt，按 [fields-design.md](references/fields-design.md) 填：Root_Cause / Fix_Description / Alternatives_Considered / Risks / Spec_Impact。

**4.2 Gate-B（Spec_Impact）**：命中 → `openspec instructions specs` 写 delta，按 [fields-specs.md](references/fields-specs.md)；不命中 → 跳过。

**4.3 Gate-B（安全）**：鉴权 / 用户输入 / 加密 / 文件上传 / 反序列化 / supply chain → 委派 `Skill: kdev-secure-coding:python-security-coding`（或对应栈）。

**4.4 RED**：委派 `Skill: superpowers:test-driven-development`。硬规则：

- 测试**先于**修复代码写出来
- 跑一遍**必须真的失败**，原因**直接对准根因**
- 反模式（发现立即回 3）：先写修复再补测试 / 测试 RED 因为 import 错 / 只精确卡修复点不防御等价类

### 步骤 5 · Tasks + GREEN + 验证闸门

**5.1 tasks.md**（OpenSpec 模式）：按 [fields-tasks.md](references/fields-tasks.md) 填 T1–T12 模板。纯模式跳过，用 TodoWrite 内部跟踪。

**5.2 GREEN**：判据——改动文件 ≤ 3 / 删改远少于新加 / 不顺便修 lint warning。

**5.3 验证闸门（必须全绿，委派 `superpowers:verification-before-completion`）**：

1. 回归测试 PASS（RED→GREEN）
2. 既有单元/集成测试全量 PASS
3. type-check PASS（mypy / tsc / 按栈）
4. lint PASS（ruff / eslint / 按栈）
5. （如适用）安全复核 8 类清单 PASS
6. （Gate-C）业务关键入口 E2E PASS——见 [kdev-coding-flow 节点 12](../../../kdev-coding-flow/skills/kdev-coding-flow/SKILL.md)

任一 ❌ 回 5.2 改代码（**不**注释 / skip 测试）。

### 步骤 6 · 评审闸门

**默认 `--review-mode=ai`**。详见 [review-modes.md](references/review-modes.md)。

**强制升级到 multi**（即便传 `ai`）：

- P0 严重度
- 鉴权 / 权限 / 会话相关
- 跨模块状态协调 / 数据迁移
- 修改文件 > 3

**4 档**：

| 模式 | 评审员 |
|------|--------|
| `ai`（默认） | `superpowers:code-reviewer` |
| `multi` | AI 自评 + 派 subagent（opus）独立评审，prompt 模板见 [review-modes.md §2](references/review-modes.md) |
| `human` | 主 Claude 输出摘要 → 暂停等用户 `APPROVE` / `REJECT <理由>` / `APPROVE WITH CHANGES <要求>` |
| `both` | multi → human 串行 |

**保守裁决**：任一 reviewer FAIL/REJECT 即 FAIL，**不**投票。

**落档**：评审结论写到 design.md（纯模式 fix.md）末尾 `## Review_Decisions` 段，格式见 [review-modes.md §5](references/review-modes.md)。

### 步骤 7 · Validate + Commit

```bash
# OpenSpec 模式
openspec validate <bug-id>   # schema 校验，红了按报错补字段
```

**Commit**（委派 `Skill: kdev-commit`）：

- 分支 `fix/<bug-id>`（已在 feature 分支问用户复用或新开）
- message 模板：

  ```
  fix: <Symptom 一句话> (#<bug-id>)

  Root cause: <Root_Cause 一两句压缩>
  Regression test: <测试文件路径或测试名>
  Reviewers: AI (PASS), multi-agent (PASS/N/A), human (PASS/N/A)

  Refs: openspec/changes/<bug-id>/   # 或 docs/bugfix/<bug-id>/
  Zentao: #<bug-id>                  # 仅 bug_source=zentao
  ```

### 步骤 8 · 后置动作

**8.1 禅道状态回写**（仅 `bug_source=zentao` 且无 `--no-zentao-update`）：

调禅道 API `active → resolved`，详见 [zentao-integration.md §3](references/zentao-integration.md)。

失败兜底：API 错（401/403/5xx）→ STDOUT 输出手动指引（按 [§5](references/zentao-integration.md)），**不阻塞**——代码已 commit。

**8.2 终态报告**：bug-id / 来源 / 模式 / 严重度 / 根因 / 改动文件 / 任务清单 / 评审 / 产物路径 / commit / 禅道状态 / Spec 影响。

## P0 hotfix 快路径

| 步骤 | 压缩 |
|------|------|
| 2 Proposal | 先 Symptom + Actual + Environment 三段，其余 7 前补 |
| 3 根因 | 走，允许复现+定位并行 |
| 4 RED | **不能跳**；minimal repro test 即可，broader 等价类 7 前补 |
| 5 GREEN 验证闸门 | **不能跳** |
| 6 评审 | **自动升级 multi**（P0 不允许单 AI） |
| 7 commit | 可先发，design/tasks 合并前补齐 |
| 8 禅道回写 | 自动；失败兜底手动指引 |

绝对不允许跳：回归测试 / type-check + lint / root cause / `openspec validate` / 评审（至少 AI）。

## Auto Mode + 异常处理

| 场景 | 处理 |
|------|------|
| 模式 / 严重度 / 评审升档判定 | autodetect，不询问 |
| 禅道 token 缺失 / 401 / 探测失败 | 明确告诉用户改 .env，**不**降级 direct |
| 复现失败 | 禅道源在禅道下 comment 要详情；直接源返用户。**不假修** |
| 根因 Iron Law | 不可降；投资完不口头确认，直接写 design.md 草稿 |
| 回归测试 RED 时通过 | 测试没卡根因，回 4.4 重写 |
| 修复让别的测试变红 | 影响超预期，回 3 复盘或 5.2 收窄 |
| 评审员打架（AI APPROVE / subagent REJECT） | 保守，**任一 FAIL 即 FAIL**，不投票 |
| `openspec validate` 失败 | 按报错精确补字段，**不**绕开 |
| commit hook deny | 按 deny reason 重试，**不**绕开 |
| 禅道 8.1 失败 | 输出手动指引继续，**不阻塞**流程 |
| Spec_Impact 命中 | 本 PR 只补救代码 + design.md 记录；spec 真改另起 `kdev-change` |
| 任何闸门红 | 输出 `BLOCKED: <原因>`，**不**死循环重试 |

## 不要做的事

- 不要在没复现的情况下修代码
- 不要在没找到根因之前写回归测试
- 不要跳 RED 直接写修复
- 不要扩大 bug 修复范围（其他问题写 Follow_Up，另开 issue）
- 不要在评审 FAIL / `openspec validate` 红时声明完成
- 不要假装禅道源——拿不到 token 就明说，不降级 direct
- 不要把 spec 真实修改塞进 bugfix PR
- 不要混用模式（同一 bug 写 openspec/changes/ 又写 docs/bugfix/）
- **不要把 dry-run 结论当成"方案可行"的最终证据**——dry-run 跳过 RED 实测，"watch it fail"保证缺席；真跑前必须去掉 `--dry-run` 重做一次
- **不要在真实 bug 修复时挂 `--dry-run`**——dry-run 用于演练 / 教学 / wet-test 评估，不是缩水版 bugfix

## 必读 references

| 用途 | skill 名 |
|------|----------|
| 根因投资 | `superpowers:systematic-debugging` |
| TDD red→green | `superpowers:test-driven-development` |
| 完成验证 | `superpowers:verification-before-completion` |
| 评审 | `superpowers:code-reviewer` |
| 提交 | `kdev-commit` |
| 安全复核（按需） | `kdev-secure-coding:python-security-coding` |
| spec 缺陷重做 | `kdev-coding-flow` |

skill 内附：

- 字段速查表（按 artifact 拆分）：
  - [references/fields-proposal.md](references/fields-proposal.md) — OpenSpec proposal.md Bug Context + frontmatter
  - [references/fields-design.md](references/fields-design.md) — OpenSpec design.md Root_Cause / Fix / Risks / Spec_Impact / Review_Decisions
  - [references/fields-specs.md](references/fields-specs.md) — OpenSpec specs/ spec delta（仅 Spec_Impact 命中时写）
  - [references/fields-tasks.md](references/fields-tasks.md) — OpenSpec tasks.md T1–T12 模板
  - [references/fields-pure-mode.md](references/fields-pure-mode.md) — 纯模式 bug-report.md + fix.md 字段
  - [references/fields-mapping.md](references/fields-mapping.md) — 模式交叉对照 + 迁移命令
- [references/zentao-integration.md](references/zentao-integration.md) — 禅道 API curl 模板、配置、§0 启动探测、字段陷阱（`.pri` / `.profile.*`）、HTTP 部署安全、失败兜底
- [references/review-modes.md](references/review-modes.md) — 3 档评审详解、强制升级条件、Review_Decisions 落档格式
- [references/prompts/multi-agent-review.md](references/prompts/multi-agent-review.md) — 步骤 6.2 subagent 派单 prompt 模板（带占位符替换规范）
- [references/dry-run-mode.md](references/dry-run-mode.md) — `--dry-run` 详解：每步行为差异、diff 预览格式、plan-review 评审变体、底线保证

## 触发示例

> "拉禅道 bug 12345 修一下"
> "/kdev-bugfix --from-zentao 12345"
> "/kdev-bugfix --from-zentao 12345 --dry-run"  ← 先演练一遍看流程合理性
> "/kdev-bugfix login-button-error --review-mode=multi"
> "/kdev-bugfix '订单金额错' --p0 --review-mode=both"
> "/kdev-bugfix issue-123 --no-openspec --no-zentao-update"
> "/kdev-bugfix --from-zentao 67890 --dry-run --auto"  ← 完全自主演练
> "演练一下修这个 bug，不要真改代码"
> "hotfix 一下数据被覆盖的问题，禅道 bug 67890"
