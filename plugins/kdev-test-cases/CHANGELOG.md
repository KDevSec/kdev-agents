# kdev-test-cases CHANGELOG

## [0.2.0] — 2026-06-16

**同步 v2 canonical 渲染器：承载 h4 测试范围分组 + 新增 SOP_测试用例MODv2 资产 + eval 更新。**

### ✨ 新增

- **`assets/SOP_测试用例MODv2.md`** — v2 测试用例渲染 SOP，承载 4 项 v2 传播（h4 测试范围分组 / AR 前缀解锁 / AR 编号 spec-verbatim / 角色解锁）。
- `references/output-skeleton.md` 扩写以支持 `#### 测试范围 N` h4 分组与 `TC-AR{数字段}-G{N}-{NNN}` 编号（`G{N}` 编码测试范围号）。

### 🔄 变更

- **SKILL.md 升级为 production-default v2**（前身 kdev-test-cases-old / v1 弃用，仅留迁移兼容）：用例编号从 `TC-AR<8 位>-<3 位>` 升级为 `TC-AR{数字段}-G{N}-{NNN}`（承载上游 `#### 测试范围 N` h4 分组）；AR 前缀解锁（不再硬编码 `AR-SATP-`，接受 spec 任意前缀）；AR 编号 spec-verbatim 不造 sub-AR；角色从上游 测试点 .md 取，不再默认「超级管理员」。byte-equality / arithmetic-equality 契约不变。
- `evals/evals.json` 同步对齐 v2。

### 来源

- 内容同步自 `Functional-Test-Skill/kdev-test-cases`（canonical 源），逐字一致；`references/playwright-handoff.md` 无变化。

## [0.1.1] — 2026-06-16

**marketplace 注册名纠偏：`-v1` 旧名纠正为规范名。**

### 🐛 修复

- **marketplace 注册名/源纠偏**：`kdev-agents/.claude-plugin/marketplace.json` 里本插件条目原登记为 `kdev-test-cases-v1` + `source: ./plugins/kdev-test-cases-v1`（该目录不存在，真目录为 `./plugins/kdev-test-cases`），导致安装命令无法解析、真插件未被注册。现 name / source 纠正为规范名 `kdev-test-cases`，description 去残留 `-v1` 文案；与配套插件 kdev-test-points 同批修复。

## [0.1.0] — 2026-05-19

**首次发布**：从 `kdev-test-case` 拆分出的纯渲染器——1:1 把上游 测试点 .md 渲染为 Playwright 友好的 fielded 测试用例代码块。

### 背景

旧的 `kdev-test-case` 同时做两件事：测试点设计（从 spec/PRD 判断测什么、怎么定级）+ 测试用例渲染（把设计结果写成 fielded blocks）。两者耦合导致：
- 渲染阶段想"润色"标题 → 静默漂移
- 设计判断和渲染写在同一轮 → 边界模糊
- 下游 Playwright 生成器依赖字节级一致（用例名称/编号），但上游没有 byte-equality 契约

拆分方案：`kdev-test-points` 做设计（judgment-heavy upstream），`kdev-test-cases` 做渲染（deterministic downstream renderer）。两个 skill 各司其职，中间靠文件契约（测试点 .md 的 `### AR-...` 头 + 编号表格行）对接。

### 核心内容

- **SKILL.md** 主 skill：6 步工作流（pre-flight → index → read example → render → statistics → self-check）+ 7 条硬契约
- **Contract §3.1 Cardinality**：输出块数 == 输入行数，`grep -c "^- 用例编号："` 校验
- **Contract §3.2 Title preservation**：用例名称 == 测试点标题 byte-equal（不润色、不省略前缀、不修 typo）
- **Contract §3.3 ID derivation**：`TC-AR<8 位 AR 数字串联>-<3 位行号>`，确定性纯函数
- **Contract §3.4 Pass-through**：用例类型/优先级/准入/UI自动化/API自动化 从源行逐字复制，不重判
- **Contract §3.5 预期结果**：同序保留，异常流缺失时仅追加 "平台数据保持不变"
- **Contract §3.6 Generative**：仅 测试步骤 / 前置条件 / 测试数据 生成——且只从 测试点 标题+预期推断
- **Contract §3.7 No re-design**：不产出 §6.1–§6.11 等上游已覆盖的 ceremonial sections
- **§6 Self-check**：10 项检查（cardinality + ID regex + spot-check ×5 + title + pass-through + 预期 + generative + no-redesign + output hygiene）

### 资产

- `references/output-skeleton.md` — 完整输出布局 + block 格式 + block 分隔符 + 统计表 + 自检 + 上游问题报告格式
- `references/playwright-handoff.md` — Playwright 接驳词汇表（`【菜单】` / `"按钮"` / 字段填写 / 默认账号 / 表单提交）+ 反例 + 完整 worked examples（基本流 + 异常流）
- `evals/evals.json` — 4 个回归 eval：
  1. happy-path-1-to-1-render：基本 1:1 映射
  2. rejects-raw-spec-input：拒收 raw spec（pre-flight 拦截）
  3. title-with-prefix-preserved-verbatim：验证前缀透传（"超级管理员登录，" 不省略）
  4. id-derivation-determinism：3 AR × 多行，验证 ID 确定性

### 设计决策

- **为什么是独立 skill 而不是 kdev-test-points 的一个 mode**：渲染的 byte-equality 契约和设计的 judgment 自由是天然冲突的——放一起迟早互相污染。拆分后两个 skill 各自迭代互不牵制
- **为什么 ID 是 `TC-AR<8 digits>-<3 digits>` 而不是语义 ID**：确定性——重新跑 produce byte-identical IDs，CI 可 `diff` 验证；语义 ID（如 `TC-LOGIN-001`）需人工维护且易冲突
- **为什么标题必须 byte-equal 包括前缀**：下游 Playwright 生成器用 `用例名称` 哈希出 `test_xxx` 函数名。省略前缀会破坏跨用例命名一致性，且无法机械验证
- **为什么 generative fields 只从标题+预期推断**：开其他信息源（如外部知识库、--example 示例行）会在不同 session 间产生漂移。只用输入文档保证确定性

### 注册

- `.claude-plugin/plugin.json`：`name: kdev-test-cases, version: 0.1.0`
- 注册到 KDevSec/kdev-agents marketplace
- 仓库根 README 插件表新增条目
- 仓库根 README 安装命令新增 `claude plugin install kdev-test-cases@kdev-agents`

### 相关文档

- 拆分背景：旧 `kdev-test-case` → `kdev-test-points` + `kdev-test-cases` 的决策
- 上游 skill：[kdev-test-points](../kdev-test-points/SKILL.md)
- 下游消费方：[kdev-ui-autotest](../kdev-ui-autotest/SKILL.md)（约束 5：按 `是否UI自动化=是` 分流）
