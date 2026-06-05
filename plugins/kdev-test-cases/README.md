# kdev-test-cases

测试用例渲染 skill —— 把上游 `kdev-test-points` 产出的 测试点 .md（或任意 SP15/SOP-测试点 格式 markdown）**1:1 逐行渲染**为 Playwright 友好的 fielded 测试用例代码块。

**与 `kdev-test-points` 组合使用，取代旧的 `kdev-test-case`。**

## 解决什么问题

测试点设计（`kdev-test-points`）和测试用例编写之间有一条关键的"翻译断层"：
- 测试点文档里是编号表格行（`| # | 测试点标题 | 预期结果 | ...`），人类可读但机器无法直接消费
- Playwright 脚本生成器需要结构化 fielded blocks（`用例编号 / 用例名称 / 测试步骤 / 预期结果 ...`）
- 手工翻写容易出错：标题被"润色"、ID 手工编、字段漏掉

本 skill 把这条翻译变成**确定性管道**——不判、不改、不设计，只渲染。

## 核心机制

### 硬契约：byte-equality + arithmetic-equality

| 契约 | 规则 |
|------|------|
| **Cardinality** | `count(output 用例编号) == count(input 测试点 rows)` — 逐行 1:1，不聚合、不跳过、不发明 |
| **用例名称** | byte-for-byte 等于 测试点标题 — 不改写、不省略前缀、不修 typo |
| **用例编号** | 确定性派生 `TC-AR<8 位 AR digits>-<3 位行号>` — 纯函数，重新运行产出 byte-identical ID |
| **透传字段** | 用例类型 / 优先级 / 是否准入 / UI 自动化 / API 自动化 — 逐字复制，不重判 |
| **预期结果** | 同序保留；异常流缺失时仅追加 "平台数据保持不变" 一条 |
| **生成字段** | 仅 测试步骤 / 前置条件 / 测试数据 由模板推断 — 且只从标题+预期派生 |

### 为什么不放宽

下游 Playwright 生成器（`kdev-ui-autotest`、`testcases-to-playwright-pipeline`）用 `用例名称` 哈希出测试函数名，用 `用例编号` 匹配测试结果行。这里静默改写一个字 → 整个 **测试→执行→缺陷分诊链** 断裂。远比"润色几个句子"的收益大得多。

### Playwright 接驳约定

| 元素 | 写法 | 下游映射 |
|------|------|---------|
| 菜单项 | `【项目管理】→【产品线管理】` | `page.click(menu_item)` |
| 按钮 | `点击"新增"按钮` | `page.get_by_role("button")` |
| 字段填写 | `填写"名称"字段为 "测试产品线A"` | `page.fill(...)` |
| 默认账号 | `admin / admin123` | 共享 auth_state fixture |

### 不是设计师

本 skill **只渲染，不设计**：
- ❌ 不产出 §6.1 Header / Quality Matrix / COND / CI / Coverage Summary / RTM / Risk（上游 测试点 .md 已覆盖）
- ❌ 不新增/合并/重排 AR
- ❌ 不改判优先级/准入/自动化标记
- ❌ 不接收 raw spec / PRD / API contract 作为输入（→ 那是 `kdev-test-points` 的工作）

## 包含的 skill 与资产

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-test-cases](skills/kdev-test-cases/SKILL.md) | 主 skill：6 步工作流 + 7 条契约 + 自检 |
| references | [output-skeleton.md](skills/kdev-test-cases/references/output-skeleton.md) | 完整输出布局 + block 格式 + 统计表 + 上游问题报告 |
| references | [playwright-handoff.md](skills/kdev-test-cases/references/playwright-handoff.md) | Playwright 接驳词汇表 + 反例 + 完整示例 |
| evals | [evals.json](skills/kdev-test-cases/evals/evals.json) | 4 个回归 eval（happy-path / reject-spec / prefix-preserve / id-determinism） |

## 安装

```bash
claude plugin marketplace add KDevSec/kdev-agents
claude plugin install kdev-test-cases@kdev-agents
```

## 使用

```
/kdev-test-cases --input <path-to-测试点.md> --example <path-to-模板.md> [--output <path>]
```

### 前置条件

`--input` 必须是已完成的 测试点 .md（含 `### AR-[A-Z]+-\d{2}\.\d{3}\.\d{3}` 头 + 编号表格行）。如果是 raw spec / PRD / API contract，先用 `kdev-test-points` 设计测试点。

`--example` 必须是 fielded-block 模板（如 `SOP_测试用例MOD.md`），其 §二/§样例 的 code block 布局决定输出块格式。

### 触发

用户说以下任意关键词时 skill 自动激活：
"把测试点写成测试用例" / "render test points as test cases" / "测试用例编写" / "test points to fielded cases" / "把 测试点.md 渲染成 Playwright 用例" / "SOP_测试用例MOD-style fielded blocks" / "生成 fielded 用例" / "给我 Playwright 用例骨架" / "把 ARs 一行一行变成代码块" / "把 测试点 .md 落成测试用例 .md"

## 与其他 kdev-* plugin 的关系

- **[kdev-test-points](../kdev-test-points)**：上游——产出 测试点 .md，本 skill 消费
- **[kdev-ui-autotest](../kdev-ui-autotest)**：下游——消费 fielded 用例块生成 Playwright 脚本
- **[kdev-ui-autotest](../kdev-ui-autotest) 的约束 5**：`是否UI自动化=是` 的用例走 UI 通道；`=否` 的用例走 API 通道（`kdev-uicase-to-apicase`）
- **[kdev-test-cases-v2](../kdev-test-cases-v2)**（如果存在）：v2 实验分支——同一契约的扩展版

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-test-cases@kdev-agents
```

## 演进历史

- **v0.1.0**（当前）：首次发布——从 `kdev-test-case` 拆分出的纯渲染器。4 个 core eval 首跑 4/4 PASS。

详见 [CHANGELOG.md](CHANGELOG.md)。
