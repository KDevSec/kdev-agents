# kdev-uicase-to-apicase

UI→API 测试用例转换插件：把已有的 UI/Playwright 测试用例 .md（含 `【测试用例信息】` 块、`TC-AR{XX}{YYY}{ZZZ}-{NNN}` 编号格式）沿 7 条转换规则批量改写为同结构的 API 测试用例 .md，作为 `kdev-api-autotest` 生成 pytest 四件套的直接输入。

## 解决什么问题

一份 UI 测试用例文档产出后，面临"分流"问题——哪些用例跑 UI 自动化（Playwright）、哪些跑 API 自动化（pytest 接口测试）。手工逐条改写 API 用例存在三个痛点：

1. **16 条等价规则容易漏**：特别是规则 3/4/8 的"该跳"（纯前端约束 / UI 渲染 / 取消路径）与规则 5/6 的"必测"（操作日志 / negative 断言）的边界——手工改写容易把纯 UI 项硬塞成 API 用例，或漏掉本该写的 negative
2. **编号/名称漂移**：手工改写时容易"润色"用例名称、重新编排序号，导致 UI↔API 的 1:1 交叉追溯断裂
3. **字段命名不一致**：`productLineId` vs `product_line_id` 混用，下游 pytest 实现时对不上 OpenAPI schema

本 skill 把这 7 条规则固化为确定性管道——不判、不改设计，只转换。

## 核心机制

### 7 条转换规则

| # | UI 模式 | API 改写策略 |
|---|---|---|
| 1 | 点击"新增"+ 填表 + 点"确定" | `POST /<资源>`，断言 `HTTP 200 + body.code=200 + body.data.<id> 非空` |
| 2 | "列表新增一行 / 某字段显示 X" | `GET /<资源>/list` 或 `GET /<资源>/{id}`，断言字段匹配 |
| 3 | "字段必填红星 / maxlength=N / 字符计数" | **跳过**（纯前端约束） |
| 4 | "弹窗标题 / 按钮文案 / tag 颜色 / tooltip" | **跳过**（纯 UI 渲染） |
| 5 | "操作日志 4 要素" | `GET /monitor/operlog/list` 验证 4 要素 + 关联变更日志 |
| 6 | "唯一性冲突 / 必填缺失 / 超长 / 越权" | 必测，断言 `body.code != 200 + body.msg 含约定文案 + 数据库无变更` |
| 7 | UI 隐含等价类（边界值 / 高危值） | 整理为 API 参数化数据集 |
| 8 | "二次确认对话框'取消'路径" | **跳过**（API 层不发起请求） |

> 规则 3、4、8 是"该跳"，规则 5、6 是"必测"——最容易混淆的边界。

### 两条硬契约（v0.2.0 新增）

| 契约 | 规则 |
|------|------|
| **用例名称 verbatim** | `用例名称` 必须逐字沿用 UI 用例名称——禁止接口化、参数化、加 `token，<METHOD> <端点>` 前缀。UI↔API 交叉追溯靠「同编号 + 同名称」两把锁 |
| **越权/受限账号对齐真实预置** | 规则 6 的越权类、或前置条件限定了「数据范围受限」的用例，`操作人员` 必须改成对齐真实预置的受限账号——禁止默认超管 admin，否则下游成假绿 |

### 标准化输出

每条 API 用例输出为标准 fielded block（`【测试用例信息】` 块），字段与 UI 用例对齐：
- 用例编号：`TC-API-AR{XX}{YYY}{ZZZ}-{NNN}`（9 位需求段 + 3 位流水号沿用 UI 用例号）
- 用例名称：逐字沿用 UI 用例名称（verbatim）
- 前置条件 / 测试步骤 / 测试数据 / 预期结果：按 7 条规则生成
- 文档末尾 3 段收尾：统计 / 跳过索引 / 自检清单

## 包含的 skill 与资产

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-uicase-to-apicase](skills/kdev-uicase-to-apicase/SKILL.md) | 主 skill：6 步工作流 + 7 条转换规则 + 2 条硬契约 |

## 安装

```bash
claude plugin marketplace add KDevSec/kdev-agents
claude plugin install kdev-uicase-to-apicase@kdev-agents
```

## 触发

用户提到以下关键词时 skill 自动激活：
"UI→API 转换" / "把 UI 用例转成 API" / "从 UI 用例派生 API 用例" / "给 UI 用例配套写一份接口测试用例" / "测试用例 UI→API" / "跳过纯 UI 约束只保留接口可断言的部分" / "让一份用例同时驱动 UI 与 API 自动化" / "把 SOP_测试用例-XXX.md 转成 -api.md"

即使用户没明说"UI→API"，只要项目里同时存在符合标准模板（`【测试用例信息】` 块）的 UI 用例 .md + api_inventory.md / OpenAPI 清单，并要求"派生一份接口可跑的用例文档"或"分流给 API 自动化"，都视为本 skill 适用范围。

## 在流水线中的位置

```
spec.md + 原型 ──[spec-to-testcases-pipeline]──► 测试用例.md (UI)
                                                  │
                                ┌─────────────────┴─────────────────┐
                                │                                   │
              [testcases-to-playwright-pipeline]            [kdev-uicase-to-apicase]   ← 本插件
                                │                                   │
                          Playwright 用例集                  测试用例-api.md
                                                                    │
                                                          [kdev-api-autotest]
                                                                    │
                                                            pytest 四件套
```

## 与其他 kdev-* plugin 的关系

- **[kdev-test-points](../kdev-test-points)** / **[kdev-test-cases](../kdev-test-cases)**：上游——产出测试用例 .md（UI），本 skill 消费
- **[kdev-api-autotest](../kdev-api-autotest)**（如果存在）：下游——消费本 skill 产出的 API 用例 .md 生成 pytest 四件套
- **[kdev-ui-autotest](../kdev-ui-autotest)**：并行——`是否UI自动化=是` 的用例走 UI 通道（Playwright）；`=否` 的用例走本 skill 分流到 API 通道
- **[testcases-to-playwright-pipeline](../../README.md)**：并行——与 UI 自动化流水线对称

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-uicase-to-apicase@kdev-agents
```

## 演进历史

- **v0.2.0**（当前）：verbatim 用例名称硬契约 + 越权/受限用例操作人员对齐真实预置账号 + 下游引用从 `kdev-api-test-scaffold` 统一为 `kdev-api-autotest` + 常见坑新增 2 条
- **v0.1.0**：首次发布——7 条转换规则 + 6 步工作流 + 5 段产出结构

详见 [CHANGELOG.md](CHANGELOG.md)。
