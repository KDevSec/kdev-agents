# kdev-test-points CHANGELOG

## [0.1.0] — 2026-05-19

**首次发布**：从 `kdev-test-case` 拆分出的测试设计引擎——judgment-heavy upstream half，基于 ISO/IEC/IEEE 29119-4 × GB/T 25000.51 双标准，从 spec / PRD / API 契约 / RUSP / COTS 源生成可审计测试点。

### 背景

旧的 `kdev-test-case` 同时做两件事：测试点设计（从 spec/PRD 判断测什么、怎么定级）+ 测试用例渲染（把设计结果写成 fielded blocks）。两者耦合导致：
- 设计阶段的判断（技术选型/优先级/覆盖度）和渲染阶段的机械转换（byte-equality 契约）混在同一轮
- 没有双标准框架——测试点设计缺少 29119-4 技术路由和 25000.51 质量覆盖举证
- SP15/xmind 模板用户被迫接受固定列定义，无法沿用内部 house style

拆分方案：`kdev-test-points` 做设计（judgment-heavy upstream），`kdev-test-cases` 做渲染（deterministic downstream renderer）。两个 skill 各司其职，中间靠文件契约（测试点 .md 的 `### AR-...` 头 + 编号表格行）对接。

### 核心内容

- **SKILL.md** 主 skill：4 种模式（feature-spec-lite / feature-spec / api-contract / full-conformity）+ 12 步工作流 + 13 项自检清单
- **§1 Mode gating**：模式判定链（`--mode` flag > 关键词 > SP15 检测 > feature-spec default）+ `--lite` 压缩 + `--audit` 显式开启审计 companion
- **§2 Arguments**：`--input` / `--example` / `--output` / `--mode` / `--lite` / `--audit` + free-form prompt
- **§3 Template override**：`--example` 只替换 §6.5 渲染层；审计脚手架默认不生成（`--audit` opt-in）；列数 contract（≤9 列不注入 CI/子特性/技术）；AR 编号空间/模块号语义/角色/子 AR 拆分/CRUD 三 AR 等硬约束
- **§4 Pipeline**：29119-4 §6 全流程（Read → Scope → Quality Matrix → COND → CI → TC → TC-DOC → Coverage → Conformity → RTM → Defect → Risk），每步有模式×audit 产物映射表
- **§5 Technique selection**：双轴路由——输入形状（状态机→ST / 多条件→DT / 数值边界→EP+BVA / ≥4×3→Pairwise / 结构化字符串→Syntax / E2E→Scenario / 安全关键→MC/DC）+ 质量子特性（8×31 技术地板）
- **§6 Density heuristics**：N FR ≈ 100–120 TC（≈5×AR 数）；CRUD 三 AR floor；BVA 四值 floor；XSS `<script>` floor；编辑清空可选字段 floor；异常完备性 floor；非性能数量化承诺 floor；性能整体 OOS；每 AR ≤8 行 ceiling
- **§7 Workflow**：12 步——Read → Sanity check（拒收已生成测试点 .md）→ Mode+audit → Scope → Audit artifact routing → COND → CI → TC → TC-DOC → Coverage+Conformity+RTM → Risk → Self-check
- **§8 Self-check**：13 项检查——mode+audit policy / audit-OFF default / companion cross-ref / example column count / input sanity / naming+role+structure locks / coverage discipline（One FR = One AR / CRUD split / edit-clears-optional / `<script>` / no module 99 / no abstract non-functional ARs / performance OOS / exception completeness）/ technique floors / audit closure / downstream handoff
- **§9 Output language**：默认中文；`--audit` 时 companion 文件 `<stem>-audit.md` 命名契约

### 资产

