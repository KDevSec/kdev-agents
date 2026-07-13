---
name: kdev-zentao-sync
description: 把 kdev 字段化测试用例 .md 与 defects_*.csv 同步进禅道（ZenTao）——导入用例到库、创建测试单(testtask)并关联用例、提 BUG；另含两项只读能力：查询 BUG 状态(query-bugs)、回归判定(regress-bugs：已修复 bug × junit 结果对照出报告、不写回)。用户提到「同步禅道 / 提交到禅道 / 建测试单 / 导入用例到禅道 / 把缺陷提到禅道 / zentao 提 bug / 创建测试单 / 查禅道 bug / bug 状态 / 哪些 bug 已修复 / bug 回归 / 回归判定 / 已修复的能不能回归 / 已修复 bug 对照测试结果」时加载。用例+bug+查询+回归走纯 API；测试单无创建 API → 走 /browse。仅标准库 + 默认 dry-run。
---

# kdev-zentao-sync

把测试资产同步进禅道实例（REST API v1 + 必要时 /browse）。覆盖：**导入用例到库**、**创建测试单并关联用例**、**提 BUG**；外加两项**只读**能力——**查询 BUG 状态**（query-bugs）与**回归判定**（regress-bugs：已修复 bug × junit 结果对照、出报告、不写回禅道）。

## 何时用
- 把 kdev 字段化用例 `.md`（【测试用例信息】块）导入禅道产品用例库；
- 建测试单并把导入的用例关联进去；
- 把 `defects_*.csv` 里「真实-*」缺陷提为禅道 bug。
- **查 bug 状态**：按状态/提交人/模块/泳道(TC-AR vs TC-API)/标题过滤列 bug（query-bugs，只读）。
- **判回归**：拿一次测试运行的 junit.xml，对照已修复 bug 的 TC-ID，逐条判「回归通过/未过/无法回归/用例缺失」（regress-bugs，只读出报告，不动禅道状态）。

## 硬规则（继承项目第零原则 + 工作纪律）
- **默认 dry-run**，必须显式 `--execute` 才真写。**query-bugs / regress-bugs 是只读**（不改禅道），无 `--execute`；regress-bugs 只落**本地**回归报告，关单/重开由人工在禅道点。
- **全局参数放子命令之前**：`sync.py --cred X --product 1 --execute <子命令> ...`。放到子命令后会 argparse 报错（不是静默 dry-run，会 loud fail）。
- **凭据**从 gitignored `禅道.md`（`--cred` 指定）读，含 `ip/user/password` 三行，绝不硬编码、绝不进仓。
- **Fail Loud**：非 2xx raise、逐条计数落 `reports/<ts>/`，绝不静默 skip。
- **产物/凭据不进仓**：`禅道.md`、`__pycache__/`、`.pytest_cache/`、`reports/` 已 gitignore。
- **测试单走 /browse**：本实例无测试单创建 API（见下），浏览器交互一律用 gstack `/browse`（CLAUDE.md 硬规则，禁用 Playwright MCP）。
- **顺序**：先 `import-cases`（建库 + 回执 caseID）→ 再建测试单 /browse 并关联 → 执行后 `submit-bugs`。

## 能力前提（首次/换实例/换 product 先跑探测）
```bash
cd .claude/skills/kdev-zentao-sync/scripts
/usr/bin/python3 capability_probe.py --cred /path/to/禅道.md --product 1
```
输出能力矩阵 + 判断（哪些纯 API、哪个要 /browse），写 `reports/<ts>/capability_<ts>.json`。

## 三操作用法

### 1) 导入用例到库（纯 API）
```bash
cd .claude/skills/kdev-zentao-sync/scripts
# dry-run（只读 login+去重+打印）
/usr/bin/python3 sync.py --cred 禅道.md --product 1 import-cases --md <用例.md>
# 真写（建用例，回执写 reports/<ts>/imported_cases.json = {tc_id: caseID}）
/usr/bin/python3 sync.py --cred 禅道.md --product 1 --execute import-cases --md <用例.md>
# 归模块：本实例无模块 GET API → 按 md『所属模块』全路径映射到叶子模块 id（id 先经 /browse 产品菜单维护，见 §4）
/usr/bin/python3 sync.py --cred 禅道.md --product 1 --execute import-cases --md <用例.md> \
  --module-map "产品管理中心/产品线管理=8,系统管理/用户管理=9,系统管理/日志管理/操作日志=11"
# 兜底单值：模块名未命中 --module-map 时落到 --module（默认 0=根）
```
按**用例名称**在产品内去重；同名跳过不重复建。
- **对应需求(story) 自动关联**（无需 flag）：导入前拉需求库，按用例 `需求编号` 的 AR 主键匹配 story 标题里的 AR → 写 `story` 字段；未命中 **[WARN] loud surface**、留空不乱填。
- **所属模块(module) 三级解析**：`--module-map "名=id,名=id"`（显式，最高优先）> **story.module 自动反推**（次选：用例自动归到「其对应需求 story 所在模块」，因用例库与 story 共用同一棵树，无需任何 flag、绕开 §4 /browse 查 id）> `--module` 兜底。三者都没命中且『所属模块』非空时 **[WARN]** loud surface。**当目标模块下已有需求时，连 `--module-map` 都不用给**（见 §4 顶部捷径）。

