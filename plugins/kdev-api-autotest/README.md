# kdev-api-autotest

通用 **API 自动化测试方法论** skill —— 用 `pytest` + HTTP 客户端 **写 / 跑 / 诚实三分**任意 RESTful 后端的接口自动化测试。与具体后端、框架、公司项目无关。

> **第零原则（核心基座）**：API 测试脚本的目的是**执行测试、发现 BUG**，不是生成通过率高的报告。**红是产出，不是失败**；遇到冲突永远选这条。

> 旧称别名：`kdev-api-test-scaffold`。

## 解决什么问题

接口自动化最常见的烂尾不是"没写用例"，而是：
- 正向 wrapper 把后端的合法拒绝（403/422）误判成红，或反过来把异常流"弱绿"成 `assert status_code == 200`
- 测试账号与真实预置对不上 → 受限账号 / 越权 / 数据范围用例永远 skip
- 传输层抖动（登录态过期、连接重试）被 sleep+retry 掩盖成"偶发 flaky"，真缺陷一起被埋
- 跑完一堆绿，却没有可归档证据，也分不清失败是框架问题、脚本问题还是真缺陷

本 skill 把这些固化成 **6 条工程规范 + 失败三分 + 四件产物**，让"红"成为可信产出。

## 核心机制

### 6 条工程规范

| # | 规范 | 要点 |
|---|------|------|
| 1 | 分层测试代码结构 | 薄接口封装 → 复合动作 → 参数化数据 → 用例 |
| 2 | 正向/异常响应断言纪律 | 正向断业务、异常断拒绝；不把拒绝判红、不把异常弱绿 |
| 3 | 测试账号对齐真实预置 | 受限账号 / 越权 / 数据范围用例对齐真实账号体系 |
| 4 | 忠实断言不弱绿 | 禁止为过率改预期 / 弱化断言 / 吞异常 |
| 5 | 传输层治理 | 登录复用 / 重试只治连接，不掩盖断言级 flaky |
| 6 | 四件产物归档 + 失败三分 | 见下 |

### 失败三分（只用 LLM 判分类，计数 / 产 junit 用代码）

- **framework** — 测试框架 / 环境问题（连接、依赖、fixture）
- **script** — 用例脚本自身 bug（断言写错、数据备错）
- **real-defect** — 被测后端真缺陷 → 全录 `defects_<ts>.csv`，**保留红不洗绿**

### 四件产物（交付即附，缺一视为未执行）

`junit.xml` + 失败证据（响应体 / 日志）+ `defects_<ts>.csv`（即使 0 条也建空文件）+ `RUN_SUMMARY.md`

## 包含的 skill 与资产

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-api-autotest](skills/kdev-api-autotest/SKILL.md) | 主 skill：6 规范 + 失败三分 + 四件产物 |
| references | [pytest-toolbox.md](skills/kdev-api-autotest/references/pytest-toolbox.md) | pytest + HTTP 客户端分层结构工具箱 |
| references | [positive-negative-assertions.md](skills/kdev-api-autotest/references/positive-negative-assertions.md) | 正向/异常响应断言纪律 |
| references | [datascope-account-alignment.md](skills/kdev-api-autotest/references/datascope-account-alignment.md) | 测试账号对齐真实预置 |
| references | [infra-standards.md](skills/kdev-api-autotest/references/infra-standards.md) | 传输层治理（登录复用 / 重试只治连接） |
| references | [failure-triage.md](skills/kdev-api-autotest/references/failure-triage.md) | 失败三分判定 |
| references | [four-piece-recipe.md](skills/kdev-api-autotest/references/four-piece-recipe.md) | 四件产物归档配方 |
| evals | [evals.json](skills/kdev-api-autotest/evals/evals.json) | 3 个回归 eval + `inputs/` fixtures |

## 安装

```bash
claude plugin marketplace add KDevSec/kdev-agents
claude plugin install kdev-api-autotest@kdev-agents
```

## 触发

用户说以下任意关键词时 skill 自动激活：
"写 / 加 / 补 / 接入 / 优化 API 测试用例" / "API 自动化" / "接口测试脚本" / "pytest 接口用例" / "把接口用例落成 pytest" / "跑全量接口用例并三分" / "接口用例为什么挂" / "负向 / 异常用例断言" / "受限账号 / 越权 / 数据范围用例" / "四件 evidence / junit / defects.csv 归档" / "API 测试失败三分" / "禁止改被测让测试通过"

## 与其他 kdev-* plugin 的关系

- **[kdev-uicase-to-apicase](../kdev-uicase-to-apicase)**：上游——把 UI 用例转成接口用例 .md，本 skill 落成 pytest 四件套
- **[kdev-test-cases](../kdev-test-cases)**：上游——fielded 用例渲染，含可 API 自动化字段
- **边界**：本 skill 只管"写 / 跑 / 三分"的通用方法论；接口清单（OpenAPI / inventory）与接口用例 .md 视为已就绪的前置输入（由侦察 / 用例派生类流程产出）

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-api-autotest@kdev-agents
```

## 演进历史

- **v0.1.0**（当前）：首次发布——通用 API 自动化测试方法论 skill 从 `Functional-Test-Skill` canonical 源纳入 marketplace。6 工程规范 + 失败三分 + 四件产物 + 3 个 core eval。

详见 [CHANGELOG.md](CHANGELOG.md)。
