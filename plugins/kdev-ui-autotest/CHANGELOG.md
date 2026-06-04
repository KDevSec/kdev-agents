# kdev-ui-autotest CHANGELOG

## [0.2.0] — 2026-06-04

**约束 5 硬 gate + STEP 0 解耦 + Element-Plus 陷阱扩展 + 资源清理双轨。**

4 个文件改动（SKILL.md + element-plus-pitfalls.md + env-recon-bootstrap.md + infra-standards.md），累计 ~300 行净增。

### ✨ 新增功能

#### 约束 5 — 用例池入口硬 gate

- **新增第 5 条不可妥协约束**：只对 `是否UI自动化=是` 的用例写 UI 自动化脚本
- `grep -nE "是否UI自动化[：:][[:space:]]*(是|Y|yes|true|✓)" 测试用例.md` 过滤候选池
- 三种字段值处理：
  - `是/Y/yes/true/✓` → ✅ 放行
  - `否/N/no/false` → ❌ refuse，分流到 `kdev-uicase-to-apicase`
  - `待定/TBD/空白/缺失` → 🟡 打回 `kdev-test-cases` 补字段
- **显式 override 通道**：用例 `【测试用例信息】` 块内追加 `# override-ui-automation: <理由>` 注释可放行，所有 override 记入 `RUN_SUMMARY.md` 「override 清单」
- **动机**：阻止 `是否UI自动化=否` 的用例（纯接口校验/后端事件断言/日志审计/性能/SSO）硬塞 UI 通道 → 断言被迫弱化 → 假绿 → 违反第零原则
- **设计来源**：约束 4（否定性 UI 假 SKIP）的同类暗债沉淀路径——写下时是真的、没人主动复检、注释→docstring→optimize→reason 四处复制成"共识"，最终 4 条 P2 用例假 SKIP 一整迭代

#### STEP 0 迁出到独立 skill `kdev-env-recon`

- STEP 0（环境/菜单/弹窗实测前置）的 6 步标准动作**全部迁出**到独立 skill `kdev-env-recon`
- 本 skill 调用方式从"自己跑 `recon_env_bootstrap.py`"改为"调用 `Skill(skill='kdev-env-recon')`"
- 标准 10 步流程新增**前置 GATE**（step ① 之前）：约束 5 用例池过滤
- 新增用例流程从 0→1→2→3→4 调整为 **0（用例池过滤）→ 1（调 kdev-env-recon）→ 2→...**（6 步）
- **Fallback**：本 skill 保留 `assets/recon_env_bootstrap.py` + `references/env-recon-bootstrap.md`（`kdev-env-recon` 不可用时使用）

#### Element-Plus 陷阱 7 → 10

**坑 8 — 列表搜索区 + 弹窗"同名 label"冲突**：
- 典型 EL 后台管理页面同时有两个区域用相同字段 label（列表搜索区 + 新增/编辑弹窗）
- 全局 selector + `.first` 必踩；修复为 `_form_item_locator` 智能限定 `.el-dialog:visible`
- 所有 `fill_input_by_label / _open_select_dropdown / clear_select / get_field_error` 统一走智定定位器
- label selector 用 `:text-matches("^X\s*[：:]?\s*$")` 容错尾随冒号

**坑 9 — `keyboard.press("Escape")` 在 EL 2.x dialog 内是破坏性动作**：
- 旧 EL 1.x dialog 不响应 Escape，无害；EL 2.x dialog 默认 `close-on-press-escape: true`
- Escape 把整个弹窗关掉 → 后续 `.el-dialog:visible` 空 → 一切超时
- 修复：dialog 内改用点 body 空白处（`.el-dialog__body` 或 `.el-dialog__header`）收下拉
- **审计动作**：接入新项目时 grep 所有 `keyboard.press("Escape")`，标注触发上下文

**坑 10 — `:text-matches("X\s*Y")` 不匹配带 ASCII 空格的文案**：
- 中文按钮实测文案「确 定」「取 消」「保 存」带半角空格
- `:text-matches("确\\s*定")` → count=0（Playwright text engine 归一化层不按预期匹配 ASCII 空格）
- **规则**：带空格按钮必须用 `:has-text("确 定")` **字面量写空格**
- 同步修正 `env-recon-bootstrap.md` 和 `test_case_doc_header.md.tpl` 中曾推荐的错误写法