### 2) 提 BUG（纯 API）
```bash
/usr/bin/python3 sync.py --cred 禅道.md --product 1 submit-bugs --csv <defects_*.csv>            # dry-run
/usr/bin/python3 sync.py --cred 禅道.md --product 1 --execute submit-bugs --csv <defects_*.csv>   # 真提交
```
只提 `原因分类` 以「真实-」开头的行；按 bug title 内 `[TC-ID]` 去重。
> ⚠️ 本实例 v1 bug create/edit **丢弃 `steps`(正文)与 `keywords`**（实测，PUT/POST 都补不上）→ 只存 title+结构字段。故 submit-bugs 把 `用例ID|原因分类|失败摘要` 都打进 **title**(≤255，[TC-ID] 恒在最前作去重锚点)；截图路径/全量明细 v1 存不下，留在本地 `defects_*.csv` 与 `reports/`，真要进禅道须走 /browse 在 bug 编辑页补。

### 2a) 查询 BUG 状态（query-bugs，纯 API 只读）
```bash
# 列全部 bug（无过滤）
/usr/bin/python3 sync.py --cred 禅道.md --product 1 query-bugs
# 只看已修复的 UI 泳道 bug（TC-AR=UI/playwrighttest，TC-API=API/apitest）
/usr/bin/python3 sync.py --cred 禅道.md --product 1 query-bugs --status resolved --tc-prefix TC-AR
# 组合过滤 + 落 JSON
/usr/bin/python3 sync.py --cred 禅道.md --product 1 query-bugs \
  --status active,resolved --opened-by fanxiaotian01 --module 8 --title-contains 分页 --resolution fixed --json
```
过滤维度：`--status`（逗号多值）/`--opened-by`/`--module`/`--tc-prefix`（TC-AR·TC-API 分泳道）/`--title-contains`/`--resolution`。打印 id/状态/解决方案/提交人/解决人/日期/模块/TC-ID/标题 + 分布统计；`--json` 额外落 `reports/<ts>/bugs_query_<ts>.json`。**只读，无 `--execute`。**

### 2b) 回归判定（regress-bugs，纯 API 只读 + junit）
把「已修复 bug 的 TC-ID」和「一次测试运行的 junit.xml 结果」逐条对照，判每条 bug 能不能回归：
```bash
# playwrighttest 回归时显式产 junit（默认不产 junit，回归输入例外）：
#   /usr/bin/python3 -m pytest tests/ -k "<TC 节点表达式>" --junitxml=reports/<ts>/junit.xml
# apitest 原生产 junit_<ts>.xml，直接喂。
/usr/bin/python3 sync.py --cred 禅道.md --product 1 regress-bugs \
  --results <junit.xml> --tc-prefix TC-AR          # 默认 --status resolved
```
判定口径（每条 bug 按其 TC 结果聚合，多 TC 取最坏态）：
- ✅ **回归通过**（用例全 PASS）→ 可在禅道关单；
- 🔴 **回归未过**（任一 FAIL）→ 修复没生效 or 被别的 active 缺陷挡住；
- ⚪ **无法回归**（任一 SKIP，无 FAIL）→ 依赖未就绪（环境/数据，如 CQ 未激活）；
- ❓ **用例不在本次结果**（TC 没跑）；⚠️ **标题无可解析 TC**（人工）。

产 `reports/<ts>/regression_<ts>.md`（表）+ `.json`（机读）。**只读，不写回禅道状态**（关单/重开人工点）。junit 里 `test_arNN_gN_NNN` / `test_tcNNN` 命名的 testcase 才能映射；命名不符的计入 `unmatched` 并 surface；一条都映射不到则 Fail Loud raise（拒绝静默出空报告）。多 TC bug（如 `[TC-API-AR0300100-G2-006/007/008]`）自动展开逐条判、按最坏聚合。

### 3) 创建测试单 + 关联用例（/browse —— 本实例无创建 API）
> 实测：`POST /api.php/v1/testtasks` 返回 200 空 body 但**不创建**（v1 测试单只读）。故建单走 gstack `/browse` 驱 UI。GET 列表/详情在顶层 `/api.php/v1/testtasks` 可用（用于核验）。

