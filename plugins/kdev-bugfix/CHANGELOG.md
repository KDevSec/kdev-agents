# kdev-bugfix Changelog

## v0.2.2 (2026-05-13)

**新增 `--dry-run` flag**：完整跑 8 步但不动任何持久状态。

### 用途

- 演练流程：第一次跑 skill 没把握 8 步走法
- wet-test 评估：先 dry-run 看流程是否合理，满意后去掉 `--dry-run` 真跑
- 教学 / Demo：全程不污染 demo 环境
- 评估 plan 质量：让评审段（步骤 6）决定"这个 bug 值不值得修"

### 底线保证

`--dry-run` 跑完保证**零持久状态变更**：

- 不写产物文件（`openspec/changes/<bug-id>/` 或 `docs/bugfix/<bug-id>/`）
- 不动 src/ tests/ 任何代码文件
- 不创建 / 切换 / 改动任何 git 分支
- 不 commit / 不 push
- 不调禅道写接口（PUT/POST）；GET 只读除外

每个"本应执行"的动作前缀 `🔵 DRY-RUN | step N: ...`，便于 grep 视觉区分。

### 步骤 4 RED 的特殊处理

dry-run **跳过实测**回归测试（即"watch it fail"）——只 print 测试代码 + 预测失败原因，不真跑。这是 dry-run 最大局限：**真跑前不要把 dry-run 结论当成"方案可行"的最终证据**。

### 步骤 6 评审的 plan-review 变体

dry-run 无真实 diff，评审改为 plan-review：评 design.md 修复方案 + tasks.md 完整性 + Root_Cause 是否对准 Symptom。`prompts/multi-agent-review.md` subagent prompt 末尾自动追加 `dry-run plan-review` 提示。

### 输出格式

详见 [references/dry-run-mode.md](skills/kdev-bugfix/references/dry-run-mode.md) — 包含每步行为对照表、diff 预览格式、curl 命令预览（token redacted）、终态报告差异。

### 叠加规则

`--dry-run` 可叠加任何其他 flag：

| 叠加 flag | 行为 |
|----------|------|
| `--from-zentao <id>` | 真拉禅道 bug（GET 只读不污染）；不回写状态 |
| `--review-mode=<x>` | 评审改为 plan-review（评 plan 而非 diff） |
| `--p0` | 严重度判 P0，触发评审强制升级到 multi |
| `--auto` | 仍生效；"做"的动作被 dry-run 拦截 |

### 不允许的混用

- **不要在真实 bug 修复时挂 `--dry-run`**——dry-run 不是缩水版 bugfix，是演练
- **不要把 dry-run 结论当成"方案可行"的最终证据**——必须去掉 `--dry-run` 重做一次实测

## v0.2.1 (2026-05-13)

**文档结构优化**：references 拆分粒度细化，让 SKILL.md 引用更精确。

### 拆分 `bugfix-fields-reference.md` → 6 个 artifact-specific 文件

原 387 行单文件被拆为：

- `references/fields-proposal.md` — OpenSpec proposal.md 字段（Why / What Changes / Capabilities + Bug Context）
- `references/fields-design.md` — OpenSpec design.md 字段（Root_Cause / Fix_Description / Risks / Spec_Impact / Review_Decisions）
- `references/fields-specs.md` — OpenSpec specs/<capability>/spec.md delta（仅 Spec_Impact 命中时）
- `references/fields-tasks.md` — OpenSpec tasks.md T1–T12 模板
- `references/fields-pure-mode.md` — 纯模式 bug-report.md + fix.md 双文件
- `references/fields-mapping.md` — 模式交叉对照表 + 纯模式 → OpenSpec 迁移命令

旧的 `bugfix-fields-reference.md` 已删除。SKILL.md 各步骤精确引用对应小文件（不再"§1 / §2 / §3 / §4"在大文件里跳）。

### 抽取 subagent prompt 模板

`review-modes.md §2` 内联的 70 行 multi-agent review prompt → 独立文件：

- `references/prompts/multi-agent-review.md` — prompt 模板 + 占位符替换规则 + 派单代码示例
- `references/prompts/README.md` — prompts/ 目录使用规范，未来新增 prompt 模板的命名约定

`review-modes.md §2` 现在只剩 3 步派单流程 + 链接到 prompts/multi-agent-review.md。修改 prompt 不再需要动 review-modes.md（关注点分离）。

### SKILL.md 必读 references 段重写

从 3 个 reference 行扩到分组列表（字段速查 6 个 / 集成 1 个 / 评审 1 个 / prompt 模板 1 个），让 SKILL.md 读者一眼看清每个文件的覆盖面。

## v0.2.0 (2026-05-13)

**6 步 → 8 步**：新增 Intake 双源（禅道 / 直接对话）+ 评审闸门（AI / multi / human / both 三档）+ 后置动作（禅道状态回写）。

**禅道版本适配**：主要面向**开源版 22.1+ IP 部署**实测（也兼容旗舰版 / 企业版 22.x+ / 域名 + HTTPS 部署）。zentao-integration.md 新增 §0 启动探测脚本（验证 URL 路径前缀 + 认证），HTTP 部署的传输安全警告（IP + HTTP 部署凭证明文走内网）。老版本（< 18.x）走 web 表单接口的 fallback 模板也已附。

