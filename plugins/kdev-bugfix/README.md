# kdev-bugfix

Bug 修复 8 步流程 skill —— 把"bug 获取 → 复现 → 根因 → 回归测试 → 最小修复 → 验证 → 评审 → 提交 → 状态回写"固化为可复跑 skill。

**四个独立扩展轴**：
- **双源 Intake**：禅道拉取 / 直接对话
- **双模式产物**：OpenSpec spec-driven 4 件套 / 纯 docs/bugfix 双文件
- **三档评审**：AI 自评 / 多智能体 / 人工
- **演练模式**：`--dry-run` 跑完 8 步但不动持久状态（教学 / wet-test 评估 / Demo）

## 8 步流程

```
1. Intake & Triage          ← 双源（禅道 / 直接对话） + 模式判定 + 严重度
       │
       ▼
2. Proposal / bug-report    ← openspec new change OR 纯模式 mkdir
       │                       禅道源时自动 seed 字段
       ▼
3. 复现 + 根因投资          ← systematic-debugging Iron Law
       │
       ▼
4. Design + RED             ← design.md + test-driven-development 回归测试
       │
       ▼
5. Tasks + GREEN + 验证闸门 ← 最小修复 + verification-before-completion
       │
       ▼
6. 评审闸门                 ← AI 自评 / multi / human / both
       │                       强制升级条件：P0 / 鉴权 / 跨模块 / 数据迁移 / 文件>3
       ▼
7. Validate + Commit        ← openspec validate + kdev-commit
       │
       ▼
8. 后置动作                 ← bug_source=zentao 时 禅道 active→resolved 自动回写
                              失败兜底输出手动指引
```

## 双源 Intake

### 禅道源

触发：`/kdev-bugfix --from-zentao 12345` 或对话里说 "拉禅道 bug 12345"。

```bash
# 配置（gitignored）
echo 'ZENTAO_API_URL=https://zentao.example.com' >> .kdev/zentao.env
echo 'ZENTAO_API_TOKEN=your-pat' >> .kdev/zentao.env
echo '.kdev/*.env' >> .gitignore

# 跑
/kdev-bugfix --from-zentao 12345
```

skill 用 `curl + jq` 调禅道 REST API v1（`/api.php/v1/bugs/<id>`），抓字段 seed 到 proposal.md 的 Bug Context 段：

| 禅道字段 | proposal.md 位置 |
|---------|------------------|
| `.title` | Symptom |
| `.steps`（HTML 清洗） | Steps_to_Reproduce |
| `.severity` (1-4) | Gate-A 严重度初判 |
| `.openedBy.realname` + `.openedDate` | Environment |

详见 [skills/kdev-bugfix/references/zentao-integration.md](skills/kdev-bugfix/references/zentao-integration.md)。

### 直接对话源

用户口头描述症状 / 贴 stack trace。skill 让 Claude 引导用户填 Bug Context 字段。

## 双模式产物

| 触发 | 模式 | 产物路径 | 多出的闸门 |
|------|------|---------|-----------|
| `<repo>/openspec/` 存在 | **OpenSpec 模式**（默认） | `openspec/changes/<bug-id>/{proposal.md, design.md, [specs/], tasks.md}` | `openspec validate <bug-id>` 必过 |
| 不存在 | **纯模式** | `docs/bugfix/<bug-id>/{bug-report.md, fix.md}` | 仅常规 type-check + lint + 测试 |

`--openspec` / `--no-openspec` flag 可显式覆盖。

## 三档评审

| 模式 | 评审员 | 用时 | 适用 |
|------|--------|------|------|
| `ai`（默认） | 主 Claude + `superpowers:code-reviewer` | ~30s | 日常 P2/P1 |
| `multi` | AI + 派 subagent (opus) | ~2-3min | P0 / 跨模块 / 安全 |
| `human` | 主 Claude 输出摘要 → 暂停等用户 | 取决于用户 | 生产数据 / 合规 |
| `both` | multi → human 串行 | 上述总和 | 极高风险 |

**强制升级**到 multi（即便传 `ai`）：P0 / 鉴权 / 跨模块状态协调 / 数据迁移 / 修改文件数 > 3。

**保守裁决**：任一 reviewer FAIL/REJECT 即 FAIL，**不**投票，**不**少数服从多数。

详见 [skills/kdev-bugfix/references/review-modes.md](skills/kdev-bugfix/references/review-modes.md)。

## 禅道状态回写（步骤 8）

仅 `bug_source=zentao` 且无 `--no-zentao-update`：

```
commit 成功 → PUT /api.php/v1/bugs/<id>/resolve
              { resolution: "fixed", resolvedBuild: "trunk",
                comment: "Commit + 产物路径 + 回归测试 + Root cause" }
              ↓
            成功 → 禅道状态 active → resolved（不到 closed，让 QA 关单）
              ↓
            失败 → STDOUT 输出手动指引，不阻塞流程（代码已 commit）
```

## 字段映射（OpenSpec ↔ 纯模式）

| bugfix 字段 | OpenSpec 模式 | 纯模式 |
|-------------|---------------|--------|
| bug_source / zentao_* 元数据 | proposal.md frontmatter | bug-report.md frontmatter |
| Symptom / Steps / Environment | proposal.md § Bug Context | bug-report.md |
| Root_Cause / Fix_Description / Risks | design.md | fix.md |
| RED / GREEN / 验证任务清单 | tasks.md T1–T12 | TodoWrite |
| Spec delta（如命中） | specs/<capability>/spec.md | fix.md Spec_Impact 段 |
| Review_Decisions（步骤 6 落档） | design.md 末尾 | fix.md 末尾 |