**已验证的 /browse 流程**（2026-06-20 headed Chrome 实跑通；自签证书实例）：
1. `connect`（headed）；`goto https://<ip>/`。
2. **绕过自签证书**：在证书警告页直接 `type "thisisunsafe"`（Chrome 魔法词，放行）。
3. **登录**：在 `user-login-*.html` 填用户名/密码（`snapshot -i` 取 @ref）→ 点「登录」。
4. **建单**：`goto https://<ip>/testtask-create-<productID>.html` → 切进 `#appIframe-qa` iframe。
   - 字段：`name`（名称）、`execution`（迭代，下拉）、`build`（**版本，必填！**漏了会 `{"result":"fail","message":{"build":["版本不能为空"]}}`）、`owner`、`type`（type[]，如 integrate）、`begin`/`end`。
   - **陷阱**：下拉是 chosen.js（隐藏真 select，`select` 命令会超时）。用 jQuery 设值：`$('#build').val('1').trigger('chosen:updated').trigger('change')`。且 `#submit` 点击会触发重渲染**重置 build** → 必须**原子设值后立即提交**（同一段 js 里设完全部字段紧接着同步 XHR 提交 `#dataform`），别分两步。
   - 成功响应：`{"result":"success","message":"保存成功"}`。
5. **关联用例**：`goto https://<ip>/testtask-linkCase-<taskID>.html` → 切 iframe → 勾 `cases[]` 复选框（用 `closest('form')` 锁定含复选框的表单）→ 同步 XHR 提交。
6. **核验**：`GET /api.php/v1/testtasks?limit=50` 看新单；`testtask-cases-<id>.html` 看已关联用例。
7. 完事 `disconnect` 收起浏览器。

### 4) 建产品模块树 + 取模块 id（/browse —— 本实例无模块 API）
> 🟢 **先试无需 /browse 的捷径（story.module 反推）**：禅道 v1 虽无模块 GET API，但 **story 记录带 `module` 字段**，用例库与 story 共用同一棵模块树。若目标模块下**已有需求**，`import-cases` 会自动按 `用例需求编号 → story → story.module` 反推 module id 并归类（`story_module_map`，无需 `--module-map`、无需本节 /browse）。**只有「目标模块下尚无任何 story」时才需要下面的 /browse 建模块流程。**（2026-06-30 实战：版本二 157 用例靠此自动归到 项目管理=12 / 版本管理=13，未碰 UI。）
> ⚠️ **版本依赖**：下面流程在**旧版禅道**实测验证；**新版 SPA（如开源版 15.7.1）实测失效**——headed 登录后内容区 XHR 返回 401、只渲染导航壳、`#appIframe-*` 选择器全失效，整套跑不通。优先用上面的 story 反推法。
> 实测（2026-06-22）：v1 无模块 CRUD/GET 端点 → 建模块/查 id 走 UI。**必须在「产品」菜单下维护**（`tree-browse-<pid>-story`，产品级模块树）：这样模块全局可见、**用例库与之共用同一棵树**（用例 module 字段可直接挂这些 story 模块 id，实测 case→module=8 在用例库正确显示在该模块下）。**勿用「用例库→维护模块」**（`tree-browse-<pid>-case`，case 型独立树，不全局）——此法已废弃。
1. `connect`（headed）→ goto 根 → 证书页 `type "thisisunsafe"` → 登录（同 §3 步 1-3；headless 无法过自签证书，必须 headed）。
2. `goto .../product-browse-<pid>.html` → 切 `#appIframe-product` → iframe 内点「维护模块」（href `/tree-browse-<pid>-story.html`，即「产品→模块」tab）。
3. **建根级**：iframe 内空 `modules[]`/`shorts[]` 填模块名+简称 → 点「保存」（action `tree-manageChild-<pid>-story.html`）。
4. **建子级（层级）**：`location.href='/tree-browse-<pid>-story-<父moduleId>-0-.html'`（该页直接渲染 `parentModuleID=父id` 的子模块表单）→ 填子模块名 → 保存。逐层递归到叶子。
5. **取 id**：树节点链接 `tree-browse-<pid>-story-<id>-0-.html` 的 `<id>` 即模块 id（`$B js` 解析 `a[href*=story-]`）；保存后须 `frame main`→重切 iframe 再读（导航会失效旧 frame 句柄）。
6. `--module-map` 用 **md『所属模块』全路径**作键 → 映射到**叶子模块 id**（如 `产品管理中心/产品线管理=8`）；md 所属模块 = 用例标题菜单路径把 `-` 换 `/`。
7. 完事 `disconnect`。