**认证方式**：**session-auth 作为主路径**（账号密码换 24h session token，token 缓存到 `.kdev/.zentao-session`，过期自动续期），**PAT 降为可选**（仅当用户在禅道 UI 找到 PAT 入口时切换）。原因：开源版 22.1 实测 UI 入口经常找不到 PAT 选项，session-auth 是 universal fallback。`ZENTAO_AUTH_MODE=session|pat` flag 切换。session-auth 安全提示：建议用只读 service account 而非个人主账号。

**开源版 22.1 实测落到的踩坑（已写入 zentao-integration.md）**：

1. **URL 不带 `/zentao` 后缀**：即便禅道部署在 `/zentao` 路径，外部访问 nginx rewrite 后是根路径。带 `/zentao` 时端点 302 重定向到登录页，看起来像"端点不存在"
2. **`ZENTAO_INSECURE_TLS=true` 配置项**：HTTPS 自签证书（公网 IP + 自签是开源版常见组合）curl 必须 `-k`
3. **`/user` 字段嵌套在 `.profile.*` 下**：不是顶层。`.profile.account` / `.profile.realname` 才对
4. **bug 优先级字段是 `.pri`** 不是 `.priority`（22.x 内外字段命名不一致老问题）
5. **模块名读 `.moduleTitle`** 比 `.module`（ID）更可读
6. **session token response 不返回 expire 字段**（与某些 Pro 版文档不同），skill 用 cache 文件 mtime + 23h 作为 stale 判据，401 时自动重换

### Intake 双源

- **禅道拉取**：`--from-zentao <id>` 或对话里说"拉禅道 bug 12345"。通过 ZenTao REST API v1（`/api.php/v1/bugs/<id>`）抓字段（title / steps / severity / openedBy / openedDate），seed 进 proposal.md 的 Bug Context 段
- **直接对话**：保持 v0.1.x 行为，用户口头描述 / 贴 stack trace
- 配置走 `<repo>/.kdev/zentao.env`（gitignored）或环境变量 `ZENTAO_API_URL` + `ZENTAO_API_TOKEN`
- **0 依赖**：仅 curl + jq，不写 Python wrapper
- proposal.md / bug-report.md 顶部新增 frontmatter 字段：`bug_source` / `zentao_bug_id` / `zentao_url` / `zentao_severity` 等

### 评审闸门（步骤 6 新增）

四种模式 + 强制升级：

- `--review-mode=ai`（默认）：主 Claude 委派 `superpowers:code-reviewer` 自评
- `--review-mode=multi`：AI 自评 + 派 subagent (opus) 独立评审，**保守裁决**（任一 FAIL 即 FAIL，不投票）
- `--review-mode=human`：暂停输出评审请求摘要等用户回复（`APPROVE` / `APPROVE WITH CHANGES <要求>` / `REJECT <理由>`）
- `--review-mode=both`：multi → human 串行
- **强制升级**到 multi：P0 / 鉴权 / 跨模块 / 数据迁移 / 修改文件数 > 3
- 评审决策落档：design.md（或纯模式 fix.md）末尾新增 `## Review_Decisions` 段
- commit message 模板加 `Reviewers: AI (PASS), multi-agent (PASS), human (N/A)` 行

### 后置动作（步骤 8 新增）

- bug_source=zentao 时，commit 完成后自动 PUT `/api.php/v1/bugs/<id>/resolve`，状态 `active → resolved`（不到 closed，让 QA 走关单）
- resolution=fixed，comment 自动填充 Commit SHA + 产物路径 + 回归测试 + Root cause
- **失败兜底**：API 错（401 / 403 / 5xx）→ STDOUT 输出手动指引，**不阻塞**流程（代码已 commit 不撤回）
- `--no-zentao-update` 显式跳过

### 新增 references

- [references/zentao-integration.md](skills/kdev-bugfix/references/zentao-integration.md) — 禅道 API curl 模板 + 配置说明 + 安全提示
- [references/review-modes.md](skills/kdev-bugfix/references/review-modes.md) — 3 档评审详解 + subagent prompt 模板 + 强制升级条件

### 更新 references

- [references/bugfix-fields-reference.md](skills/kdev-bugfix/references/bugfix-fields-reference.md) — 加 `bug_source` / `zentao_*` frontmatter 字段 + `Review_Decisions` 段 + 字段交叉对照表扩展

### 新 slash 参数

- `--from-zentao <id>`：禅道源
- `--review-mode=ai|multi|human|both`：评审模式
- `--no-zentao-update`：跳过禅道回写

### P0 快路径调整

P0 hotfix 仍走 8 步但允许压缩：评审**强制升级到 multi**（不允许单 AI 评审 P0）。

## v0.1.1 (2026-05-13)

**深集成 OpenSpec**。修正 v0.1.0 把 openspec CLI 一刀切砍掉的错误判断。

- 新增 autodetect：`<repo>/openspec/` 存在 → OpenSpec 模式；不存在 → 纯模式
- 新增 flag：`--openspec` / `--no-openspec` / `--archive`
- OpenSpec 模式产物布局：`openspec/changes/<bug-id>/{proposal.md, design.md, [specs/], tasks.md}`
- 字段映射：bug-report → proposal Bug Context；Root_Cause + Fix → design；T1–T12 任务 → tasks
- 新增闸门：步骤 6.1 必跑 `openspec validate <bug-id>`

## v0.1.0 (2026-05-13) — 已被 v0.1.1 取代

- 初版：6 步主流程 + 3 个判断 Gate + P0 hotfix 快路径
- 完全砍掉 openspec CLI 依赖（v0.1.1 修正此判断）
