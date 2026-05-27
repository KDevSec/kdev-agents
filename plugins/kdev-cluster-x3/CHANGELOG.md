# CHANGELOG

## v0.1.0 (2026-05-28)

Phase 2 实施完成：

### 新增

- 30 个 agent definitions（1 主控员 + 4 轻组长 + 25 工作 agent）
- 4 个 skill（/kdev:start-feature、/kdev:hud、/kdev:status、kdev-statusline.sh）
- 14 份 standards（4 组组长 system prompt template + 10 评审 checklist + conflict-arbitration）
- 1 个 hook（on-blocked.py — events.log → 派组长）
- Python lib（state_md / events_log / ar_number / handoffs / slug / agent_lint / standards_lint）
- 完整 pytest 套件（46 tests）

### 已知遗留议题（v0.2 待细化）

参考 [X1 vs X3 对比文档 v0.2 §5.7](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md#57-待用户细化议题v02-填)：

1. IR 阶段（R1）是否需要独立评审员
2. D1 实施计划完成是阻断还是告警
3. TDD 增量（D2）的"增量颗粒度"细则
4. 终审聚合员（F2）额外评审标准
5. 评审循环 3 次后 BLOCKED 阈值是否合理
6. 评审员之间冲突（如代码评审员 vs 质量评审员）仲裁默认归属

### 下一步

- Phase 3：在 sop_test0518-x3 worktree 跑「产品管理三层模型」实测，按 [v0.2 §8 实测计划](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md#8-实测计划-worktree--sop_test0518) 收集 9 项对比指标。