- `references/output-templates.md` — §6.1–§6.11 完整输出模板：Header / Quality Coverage Matrix（8×31）/ Test Conditions / Coverage Items / Test Cases（含覆盖项/质量子特性/域/技术/优先级判据/前置/后置字段）/ TC-DOC / Coverage Summary / Conformity Evaluation / RTM / Defect Categorisation / Risk & Out-of-Scope
- `references/quality-characteristics.md` — 8 大质量特性 × 31 子特性的最低测试技术地板（功能性 3 子特性 / 性能效率 3 / 兼容性 2 / 易用性 6 / 可靠性 4 / 信息安全性 5 / 维护性 5 / 可移植性 3），每项标注适用的 29119-4 技术
- `references/template-override.md` — `--example` 模板覆盖规则：4 个不变量（CI/子特性/域/技术）的 3 种放置策略（列追加/标题后缀/脚注锚点）+ 脚手架 3 种放置（前缀/附录/companion file）+ 按模板家族（SP15 xmind / Excel matrix / SOP 测试用例 MOD）的合并策略
- `references/example-walkthrough.md` — 1 FR（状态机 + 条件必填 + 二次确认）端到端走通 29119-4 pipeline 的完整示例：Test Basis → Quality Matrix → COND → CI → TC（6 行含 EP/BVA/ST 技术标注）→ Coverage → RTM
- `evals/evals.json` — 4 个回归 eval：
  1. spec-with-sp15-template：SP15 模板 → feature-spec-lite，验证列数不变 + companion + AR 前缀/模块号/角色锁定
  2. spec-default-format：无 example → feature-spec，验证完整 §6.1–§6.11 格式
  3. small-api-contract：单一 POST endpoint → api-contract，验证 EP/BVA/Syntax/DT 技术选用 + 不展开 8×31 占位行
  4. rejects-testpoints-input：已生成测试点 .md → step 2 拦截 + 重定向到 kdev-test-cases

### 设计决策

- **为什么是独立 skill 而不是 kdev-test-case 的一个 mode**：测试设计（判断密集、需要双标准框架、产物可审计）和测试用例渲染（确定性 1:1 映射、byte-equality 契约）是两种根本不同的工作——放一起会导致设计判断污染渲染契约（"标题润色一下"→静默漂移），或渲染约束限制设计自由（"列不能加"→审计信息丢失）。拆分后各自迭代互不牵制
- **为什么有 4 种模式而不是 1 种**：内部 PRD 的测试设计 ≠ API 契约的测试设计 ≠ 第三方测评的测试设计。用同一套 ceremony 打所有场景会让内部 pipeline 用户被 8×31 矩阵/TC-DOC/CONFORMITY 表淹没，或让测评场景缺少合规举证。模式 gating 在入口处裁剪 ceremony level
- **为什么 audit companion 默认 OFF**：SP15 → xmind → kdev-test-cases → Playwright 是内部 pipeline 的 95% 路径。审计材料（8×31 矩阵/COND/CI/Coverage Summary/Conformity Evaluation/bidirectional RTM）对这条路径是死重——实测用户 100% 删除 companion。`--audit` 显式 opt-in 让测评场景（5% 路径）能拿到完整举证，而不拖累日常 pipeline
- **为什么模板覆盖只替换 §6.5 而不是全量替换**：example（SP15/xmind/SOP-测试点 MOD）定义的是"测试点表格长什么样"——列名、列序、列数。Header/Quality Matrix/COND/CI/Coverage/Conformity/RTM/Risk 这些审计脚手架是 29119-4 + 25000.51 的合规产出，example 不管它们。让 example 控制全量输出 = 丢失双标准可审计性
- **为什么性能整体 OOS**：功能性测试套件混入 `≤Ns` 时间断言 → flaky tests + 两种测试人口混杂 + CI 被迫承受性能噪声。所有时间特性断言统一在残余风险段标注 OOS + benchmark 转出。这个决定来自 v2.1.1 的实证反馈
- **为什么 SP15 列 ≤9 时不注入 CI/子特性/技术列**：SP15 → xmind/xlsx 脚本依赖固定列数。追加列会破坏 md→xmind 转换。FR 链路通过 AR 标题注释 + 短 RTM 承载，不侵入表格 schema

### 注册

- `.claude-plugin/plugin.json`：`name: kdev-test-points, version: 0.1.0`
- 注册到 KDevSec/kdev-agents marketplace
- 仓库根 README 插件表新增条目
- 仓库根 README 安装命令新增 `claude plugin install kdev-test-points@kdev-agents`

### 相关文档

- 拆分背景：旧 `kdev-test-case` → `kdev-test-points` + `kdev-test-cases` 的决策
- 下游 skill：[kdev-test-cases](../kdev-test-cases/SKILL.md)（fielded 渲染器）
- 下游的下游：[kdev-ui-autotest](../kdev-ui-autotest/SKILL.md)（约束 5：按 `是否UI自动化=是` 分流）
