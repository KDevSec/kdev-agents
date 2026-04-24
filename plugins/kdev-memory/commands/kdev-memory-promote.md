---
description: 列出 .kdev/memory/ 里待沉淀（promote_status: pending）的条目，推荐去向，用户确认后写入 docs/ 产物通道
argument-hint: [无参数 | --all]
---

# /kdev-memory-promote

列出当前项目 `.kdev/memory/` 里所有"待沉淀"条目（改进建议 / R-NNN / G-NNN / Q-NNN），给出推荐沉淀去向，用户确认后把内容写入 `docs/` 并更新源条目的 `promote_status: done`。

## 候选扫描（Bash 聚合）

!`bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/promote-list.sh" "$ARGUMENTS"`

## 你的任务

根据上面 bash 脚本的输出：

1. **列出所有 pending 条目** —— 编号 + 标题 + 来源文件 + 建议去向（按下表）
2. **向用户询问**："这些条目哪些要沉淀？（全选 / 指定编号 / 全跳过）"
3. 对用户确认要沉淀的每条：
   - 读源条目原文
   - 写入 `promote_target` 指向的 `docs/` 文件（追加 或 按 section 合并）
   - 更新源条目 frontmatter：`promote_status: done` + `promote_target: <path>` + `promote_date: YYYY-MM-DD`
4. 对用户确认要跳过的：
   - 更新源条目 frontmatter：`promote_status: skipped`，`promote_target` 存理由
5. **全部处理完后**执行：

```bash
touch .kdev/memory/.last-promote
```

重置"上次沉淀时间"。

## 推荐沉淀去向

| 源条目类型 | 推荐 docs/ 去向 |
|---|---|
| 改进建议.md 定稿条目 | `docs/05-报告/实战总结-<项目名>.md` 反思章节 |
| conventions.md §11 R-NNN | `docs/08-开发规范.md` 或 skill-level CLAUDE.md |
| 踩坑日志.md G-NNN 高频类 | `docs/04-架构/踩坑索引.md` |
| 决策日志.md Q-NNN 架构级 | `docs/04-架构/ADR-NNN-<slug>.md` |
| 执行日志.md Step 4.5+ 高分经验 | `docs/05-报告/实战项目总结.md` |
| 日常 G-NNN / Step 现场 | **不沉淀**（留在本地过程即可） |

**严禁替用户拍板** —— 若用户拒绝某条，尊重并标 `skipped`；不要硬推。

## 参数

- 无参数：列出全部 pending
- `--all`：同上（保留给未来扩展批量模式）
