# 产物合并规则

通过最后一个评审闸门（Gate 3）后，把中间产物合并/复制到 `docs/design-flow/<slug>/` 作为最终交付物。

## 合并映射

| 来源（中间产物） | 目标（最终交付物） | 合并方式 |
|------------------|--------------------|----------|
| `.kdev/design-flow/<slug>/stage-1-sr/iter-{{last_pass}}.md` + `.kdev/design-flow/<slug>/stage-2-ar/iter-{{last_pass}}.md` | `docs/design-flow/<slug>/01-requirements.md` | 拼接：先 SR 再 AR，加 `# 第一部分：SR 级需求` / `# 第二部分：AR 级用户故事` 二级分节 |
| `.kdev/design-flow/<slug>/stage-3-prototype/iter-{{last_pass}}/` | `docs/design-flow/<slug>/02-prototype/` | 整目录递归复制（保留 frontend-design 输出的子结构） |
| `.kdev/design-flow/<slug>/stage-4-plan/iter-{{last_pass}}.md` | `docs/design-flow/<slug>/03-design.md` | 直接复制（spec-kit:plan 已经产出了完整概要+详细设计） |

## 合并步骤

1. 从 `flow-state.json` 读取每个 stage 最后一次 PASS 的 `iter` 值（在 `history[]` 里查最大的 `iter` 且 `verdict=PASS`）
2. 创建目标目录：`mkdir -p docs/design-flow/<slug>/02-prototype`
3. 按上表执行复制 / 拼接
4. 生成 `docs/design-flow/<slug>/README.md`（索引页），内容：

```markdown
# {{feature_name}}

**Slug:** {{slug}}
**生成时间:** {{date}}
**生成方式:** kdev-design-flow v0.1（手动 review 模式：{{review_mode}}）

## 交付物

- [01-requirements.md](01-requirements.md) — SR 需求文档 + AR 用户故事
- [02-prototype/](02-prototype/) — 高保真原型（HTML）
- [03-design.md](03-design.md) — 概要设计 + 详细设计

## 流程记录

中间产物（迭代历史 + 评审记录）保留在 `.kdev/design-flow/{{slug}}/`，未提交 git。
```

5. 在 `flow-state.json` 设 `status = "completed"` + 写 `completed_at` 字段。

## 不做合并的情况

- `flow-state.json` 中 `status != "in_progress"`：流程已结束（aborted 或 completed），不重复合并
- 任一 stage 没有 PASS 记录：报错"Stage N has no PASS in history; aborting merge"

## 幂等性

合并步骤可重复运行（例如用户想刷新最终产物）：
- 目标目录如果存在，先用 `git status -- docs/design-flow/<slug>/` 检查是否有未提交改动，有则提示用户先处理
- 无未提交改动 → 直接覆盖
