# kdev-api-autotest CHANGELOG

## [0.1.0] — 2026-06-16

**首次发布**：通用 API 自动化测试方法论 skill 从 `Functional-Test-Skill` canonical 源纳入 kdev-agents marketplace——用 pytest + HTTP 客户端 写 / 跑 / 诚实三分任意 RESTful 后端的接口自动化测试，与具体后端 / 框架 / 项目无关。

### 核心内容

- **SKILL.md** 主 skill：固化 6 条反复验证的工程规范——分层测试代码结构（薄接口封装 → 复合动作 → 参数化数据 → 用例）/ 正向·异常响应断言纪律 / 测试账号对齐真实预置 / 忠实断言不弱绿 / 传输层治理（登录复用·重试只治连接，不掩盖断言级 flaky）/ 四件产物归档 + 失败三分（framework / script / real-defect）。
- **第零原则**：测试脚本目的是执行测试、发现 BUG，不是生成通过率高的报告——红是产出不是失败；遇冲突永远选这条。

### 资产

- `references/`（6 篇）：
  - `pytest-toolbox.md` — pytest + HTTP 客户端分层结构工具箱
  - `positive-negative-assertions.md` — 正向/异常响应断言纪律
  - `datascope-account-alignment.md` — 测试账号对齐真实预置（受限账号 / 越权 / 数据范围）
  - `infra-standards.md` — 传输层治理（登录复用 / 重试只治连接）
  - `failure-triage.md` — 失败三分（framework / script / real-defect）判定
  - `four-piece-recipe.md` — 四件产物归档配方（junit.xml + 失败证据 + `defects_<ts>.csv` + RUN_SUMMARY.md）
- `evals/evals.json` — 3 个回归 eval + `inputs/` fixtures（`openapi_snippet.json` / `provision_snippet.py` / `widget_api_cases.md` / `failing_output.txt` / `failing_skips.txt`）

### 注册

- `.claude-plugin/plugin.json`：`name: kdev-api-autotest, version: 0.1.0`
- 注册到 kdev-agents marketplace（`marketplace.json` 追加条目）
- 仓库根 README 插件表 + 安装命令 + 更新命令 + 目录树新增条目

### 相关文档

- 上游：[kdev-uicase-to-apicase](../kdev-uicase-to-apicase)（UI→API 用例转换，产出接口用例 .md）/ [kdev-test-cases](../kdev-test-cases)（fielded 用例渲染，含 API 自动化字段）
- 旧称别名：`kdev-api-test-scaffold`