完整速查表见 [skills/kdev-bugfix/references/fields-mapping.md](skills/kdev-bugfix/references/fields-mapping.md)（各 artifact 字段细节按需进 `fields-proposal.md` / `fields-design.md` / `fields-specs.md` / `fields-tasks.md` / `fields-pure-mode.md`）。

## 委派复用的下游 skill

| 用途 | skill |
|------|-------|
| 根因投资（Iron Law） | `superpowers:systematic-debugging` |
| TDD RED→GREEN | `superpowers:test-driven-development` |
| 完成验证闸门 | `superpowers:verification-before-completion` |
| 代码评审（步骤 6） | `superpowers:code-reviewer` |
| Commit（fix 前缀 + AI 身份） | `kdev-commit` |
| 安全复核（按需） | `kdev-secure-coding:python-security-coding`（或对应栈） |
| 大需求重做（如 bug 暴露 spec 缺陷） | `kdev-coding-flow` |

## 包含的 skill 与命令

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-bugfix](skills/kdev-bugfix/SKILL.md) | 8 步主流程 + 双源 / 双模式 / 三档评审 |
| references | [fields-proposal.md](skills/kdev-bugfix/references/fields-proposal.md) | OpenSpec proposal.md 字段（Why / What Changes / Capabilities / Bug Context） |
| references | [fields-design.md](skills/kdev-bugfix/references/fields-design.md) | OpenSpec design.md 字段（Root_Cause / Fix / Risks / Spec_Impact / Review_Decisions） |
| references | [fields-specs.md](skills/kdev-bugfix/references/fields-specs.md) | OpenSpec specs/ delta 模板（仅 Spec_Impact 命中时写） |
| references | [fields-tasks.md](skills/kdev-bugfix/references/fields-tasks.md) | OpenSpec tasks.md T1–T12 模板 |
| references | [fields-pure-mode.md](skills/kdev-bugfix/references/fields-pure-mode.md) | 纯模式 bug-report.md + fix.md 字段 |
| references | [fields-mapping.md](skills/kdev-bugfix/references/fields-mapping.md) | 模式交叉对照 + 纯模式 → OpenSpec 迁移命令 |
| references | [zentao-integration.md](skills/kdev-bugfix/references/zentao-integration.md) | 禅道 API curl 模板 + 配置 + 安全 + 字段陷阱（`.pri` / `.profile.*`） |
| references | [review-modes.md](skills/kdev-bugfix/references/review-modes.md) | 3 档评审详解 + 强制升级条件 + Review_Decisions 落档格式 |
| references | [prompts/multi-agent-review.md](skills/kdev-bugfix/references/prompts/multi-agent-review.md) | multi 模式 subagent 派单 prompt 模板（带占位符替换规范） |
| references | [dry-run-mode.md](skills/kdev-bugfix/references/dry-run-mode.md) | `--dry-run` 详解：每步行为差异、diff 预览、plan-review 评审、底线保证 |
| references | [delivery-summary.md](skills/kdev-bugfix/references/delivery-summary.md) | 统一三段交付摘要格式（【根因分析】/【影响范围】/【修复方案】），跨禅道 comment / 会话报告 / 产物文档 / commit message 共用 |
| 命令 | [`/kdev-bugfix`](commands/kdev-bugfix.md) | 显式触发，含 `--from-zentao` / `--review-mode` / `--no-zentao-update` 等 |

## 触发示例

> "拉禅道 bug 12345 修一下"
> "/kdev-bugfix --from-zentao 12345"
> "/kdev-bugfix --from-zentao 12345 --dry-run"  ← 演练一遍看流程
> "线上 500 了，stack trace 在这: ..."
> "/kdev-bugfix login-button-error --review-mode=multi"
> "/kdev-bugfix '订单金额错' --p0 --review-mode=both"
> "/kdev-bugfix issue-123 --no-openspec --no-zentao-update"
> "演练一下修这个 bug，不要真改代码"
> "hotfix 一下数据被覆盖的问题，禅道 bug 67890"

## 演进历史

- **v0.2.3**（当前）：统一三段交付摘要格式（【根因分析】/【影响范围】/【修复方案】），跨禅道 comment / 会话报告 / 产物文档 / commit message 共用
- **v0.2.2**：`--dry-run` flag — 完整跑 8 步但不动持久状态（演练 / 教学 / wet-test 评估）
- **v0.2.1**：references 拆分（bugfix-fields-reference.md → 6 个 fields-*.md）+ subagent prompt 抽出独立模板
- **v0.2.0**：双源 Intake + 三档评审 + 禅道状态回写（开源版 22.1 IP 部署实测）
- **v0.1.1**：OpenSpec 深集成 + autodetect + `--openspec` / `--no-openspec` / `--archive`
- **v0.1.0**：6 步初版，无 openspec 依赖（已被 v0.1.1 修正）

详见 [CHANGELOG.md](CHANGELOG.md)。

## 与其他 kdev-* plugin 的关系

- **kdev-coding-flow** 处理"从需求到上线"的 13 节点 SOP。bugfix 不走全套 SOP——是更窄更快的修复链路
- **kdev-commit** 负责 commit 动作。bugfix 步骤 7.2 直接委派
- **kdev-secure-coding** 在评审强制升级（鉴权 / 安全）时被调起
- **kdev-change**（设计中，未落地）：未来若实现，Spec_Impact 命中场景改为触发它

## 安全提示

- `ZENTAO_API_TOKEN` **永远不**进 commit / 截图 / 公开 PR
- `.kdev/zentao.env` 必须 gitignored，skill 启动时校验
- subagent 评审 prompt **不**透传 token——subagent 不直接调禅道 API
- 多人协作：每人用自己的 PAT，不共享 service account
