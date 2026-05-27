# SR评审员 checklist（R2 阻断 / R3 抽查）

> 评审对象：`.kdev/handoffs/reqs/sr.md`
> 评审结论：PASS / FAIL（FAIL 必须列具体问题）

## R2 必检项（8 条 / 1 项 FAIL = 总体 FAIL）

1. [ ] **FRs 完整**：所有用户故事都有对应功能需求条目，每条带「角色 / 触发 / 行为 / 期望」四要素。
2. [ ] **NFRs 完整**：至少覆盖性能 / 安全 / 可用性 / 可维护性 4 类，每条可量化（数字或对比基线）。
3. [ ] **假设明确**：列出至少 3 条假设条件，标注「待用户确认」or「已确认」。
4. [ ] **范围明确**：In Scope / Out of Scope 各列至少 3 条。
5. [ ] **上下文充分**：跟现有系统 / 依赖系统的关系明确。
6. [ ] **验收线索可执行**：至少 5 条验收标准，每条可写成测试用例。
7. [ ] **回溯 IR**：SR 每个 section 都能回溯到 IR 的对应段。
8. [ ] **无 TBD / TODO / FIXME** 占位。

## R3 抽查项（AR 拆解后回看）

- [ ] AR.csv 中每条 AR 都能回溯到 SR 的某个 FR 或 NFR。
- [ ] AR 数量合理（≥ FR 数 × 1.5 倍 — 太少则颗粒度过粗）。

## 输出格式

写到 `.kdev/handoffs/reqs/SR评审员-review.md`：

```markdown
# SR评审员 review — R2

verdict: PASS | FAIL
date: <ISO-ts>

## 检查项结果
1. ✅ FRs 完整
2. ❌ NFRs 完整 — 缺失「性能」与「可维护性」类，建议补 §3.2 章节
...

## 问题清单（FAIL 必填）
- ...
```
