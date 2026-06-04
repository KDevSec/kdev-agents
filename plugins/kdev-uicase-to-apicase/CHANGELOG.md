# kdev-uicase-to-apicase CHANGELOG

## [0.2.0] — 2026-06-04

**verbatim 用例名称硬契约 + 越权/受限用例操作人员对齐真实预置账号 + 下游引用统一。**

### ✨ 新增功能

#### 用例名称 verbatim 硬契约

- **`用例名称` 从可执行字段重新定义为身份/可追溯字段**：必须逐字沿用 UI 用例名称，禁止接口化、参数化、加 `token，<METHOD> <端点>` 前缀或任何改写
- UI↔API 的 1:1 交叉追溯靠「同编号 + 同名称」两把锁——名称一改写人工 diff 就对不齐
- 与上游 `kdev-test-cases` / `kdev-test-cases-v2` 的「用例名称 == 测试点标题 verbatim」契约保持一致
- **接口腔只落在可执行字段**：`测试步骤`（`<METHOD> <URL>`）/ `测试数据` / `预期结果` / `前置条件`
- **自检**：`用例名称` 行去掉编号后应与 UI 源文件同编号用例逐字相等

#### 越权/受限用例操作人员对齐真实预置账号

- **规则 6 的越权类、或前置条件限定了「数据范围受限 / 缺某权限点」的用例**：`前置条件` 第 1 条「操作人员」必须改成对齐真实预置的受限账号
- 账号名必须是环境 provision 脚本真实创建的，禁止自造、禁止默认 admin/超管
- 判定锚点是**前置条件/规则归类的限定语**，不是用例名是否点名账号
- 仅当用例确实是「全部数据范围 / 全权限」时才保留超管
- **动机**：用全权限 admin 测越权 = 逻辑不可证伪（admin 看得到一切、做得了一切），下游 `kdev-api-autotest` 会忠实渲染成假绿
- 与下游 `kdev-api-autotest` 约束 3「测试账号对齐真实预置」同源

### 🔧 修正

- **下游引用统一**：全部引用从 `kdev-api-test-scaffold` 改为 `kdev-api-autotest`（skill 描述、流水线图、前置条件注释、越权警告块内的下游引用）
- **Step 4 模板**：`用例名称` 从 `超级管理员 token，<HTTP 方法> <端点> <关键场景>` 改为 `<逐字沿用 UI 用例名称 — verbatim，禁止接口化/参数化/改写>`
- **Step 4 模板**：`前置条件` 第 1 条新增内联注释 `<越权/数据范围受限用例改为「对齐真实预置的受限账号」，禁默认超管，详见下方 🔴>`
- **Step 4 模板**：`前置条件` 第 2 条从「已通过 POST /login 拿到 admin access_token」改为「已通过 POST /login 拿到 access_token（受限用例用受限账号登录，非 admin）」
- **常见坑**：新增 2 条——`用例名称` 接口化改写、越权/受限用例照抄 admin 模板

### 📋 注册

- `plugin.json`：version 0.1.0 → 0.2.0，keywords 新增 `verbatim-contract`

---

## [0.1.0] — 2026-05-12

**首次发布**：从 `kdev-test-case` 的 API 通道拆分出独立 UI→API 转换 skill。

### 背景

测试用例 .md 产出后需要分流到 UI 自动化（Playwright）和 API 自动化（pytest 接口测试）两条流水线。手工逐条改写 API 用例有三个痛点：
- 16 条等价规则（规则 3/4/8 的"该跳"与规则 5/6 的"必测"边界）容易漏
- 编号/名称漂移——手工改写时容易"润色"用例名称、重新编排序号
- 字段命名不一致——`productLineId` vs `product_line_id` 混用

拆分方案：`kdev-uicase-to-apicase` 做 UI→API 转换，`kdev-api-autotest`（当时称 `kdev-api-test-scaffold`）做 pytest 四件套生成。中间靠文件契约（fielded-block `【测试用例信息】` + `TC-API-AR{XX}{YYY}{ZZZ}-{NNN}` 编号）对接。

### 核心内容

- **SKILL.md** 主 skill：6 步工作流（收齐输入 → 分类清点 → 按 AR 段平行改写 → 标准化每条 → 写收尾 3 段 → 自检交付）
- **7 条转换规则**：基本流配套（规则 1/2）、纯前端跳过（规则 3/4/8）、必测断言（规则 5/6）、等价类回收（规则 7）
- **5 段产出结构**：一~四段（按 AR 段分组）、第五段（统计）、第六段（跳过索引表）、第七段（自检清单）
- **编号规则**：`TC-API-AR{XX}{YYY}{ZZZ}-{NNN}`，9 位需求段 + 3 位流水号沿用 UI 用例号
- **字段命名**：遵循后端约定（RuoYi 系 camelCase / 其他后端按其约定），以 OpenAPI schema 为准

### 设计决策

- **为什么是独立 skill 而不是 kdev-test-case 的一个 mode**：UI→API 转换有独立的规则集（7 条）和输出结构（5 段），与 UI 用例渲染（Playwright handoff）是正交的流水线
- **为什么编号保持 UI 用例号而不重新排号**：便于交叉追溯——跳过的会让流水号不连续，但比"重新排号致使 UI 与 API 编号错位"更重要
- **为什么需要 3 段收尾**：统计表让用户一眼看清范围；跳过索引表让用户能追溯"为什么这条 UI 用例没出现在 API 文档"；自检清单让 reviewer 能快速验证规则是否全部落实

### 注册

- `.claude-plugin/plugin.json`：`name: kdev-uicase-to-apicase, version: 0.1.0`
- 注册到 KDevSec/kdev-agents marketplace