## 本实例已知事实（KDevSec）
- product=1 (KDevSec)，execution=1 (KDevSec 迭代一)，build id=1。
- REST `DELETE /testtasks|/testcases|/bugs /{id}` 可用（清理 smoke 产物用）。
- 无 v1 模块端点（产品详情 `modules=null`）→ 建模块/查 id 走 /browse **产品菜单**维护页（§4），用例库共用此 story 模块树。**当前产品模块树**：`产品管理中心(6)/产品线管理(8)`、`系统管理(7)/用户管理(9)`、`系统管理(7)/日志管理(10)/操作日志(11)`；叶子 8/9/11 挂用例（70/8/1，2026-06-22 实建实导）。后续新增 `产品管理中心/项目管理(12)`、`产品管理中心/版本管理(13)`、`统一数字签名(14)`（2026-06-30，story 7~22 已落这些模块）。⚠️ 早期误用「用例库→维护模块」建的 case 型模块 `产品线管理中心(1)/产品管理中心(2)/系统管理(3)` 不全局、已弃，待清理。import `--module-map` 用全路径键 → 叶子 id；**或不给 --module-map 直接靠 story.module 自动反推**（目标模块下有需求时，见 §4 顶部捷径）。
- 需求库已有 story#1~6，标题嵌 AR 编号（`AR-PRL-FUN-01.001~005.00` + `AR-AUTH-FUN-04.001.00`）→ `import-cases` 自动按用例 `需求编号` 关联 story（无需 flag）。`testcase` POST 接受 `story` 字段，建后 `storyVersion` 自动置 1（实测 case#7：story=1/module=2 落库）。
- **无 v1 文件上传端点**（`/api.php/v1/files`、`/bugs/{id}/files` 均 404，内嵌 base64 图也被净化器剥除，2026-06-20 实测）→ 截图无法经 API 进禅道。
- **存储标题会 HTML 转义**（实测 2026-06-22：`「\<script\>」` 存成 `「\&lt;script\&gt;」`）。`import-cases` 去重已 `html.unescape` 回原文再比，含 `<>&` 特殊字符的标题也能正确去重、重跑幂等；早期按原文比对会对这类标题每跑重复建（已修，见 `existing_case_titles`）。**keywords 不持久**（testcase POST 后存空，同 bug）→ 不能拿 TC-ID 当去重锚点。
- **v1 bug create/edit 丢弃 `steps`(正文)与 `keywords`**（实测：建/PUT/POST 均存空）→ 只存 title+结构字段。故 bug 正文/截图路径/失败摘要全量明细 v1 存不下，submit-bugs 把关键分诊打进 title、明细留本地 `defects_*.csv`/`reports/`，真要进禅道正文/附图须走 /browse 在 bug 编辑页补。
- **v1 testcase PUT 改不了 `module`**（实测 2026-06-30）：`{module:N}` 单字段、及「GET 全字段回填 + 改 module」两种 PUT 都返回 200 但 `module` 不变（同上条 bug PUT 丢字段）→ **重新归类已建用例只能删 + 带 module 重导**（删+重导会换 caseID）。
- **DELETE 是软删除**（实测 2026-06-30）：`DELETE /testcases/{id}` 返回 success，但随后 `GET` 仍返回该记录，靠 `deleted` 字段区分，其值是**布尔 `true`（非字符串 '1'）** → 删除核验须读 `deleted` 字段（兼容 `true`/`'1'`），别用「GET 查不到」判定。

## 脚本结构（薄壳 + 确定性脚本）
- `case_md_parser.py` 解析【测试用例信息】块（纯函数）
- `mapper.py` 中性记录→禅道 payload（纯映射；步骤 N 行、整块预期挂最后一步 expect；`base_ar()` 归一 AR 主键；按 `ar2story`/`name2module` 填 story/module）
- `zentao_client.py` 传输层（token 登录/GET·POST/分页/DELETE；v1 无文件上传端点故无 upload）
- `capability_probe.py` Phase-0 只读能力探测
- `bug_ops.py` 纯函数（无网络/无文件 IO）：`filter_bugs`（query 过滤）/`canon_bug_tcs`·`canon_node`（TC-ID 规范化，去 TC-/API- 前缀 + 多 TC 展开）/`parse_junit_text`（junit→{TC:状态}）/`correlate_regression`（bug×结果→回归判定）
- `sync.py` 编排：`import-cases` / `submit-bugs` / `query-bugs`（只读列 bug）/ `regress-bugs`（只读 bug×junit 出回归报告）（`create-testtask`/建模块走 /browse 流程 §3/§4，非子命令）
- `tests/` 离线单测（parser/mapper/client/sync/bug_ops，全 mock 无网络；75 条）
