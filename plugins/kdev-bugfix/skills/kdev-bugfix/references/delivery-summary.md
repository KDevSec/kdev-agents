# delivery-summary

修复交付摘要的**统一三段格式**，跨多个出口共用：

- 禅道 bug 状态回写时的 comment 字段（步骤 8.1）
- 会话终态报告（步骤 8.2）
- 产物文档（OpenSpec 模式 `design.md` 末尾 / 纯模式 `fix.md` 末尾）的 `## Delivery_Summary` 段
- commit message body（可选）

## 格式定义

```
【根因分析】
<1-3 句话浓缩 Root_Cause。回答"为什么 bug 产生"。同 fields-design.md Root_Cause 段的"好例子"标准——精确到哪行代码 + 哪个条件 + 为什么 trigger>

【影响范围】
<浓缩 Impact_Scope。含 3 个维度：
  - 受影响用户/角色（如：所有未验证邮箱的用户 / 单产品线运营 / 全量用户）
  - 受影响数据/路径/功能（如：登录路径，主页跳转 / 订单金额计算 / 4 个 multipart 端点）
  - 严重度 + 时间窗口（如：P1，自 2026-05-01 上线 v1.2.0 后）>

【修复方案】
<浓缩 Fix_Description。含 3 个要点：
  - 改了什么（文件 + 函数 / 行号）
  - 为什么这么改（与 Alternatives_Considered 对应；最小变更 vs 治标 vs 重写架构的取舍）
  - 回归测试如何 cover（测试名 + 覆盖的等价类）>
```

## 字段来源对照

| 三段 | 来源（OpenSpec 模式） | 来源（纯模式） |
|------|----------------------|---------------|
| 根因分析 | `design.md` `## Root_Cause` 段 | `fix.md` `## Root_Cause` 段 |
| 影响范围 | `proposal.md` `## Why` "影响范围" + Bug Context `### Environment` 表 + `Capabilities` Modified | `bug-report.md` `## Symptom` + `## Environment` 表 |
| 修复方案 | `design.md` `## Fix_Description` + `tasks.md` T2-T3 + T1 回归测试名 | `fix.md` `## Fix_Description` + `## Files_Changed` + `## Testing_Strategy` |

## 落点速查

| 场景 | 落点 | 说明 |
|------|------|------|
| 禅道 resolve comment | `curl POST /bugs/<id>/resolve` body 的 `comment` 字段 | 主要场景：让 QA 关单时看清楚 |
| 会话终态报告 | SKILL.md 步骤 8.2 的 `## Bugfix 完成` 报告 | 用户看到 skill 跑完后的总结 |
| OpenSpec `design.md` 末尾 | 新增 `## Delivery_Summary` 段（在 `## Review_Decisions` 之前） | 产物归档，未来 grep 可追溯 |
| 纯模式 `fix.md` 末尾 | 同上 | 同上 |
| commit message body（可选） | 在 `Root cause:` / `Regression test:` 行之后追加完整三段 | 适合 P0 hotfix / 安全 bug，需要 commit 本身就能讲清楚 |

## 风格规范

**必须**：

- 每段用 **`【段名】`** 中文方括号开头——便于禅道纯文本备注 + git log + 终端输出统一渲染
- 段间用**一个空行**分隔
- 不要用 markdown emphasis（`**` / `*` / `#`）——禅道富文本编辑器渲染丢失，且 git log 显示难看
- 写**完整自然语言**，不要嵌套点列表（三段已经是结构化的）

**长度**：

- 总长度建议 **200-500 字符**（过长不利于禅道列表预览 / commit message 一屏；过短信息不全）
- 每段 1-3 句话最佳
- 长度参考：
  - 禅道 comment：200-300 字符（让 QA 列表页摘要可见）
  - design.md / fix.md `## Delivery_Summary` 段：300-500 字符（产物归档可详）
  - commit message body：200-400 字符（让 `git log` 一屏可读）

## 示例

```
【根因分析】
用户登录后访问 /api/me 时，cookie-parser 中间件挂在 express.json() 之后导致 multipart 路由读不到 session_id cookie，Express 4.18 的默认中间件顺序对 multipart body parser 不兼容。

【影响范围】
所有走 multipart 提交的鉴权接口（用户头像上传、Excel 导入、附件上传共 4 个端点），自 2026-05-01 上线 v1.2.0 后受影响。受影响用户：所有已登录且使用上述功能的用户。严重度 P1（核心功能局部失效，可绕开但用户体验严重退化）。

【修复方案】
src/app.ts 第 42 行把 cookie-parser 挪到 express.json() 之前，确保 cookie 解析在所有 body parser 之前完成。src/routes/me.ts 第 28 行添加 session_id 为空时的显式 401 防御（避免未来再有类似中间件顺序问题时直接 500）。回归测试 tests/regression/auth-cookie-order.test.ts 覆盖：(1) JSON 路由 + cookie 仍可用；(2) multipart 路由 + cookie 修复后可用；(3) 无 cookie 的 multipart 路由返回 401。
```

## 与既有字段的关系

三段摘要**不替代** `design.md` / `fix.md` 里的完整字段——它是**浓缩交付**版本，方便：

- QA 关单时不需要打开产物文件就能看清根因 + 影响 + 修法
- skill 跑完后用户能口头复述/转述给非技术干系人
- 未来同类 bug `grep -A 3 "【根因分析】" openspec/changes/` 可批量提取

完整细节（含 Alternatives_Considered / Risks / Spec_Impact / Follow_Up / Review_Decisions）**仍按 fields-design.md / fields-pure-mode.md 留在原字段**。三段只是**导出视图**，不是**主存储**。

## P0 hotfix 路径下的特殊处理

P0 hotfix 时为了快速发 commit + 立即开始恢复服务：

- 步骤 7 commit 时 `## Delivery_Summary` 的三段**允许填占位符**（`<待 7.1 后补>`）
- 步骤 7 commit 完成 → 8.1 禅道回写**之前**，必须把占位符替换为实际内容（禅道 comment 不能是占位符）
- 8.1 完成后回填到 design.md / fix.md 的 `## Delivery_Summary` 段

## 不要做的事

- **不要把三段当成 Root_Cause / Fix_Description 字段本身**——它们是**衍生视图**，原字段仍要按 fields-* 模板完整填
- **不要在三段里堆完整 stack trace / 大段日志**——这些进原字段，三段是浓缩
- **不要省略段头 `【XX】`**——下游 grep / 禅道渲染依赖这个分隔符
- **不要用英文段头**（`[Root Cause]`）——禅道 + 团队习惯是中文，统一中文段头
