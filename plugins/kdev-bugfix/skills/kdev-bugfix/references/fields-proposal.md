# fields-proposal

OpenSpec 模式 — `openspec/changes/<bug-id>/proposal.md` 的 bugfix 字段补充。

**先跑 `openspec instructions proposal --change <bug-id>`** 拿 upstream prompt，再按本文补 bugfix 扩展字段。

字段命名规则：snake_case + 首字母大写（`Steps_to_Reproduce`、`Root_Cause`），固定不可改——便于 `grep -A 2 "Root_Cause:" openspec/changes/` 跨 bug 检索。

## frontmatter（YAML 段，必须）

```yaml
---
bug_source: zentao | direct
# 仅 bug_source=zentao 时填以下字段：
zentao_bug_id: 12345
zentao_url: https://zentao.example.com/bug-view-12345.html
zentao_severity: 2                # 1=致命, 2=严重, 3=一般, 4=轻微
zentao_priority: 2
zentao_opened_by: qa01
zentao_opened_date: 2026-05-10
---
```

详见 [zentao-integration.md §2](zentao-integration.md)。

## upstream 三段（Why / What Changes / Capabilities）的 bugfix 写法

### Why

```markdown
## Why

<Symptom 一句话>。影响范围：<受影响用户群体 / 数据范围 / 时间窗口>。
<触发上报的原因：「线上 P0」「客户反馈」「QA 发现」「我自己跑 E2E 看到」等>。
```

### What Changes

```markdown
## What Changes

- 修复 `<file 或模块>` 中 <Root_Cause 一句话>（精确点见 design.md）
- 新增回归测试 `<test 文件路径>`

**Breaking changes**：无 / <如有：列出>
```

步骤 5.2 实施完后回来精确化（步骤 2 写初稿即可，文件路径可能在步骤 4.4 写测试后才能精确）。

### Capabilities

```markdown
## Capabilities

**New Capabilities**：无（本变更只修复既有 capability，不引入新能力域）

**Modified Capabilities**：
- `<capability-name>`（如 `user-auth` / `order-checkout`）：修复 <bug 现象>，spec 行为保持不变 / 修订（如修订见 specs/<name>/spec.md delta）
```

如本次实际没有 spec 行为修订（最常见），写"spec 行为保持不变"。命中 Spec_Impact 时写"spec 行为修订见 specs/<name>/spec.md delta"。

## Bug Context（bugfix 扩展段——upstream 默认 proposal 模板没有，本 skill 强制加）

```markdown
## Bug Context

### Symptom
<一两句描述用户能直接感知到的现象>

### Steps_to_Reproduce
1. <第 1 步>
2. <第 2 步>
3. <第 N 步，触发的那一刻>

**前置条件**：
- <如：用户已注册但未验证邮箱>

### Expected_Behavior
<应当发生什么。一句话>

### Actual_Behavior
- **错误信息**：
  ```
  <stack trace / 控制台输出 / 错误码 / HTTP response>
  ```
- **截图**：`./screenshots/<filename>.png`（如适用）
- **日志摘录**：
  ```
  <时间戳 + 关键日志行>
  ```

### Environment
| 维度 | 值 |
|------|----|
| OS / 平台 | <如 macOS 14.5 / Ubuntu 22.04> |
| 浏览器（如适用） | <Chrome 124 / Safari 17> |
| 运行时 | <如 Python 3.11.7 / Node 20.11> |
| 项目版本（git sha 或 tag） | <如 v1.2.3 / abc1234> |
| 部署环境 | <本地 dev / 测试 / 生产> |
| 复现率 | <100% / 偶发 ~30% / 仅一次> |

### Initial_Hypothesis（可选）
<填写前的初步猜测。这只是「假设」，不是「根因」。根因写到 design.md>

### Workaround（可选）
<用户当前能用什么临时绕开>
```