#### EL 1.x → 2.x 迁移附录

- 跨大版本接入时 class hook 对照表（`.el-input__inner` → `.el-select__input` 等）
- 实测 dump 命令：`page.evaluate(...)` 输出"控件类型矩阵"，与 `recon/menu_list.md` 交叉校验
- **冲突时以 DOM 真值为准**，同时反向修 `menu_list`
- 真实踩坑：spec 写「el-select」实测是 `el-cascader` → 22 条 AR-05 用例 100% 失败

#### 资源清理：单轨 → 双轨

**API 轨（推荐，毫秒级）**：
- `cleanup.add(rtype, id)` 紧跟资源创建后注册（**禁止延迟到断言之后**）
- `CleanupRegistry` 算法：类型内 LIFO + 类型间 FK rank 排序 + 第一遍失败 → deferred → 再试一次 → 仍失败 warn
- `ApiClient` 子类化命名契约：`add_<resource> → int` / `delete_<resource>(id, ignore_missing=True) → bool` / `find_<resource>` / `list_<resource>`

**UI 轨（兜底，秒级）**：
- 保留原 PageObject `save()` → `_emit_resource_created("rtype", name)` 机制
- 两条轨道可并存：业务有 API 走 API 轨；UI-only 资源走 UI 轨

**反例从 3 个扩展到 4 个**：新增 `cleanup.add` 延迟到断言之后 → 资源泄漏（源项目曾因此累积孤儿数据 14 productlines + 5 projects）

#### 基础设施增强

- **`storage_state` 落盘**：`APP_AUTH_STATE_FILE=.auth_state.json` 后，`auth_state` fixture 持久化 storage_state（默认 TTL 1800s），本地反复跑单条用例省 5-10s/次。**必须 `.gitignore`**
- **page-level XSS / dialog 录制**：`conftest.page` 默认挂 `page.on("dialog", ...)` 录制 alert/confirm/prompt 消息到 `request.node._xss_alerts`，自动 dismiss 避免阻塞

### 🔧 修正

- SKILL.md：不可妥协约束数量 4→5、STEP 0 承担方改为 `kdev-env-recon`、用户场景速查表更新
- `env-recon-bootstrap.md`：按钮定位从 `:text-matches("确\\s*定")` → `:has-text("确 定")`
- `test_case_doc_header.md.tpl`：按钮文案空格约定从 `:text-matches("确\\s*定")` → `:has-text("确 定")`

---

## [0.1.0] — 2026-05-19

**首次发布**：从源项目 KDevSec/playwrighttest 的 `playwrightmode` 模板固化为独立 plugin。

### 核心内容

- **SKILL.md** 主 skill：6 大规范 + 4 条不可妥协约束 + 10 步标准开发流程
- **第零原则**：测试脚本目的是发现 BUG，不是刷通过率
- **STEP 0** 环境/菜单/弹窗实测前置（内置于本 skill）
- **约束 1**：不绕过 BasePage 直接拼 Element-Plus locator
- **约束 2**：失败三分（framework / script / real-defect）
- **约束 3**：四件产物归档
- **约束 4**：禁止静默跳过

### 资产

- `assets/recon_env_bootstrap.py` — STEP 0 一键脚本
- `assets/test_arNN_skeleton.py` — 基本流/异常流用例骨架
- `assets/test_case_doc_header.md.tpl` — 用例文档头部模板
- `references/element-plus-pitfalls.md` — 7 大陷阱
- `references/infra-standards.md` — 登录复用 + UI 轨资源清理
- `references/case-skeleton.md` — 新增模块接入指南
- `references/failure-diagnosis.md` — 失败诊断流程
- `references/env-recon-bootstrap.md` — STEP 0 详细流程

### 注册

- `.claude-plugin/plugin.json`：`name: kdev-ui-autotest, version: 0.1.0`
- 注册到 KDevSec/kdev-agents marketplace
- 仓库根 README 插件表新增条目
