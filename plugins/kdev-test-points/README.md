# kdev-test-points

可审计测试点 / 测试设计文档生成 skill —— 从 spec / PRD / API 契约 / RUSP / COTS 源生成测试点，是测试工坊的**判断密集型上游**（judgment-heavy upstream half）。

**与 `kdev-test-cases` 组合使用，取代旧的 `kdev-test-case`。**

## 解决什么问题

测试设计阶段缺少结构化方法时，常见三类问题：
- **漏测**：只覆盖 happy path，边界/异常/状态迁移/非功能质量特性无人管
- **不可审计**：测试点与需求之间没有可追溯的映射，第三方测评时无法举证覆盖度
- **规格漂移**：测试点标题/编号与上游 spec 不一致，下游渲染链路断裂

本 skill 把测试设计变成**可审计工程**——基于 ISO/IEC/IEEE 29119-4（测试设计技术）和 GB/T 25000.51 ≡ ISO/IEC 25051（三域覆盖 + 8×31 质量子特性 + 符合性 verdict）双标准，让每个测试点都能追溯到"为什么测、用什么技术测、覆盖了哪个质量子特性"。

## 核心机制

### 四种模式，按需裁剪

| 模式 | 适用场景 | 产物 |
|------|---------|------|
| `feature-spec-lite` | 内部 PRD + SP15/xmind/SOP-测试点 模板 | 范围与参数表 + §6.5 TC + RTM + Risk + 自检（SP15 列数不变） |
| `feature-spec` | 内部 PRD/spec，无外部模板 | Header + 在范围 Quality Matrix + COND + CI + TC + Coverage + RTM + Risk |
| `api-contract` | 单个或批量 API 端点契约 | Header + COND + CI + TC + Coverage + RTM（Quality Matrix 仅保留在范围行） |
| `full-conformity` | RUSP / COTS / 25051 第三方测评 | 完整 §6.1–§6.11 双标准文档（单文件，全部内联） |

### 双标准框架

- **29119-4** = 作坊——怎么设计测试点：Test Basis → Test Conditions → Coverage Items → Test Cases → Test Procedures
- **GB/T 25000.51** (≡ ISO/IEC 25051) = 验收清单——必须测什么 + 怎么声明符合性：三域（产品说明/用户文档/软件）× 8 特性 × 31 子特性 × 符合/部分符合/不符合 verdict

### 模板覆盖规则

`--example` 只替换 §6.5 测试用例的**渲染层**——列定义、命名空间、模块号语义从 example 继承，不发明新列/新前缀/新编号规则。审计脚手架（Quality Matrix / COND / CI / Coverage Summary / Conformity）默认不生成；`--audit` 显式开启后写入 companion 文件 `<stem>-audit.md`。

### 关键硬约束

- **AR 编号空间锁定**：前缀从 example grep，不发明（如 `AR-SATP-`）
- **CRUD = 三 AR**：新增 / 编辑 / 删除各自独立，不合并
- **每 AR ≤ 8 行**：超出则拆分子 AR
- **性能整体 OOS**：功能性测试套件不包含任何 `≤Ns` 时间断言，统一在残余风险段标注 + benchmark 转出
- **异常流完备性**：每个业务 AR 独立覆盖 spec 声明的所有校验（空/长度/唯一/不存在/格式/状态/字典越界/特殊符号）
- **One FR = One AR**：跨 FR 相似测试点不合并；重复优于丢失可追溯性

### 不是渲染器

本 skill **只设计，不渲染**：
- ❌ 不产出 Playwright fielded 用例块（→ 那是 `kdev-test-cases` 的工作）
- ❌ 不接收已完成的 测试点 .md 作为输入（→ 检测到 `### AR-` 头 + 表格行时会停止并重定向）

## 包含的 skill 与资产

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-test-points](skills/kdev-test-points/SKILL.md) | 主 skill：4 种模式 + 12 步工作流 + 13 项自检 |
| references | [output-templates.md](skills/kdev-test-points/references/output-templates.md) | §6.1–§6.11 完整输出模板（Header / Quality Matrix / COND / CI / TC / TC-DOC / Coverage / Conformity / RTM / Defect / Risk） |
| references | [quality-characteristics.md](skills/kdev-test-points/references/quality-characteristics.md) | 8×31 质量子特性 × 最低测试技术地板 |
| references | [template-override.md](skills/kdev-test-points/references/template-override.md) | `--example` 模板覆盖规则：不变量 + 脚手架放置 + 按模板家族的合并策略 |
| references | [example-walkthrough.md](skills/kdev-test-points/references/example-walkthrough.md) | 1 FR 端到端走通 29119-4 pipeline 的完整示例 |
| evals | [evals.json](skills/kdev-test-points/evals/evals.json) | 4 个回归 eval（SP15 模板 / 默认格式 / API 契约 / 拒收已生成测试点） |

## 安装

```bash
claude plugin marketplace add KDevSec/kdev-agents
claude plugin install kdev-test-points@kdev-agents
```

## 使用

```
/kdev-test-points [--input <path>]
                     [--example <path>]
                     [--output <path>]
                     [--mode feature-spec|api-contract|full-conformity]
                     [--lite]
                     [--audit]
                     [free-form prompt]
```

### 前置条件

`--input` 必须是 raw spec / PRD / API 契约——不是已生成的 测试点 .md。如果输入已含 `### AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` 头 + 编号表格行，skill 会在 workflow step 2 检测到并停止，提示用户改用 `kdev-test-cases`。

`--example` 可选——提供 SP15/xmind/SOP-测试点 模板时自动切换为 `feature-spec-lite` 模式，输出列定义/命名空间/自检风格从模板继承。

### 触发

用户说以下任意关键词时 skill 自动激活：
"generate test points" / "design test points for this spec" / "create test design document" / "boundary tests" / "decision table tests" / "pairwise combinations" / "regression coverage" / "什么测试点" / "梳理测试点" / "测试点编写" / "测试设计文档" / "GB 25000 测试" / "25051 测试" / "软件产品测评" / "就绪可用软件产品测试" / "质量特性测试" / "符合性测试" / "用户文档测试" / "产品说明测试"

即使只粘贴 spec / API 契约 / 状态图说"测一下"，也视为本 skill 适用范围。

## 与其他 kdev-* plugin 的关系

- **[kdev-test-cases](../kdev-test-cases)**：下游——把本 skill 的 测试点 .md 1:1 渲染为 Playwright fielded 用例块
- **[kdev-test-cases-v2](../kdev-test-cases-v2)**（如果存在）：v2 实验分支——同契约的扩展版
- **[kdev-ui-autotest](../kdev-ui-autotest)**：下游的下游——消费 fielded 用例块（`是否UI自动化=是`）生成 Playwright 脚本
- **[kdev-env-recon](../kdev-env-recon)**：并行——提供 UI 实测菜单/字段/弹窗文案，作为测试点设计的环境参照
- **[kdev-api-recon](../..)**（如果存在）：并行——提供 OpenAPI 接口清单，作为 `api-contract` 模式的输入源

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-test-points@kdev-agents
```

## 演进历史

- **v0.1.0**（当前）：首次发布——从 `kdev-test-case` 拆分出的测试设计引擎。4 种模式 + 双标准框架 + SP15 模板覆盖 + 审计 companion 机制。4 个 core eval 覆盖 feature-spec-lite / feature-spec / api-contract / rejects-testpoints-input。

详见 [CHANGELOG.md](CHANGELOG.md)。
