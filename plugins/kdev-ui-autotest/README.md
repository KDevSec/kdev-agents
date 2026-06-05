# kdev-ui-autotest

Playwright + pytest + Element-Plus UI 自动化测试规范固化插件：把 6 大类规范（STEP 0 环境/菜单/弹窗实测前置、登录复用、资源清理、四件产物归档、Element-Plus 陷阱、用例命名、失败诊断）固化为下游项目（KDevSec / Gen9 / 可信评估 / vfadmin 等）的强制实践。

**第零原则（基座）**：测试脚本的目的是执行测试、发现 BUG，不是生成通过率高的 reports。红是产出，不是失败；遇到冲突永远选这条。

## 解决什么问题

基于 `playwrightmode` 模板（源项目 KDevSec/playwrighttest）反复翻车后沉淀的硬规则，解决 6 类高频问题：

1. **环境/菜单与 spec 漂移**：spec 文档常滞后于真实 UI——按钮名叫「新增项目」实际只叫「新增」、必填字段漏列。先做 5 分钟实测前置，省 5 小时调试
2. **Element-Plus 组件陷阱**：el-select 点不到、toast 抓不到、readonly 误判、dropdown 同名 label 冲突、Escape 关弹窗、`:text-matches` 不匹配空格——10 个已实证陷阱
3. **登录复用**：`logged_page` fixture 自动检测过期补登录，省每次用例 5-10s
4. **资源清理**：API 轨（毫秒级，推荐）+ UI 轨（兜底）双轨，LIFO + FK rank + 重试，防止孤儿数据
5. **四件产物归档**：`junit.xml` + 失败截图 + `defects_<ts>.csv` + `RUN_SUMMARY.md`，交付即附 evidence
6. **缺陷三分**：失败 → framework / script / real-defect 三分类，拒绝刷通过率

## 核心机制

### 五条不可妥协约束

| 约束 | 内容 |
|------|------|
| 1 | 不走 BasePage 直接拼 Element-Plus locator → 禁 |
| 2 | 失败三分（framework / script / real-defect），拒绝"修脚本让测试绿" |
| 3 | 四件产物归档，缺一不可 |
| 4 | 禁止静默跳过（skip/xfail 需显式理由 + 定期复检） |
| 5 | 用例池入口硬 gate：只对 `是否UI自动化=是` 的用例写 UI 脚本；`否` 分流到 `kdev-uicase-to-apicase`；`空白/待定` 打回补字段 |

### STEP 0（环境实测前置）

STEP 0 已迁出到独立插件 **[kdev-env-recon](../kdev-env-recon)**——登录测试环境 → 抓取左菜单全树 / 字段 / 弹窗 → 持久化为 `recon/menu_list.md` + 4 类 JSON + 截图。本插件在 `recon/menu_list.md` 就绪后走 STEP 1+。

本插件保留 fallback 能力：`assets/recon_env_bootstrap.py` + `references/env-recon-bootstrap.md`（`kdev-env-recon` 不可用时使用）。

### 标准 10 步开发流程（STEP 0 完成后）

```
前置 GATE（约束 5）→ grep "是否UI自动化=是" 过滤用例池
① 跑 tools/recon_elements.py 侦察目标页面
② 写/更新 PageObject（pages/<biz>_page.py）
③ 写/更新测试用例 .md 文档
④ 从 assets/test_arNN_skeleton.py 拿骨架
⑤ 写 pytest 用例
⑥ 跑 pytest --co 收集 → 确认全绿
⑦ 跑完整 suite → 失败三分
⑧ 写 defects_<ts>.csv + RUN_SUMMARY.md
⑨ 资源清理验证
⑩ 交付四件套
```

## 包含的 skill 与资产

| 类型 | 名称 | 作用 |
|------|------|------|
| skill | [kdev-ui-autotest](skills/kdev-ui-autotest/SKILL.md) | 主 skill：6 大规范 + 5 条约束 + 10 步流程 |
| assets | [test_arNN_skeleton.py](skills/kdev-ui-autotest/assets/test_arNN_skeleton.py) | 基本流/异常流用例骨架 |
| assets | [recon_env_bootstrap.py](skills/kdev-ui-autotest/assets/recon_env_bootstrap.py) | STEP 0 fallback 脚本 |
| assets | [test_case_doc_header.md.tpl](skills/kdev-ui-autotest/assets/test_case_doc_header.md.tpl) | 用例文档头部"测试环境与导航约定"模板 |
| references | [element-plus-pitfalls.md](skills/kdev-ui-autotest/references/element-plus-pitfalls.md) | Element-Plus 10 大陷阱 + 1.x→2.x 迁移附录 |
| references | [infra-standards.md](skills/kdev-ui-autotest/references/infra-standards.md) | 登录复用 + 资源清理双轨 + storage_state + XSS 录制 |
| references | [case-skeleton.md](skills/kdev-ui-autotest/references/case-skeleton.md) | 新增测试模块/PageObject 接入指南 |
| references | [failure-diagnosis.md](skills/kdev-ui-autotest/references/failure-diagnosis.md) | 用例失败诊断流程 |
| references | [env-recon-bootstrap.md](skills/kdev-ui-autotest/references/env-recon-bootstrap.md) | STEP 0 fallback 详细流程 |
| evals | [evals.json](skills/kdev-ui-autotest/evals/evals.json) | skill 质量回归 eval |

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件
claude plugin install kdev-ui-autotest@kdev-agents
```

## 触发

用户提到以下关键词时 skill 自动激活：
"写 / 加 / 补 / 接入 / 优化测试用例、test_arNN、TC-NNN、PageObject、el-select 点不到 / 下拉、toast 抓不到、is_field_readonly、defects_<ts>.csv、recon_elements、用例为什么挂、登录复用、资源清理、Element-Plus 自动化测试、playwrightmode、playwrighttest、UI 与 spec 对不上"

即使用户没明说"playwrightmode"，只要项目里有 `pages/base_page.py` + `conftest.auth_state` + `utils/cleanup_registry.py` + `tools/recon_elements.py` 等模板特征文件，也视为本 skill 适用范围。

## 与其他 kdev-* plugin 的关系

- **[kdev-env-recon](../kdev-env-recon)**：承担 STEP 0 环境实测前置。本 skill 在其产物 `recon/menu_list.md` 就绪后走 STEP 1+
- **[kdev-test-points](../kdev-test-points)** / **[kdev-test-cases](../kdev-test-cases)**：上游——产出测试点/测试用例 .md，本 skill 消费其中的 `是否UI自动化=是` 用例
- **[kdev-uicase-to-apicase](../kdev-uicase-to-apicase)**：并行——`是否UI自动化=否` 的用例分流到此插件做 API 自动化
- **[testcases-to-playwright-pipeline](../../README.md)**：下游——批量把测试用例 .md 转为 Playwright 脚本的流水线

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-ui-autotest@kdev-agents
```

## 演进历史

- **v0.2.0**（当前）：约束 5 硬 gate + STEP 0 迁出到 kdev-env-recon + Element-Plus 陷阱 7→10（含 1.x→2.x 附录）+ 资源清理双轨（API+UI）+ storage_state + XSS 录制 + 按钮空格定位修正
- **v0.1.0**：首次发布，6 大规范 + 4 条约束 + 10 步流程

详见 [CHANGELOG.md](CHANGELOG.md)。
