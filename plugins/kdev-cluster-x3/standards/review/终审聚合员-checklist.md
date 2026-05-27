# 终审聚合员 checklist（F1 最终裁决）

> 评审对象：F1 两路评审（CEO视角评审员 + 架构评审员）结论 + events.log gate 历史
> 评审结论：pass / conditional / reject（必须说明理由）

## F1 必检项（8 条 / 1 项 reject 级 = 总体 reject）

1. [ ] **F1 两路 verdict 一致**：CEO视角评审员 和 架构评审员 均已输出 review.md，且 verdict 均为 PASS；若不一致则触发冲突仲裁流程再提交本 checklist。
2. [ ] **R 阶段 gate_pass 完整**：events.log 中 R2 gate 事件存在且最终状态为 pass；若有 FAIL 记录，需有后续「重审通过」记录闭环。
3. [ ] **D 阶段 gate_pass 完整**：所有 AR 的 D2 gate 事件均已记录且状态为 pass；未完成 AR 数量为 0。
4. [ ] **T 阶段 gate_pass 完整**：T1 gate 事件存在且状态为 pass；若有回归测试阶段（T2），T2 gate 同样 pass。
5. [ ] **遗留高风险已处置**：各评审员 review.md 问题清单中标注「高风险」的条目均有关闭说明（修复 / 接受 / 降级），无悬挂。
6. [ ] **仲裁记录完整（如有）**：若本 Feature 触发过冲突仲裁，`.kdev/handoffs/<group>/arbitration-*.md` 存在且有最终裁决结论。
7. [ ] **无阻断问题遗留**：所有评审员 verdict=FAIL 后的修复流程均已走完，无「FAIL 已知但未修复」的开环项。
8. [ ] **产物完整性**：以下文件均存在且非空：`sr.md`、`design.md`、`test-points.md`、`security.md`、两路 F1 review.md。

## 输出格式

写到 `.kdev/handoffs/review/终审聚合员-review.md`：

```markdown
# 终审聚合员 review — F1

verdict: pass | conditional | reject
date: <ISO-ts>

## 汇总检查项
1. ✅ F1 两路 verdict 一致（CEO视角=PASS，架构=PASS）
2. ✅ R/D/T gate_pass 完整
3. ⚠️ 遗留高风险已处置 — AR-PAY-05 安全问题已降级，附审查组长决策记录
...

## 遗留风险列表（conditional / reject 时必填）
- ...

## 最终决策说明
<pass: 所有 gate 完整，两路一致，可上线>
<conditional: 上线前须完成 [具体条件]，否则回退>
<reject: [致命原因]，需返工后重走 F1 流程>
```
