# fields-specs

OpenSpec 模式 — `openspec/changes/<bug-id>/specs/<capability>/spec.md` 的 bugfix spec delta 模板。

**仅当** [fields-design.md](fields-design.md) 的 Spec_Impact `Change_Type ≠ none` 才写本文件。

**先跑 `openspec instructions specs --change <bug-id>`** 拿 upstream prompt，再按下面模板做 delta。

## 完整模板

```markdown
## Capability：<capability-name>

### 修订点 1
**原文**（来自 `openspec/specs/<capability>/spec.md`）：
> <引用原文>

**改为**：
> <修订后文字>

**理由**：<为什么改，引用 design.md Root_Cause 段对应位置>

### 修订点 2（如有）
**原文**：
> <引用原文>

**改为**：
> <修订后文字>

**理由**：<...>
```

## 关键约束

⚠️ 这是 change 提案级别的 spec delta，**不是**直接改 `openspec/specs/` 下的真实 spec 文件。

`openspec archive <bug-id>` 之后才会把 delta 真的 apply 到主 spec。在 archive 前：

- 主 spec（`openspec/specs/<capability>/spec.md`）**保持原样**
- delta 留在 `openspec/changes/<bug-id>/specs/<capability>/spec.md`，由 reviewer 在评审阶段看是否接受
- 评审 REJECT → 删 delta + 同时回退本次 bugfix 的代码改动（spec 不接受意味着根因诊断错了，治本方向得换）

## 何时不应该写 specs delta

如果 design.md 的 Spec_Impact 段填的是：
- `Change_Type: none` — bug 不在 spec 层，只是代码 bug → **不写本文件**
- `Affected_Spec: None` — spec 没问题 → **不写本文件**

最常见情况是不写：bug 是实现 bug，spec 描述本身是对的。命中 Spec_Impact 反而少见，命中时大概率说明 root cause 走深了一层。
