# fields-tasks

OpenSpec 模式 — `openspec/changes/<bug-id>/tasks.md` 的 bugfix T1–T12 任务清单模板。

**先跑 `openspec instructions tasks --change <bug-id>`** 拿 upstream prompt，再用下面模板覆盖。

## 完整模板

```markdown
## Tasks

### Phase 1: RED
- [x] T1. 写回归测试 `tests/test_<module>_<bug>.py::test_<bug-id>`，实测失败（输出贴在 T1 备注里）

### Phase 2: GREEN
- [ ] T2. 修复 `<file1>` 第 N 行：<具体改动>
- [ ] T3. 修复 `<file2>` 第 M 行（如有第二处）：<具体改动>

### Phase 3: 验证闸门
- [ ] T4. 跑 T1 回归测试 → PASS
- [ ] T5. 跑既有单元/集成测试 `pytest`（或 `npm test` / 按栈）→ 全量 PASS
- [ ] T6. type-check `mypy` / `tsc` / `cargo check` / `go vet`（按栈）→ PASS
- [ ] T7. lint `ruff` / `eslint` / `golangci-lint`（按栈）→ PASS
- [ ] T8. （如安全相关）`kdev-secure-coding:python-security-coding` 8 类清单 → PASS / N/A
- [ ] T9. （如涉及业务关键入口）E2E 真走完整流程 → PASS / N/A

### Phase 4: 收尾
- [ ] T10. `openspec validate <bug-id>` → PASS
- [ ] T11. kdev-commit `fix: <Symptom> (#<bug-id>)`
- [ ] T12. （可选）`openspec archive <bug-id>`

## Notes

- T1 完成时机：步骤 4.4 写完回归测试且实测红
- T11 commit message 必须含 Root_Cause 一句压缩 + Regression test 测试名
- T12 archive 是否执行依项目习惯（参 KDevSec 既有 archive 风格决策）
```

## 字段约束

- **任务编号**：T1–T12 固定不变。不要重排（如把 T10 改到 T9 后）——编号是跨 bug 检索 key
- **`[ ]` / `[x]`** 状态实时维护：每完成一项立即更新（不要等到全做完再批量改）
- **备注**（如"输出贴在 T1 备注里"）：可在 task 下追加 `\n  - ` 缩进列表写过程信息，但不要写完整 stack trace（太长污染 tasks.md）

## 与评审闸门的关系

- T1–T9 全绿才能进步骤 6 评审闸门（review-modes.md）
- T10 `openspec validate` 失败 → 回 [fields-proposal.md](fields-proposal.md) / [fields-design.md](fields-design.md) 补字段
- T11 commit message 模板见 SKILL.md 步骤 7

## 与 P0 hotfix 快路径的关系

P0 模式下：
- T1 仍必填（minimal repro test 即可，broader 等价类 T11 前补）
- T2–T9 仍必跑（不能跳）
- T6 评审强制升级到 multi（即便用户没传 `--review-mode=multi`）
- T10–T12 同标准流程
