# OMC 架构借鉴点 — kdev-core 编排底座（参考资料）

| 项 | 值 |
|---|---|
| 文档性质 | **参考资料 / 调研依据**（从整体架构正文剥离至此，正文只写最终架构，不写借鉴来源）|
| 日期 | 2026-06-05 |
| 范围 | OMC（oh-my-claudecode）作为**架构参考**对 kdev-core 编排底座的借鉴点；**不引入 TS 源码** |
| 关联 | [整体架构](../01-design/2026-05-28-02-KDev-staff-整体架构-v0.1.md) · [底座设计总纲 v1.0](../01-design/2026-06-05-01-kdev-core底座设计总纲-v1.0.md) · [kdev-memory vs OMC 源码层对比](./2026-05-30-06-kdev-memory-vs-OMC源码层对比.md) |
| 源码位置 | `_repos/oh-my-claudecode/src/`（gitignore，不提交）|

---

## 0. 定位

底座路线 = **从现有 flows 抽 R1–R7 公共编排层，照 OMC 范本但不 fork TS 源码**。OMC 是 3.3MB TS 编译运行时，与 KDev Python/markdown 哲学冲突——故只**借设计范本**（mode / Team Pipeline / Notepad），不引入源码；L3 自主 / 跨 IDE 真要完整多 agent 运行时再重评采用 OMC（不 foreclose）。

底座设计总纲 §7 已沉淀实施级的「Top 8 好经验 + 2 避坑」。本文档保留架构概念级的借鉴对照，作为调研档案。

---

## 1. OMC Notepad 3 层生命周期 → kdev-core 借鉴方向

| OMC | KDev 借鉴 |
|---|---|
| Notepad priority（永久）| flow-state / 评审 standards |
| Notepad working（7 天自动清理）| events.log / checkpoints/（按 ttl 清理）|
| Notepad manual（永不过期）| review-memory.md / handoffs/ |

---

## 2. OMC 6 类 JSON 状态 → 状态模型借鉴

OMC 拆 6 个 JSON（session / tasks / quality / agents / notepad / project-memory）。KDev 收敛为 **per-flow `flow-state.json` + events.log + CEO 聚合视图**（避免文件碎片化 + markdown 用户可读）。OMC 的「6 类信息分类」思路被状态 section 结构继承（当前阶段 / 员工状态 / warnings）。

---

## 3. OMC Team Pipeline 状态机 → 编排引擎借鉴

OMC 的 `plan → spec → exec → verify → fix` 状态机思路在 kdev 中演化为：

- 员工编排节点链：`IR → 需求方向 → SR → AR → 原型 → 方案 → ...`
- 评审循环 + CEO 升级 = OMC「fix 循环」加强版（加百分制 + 双重通过条件 + 用户拍板兜底）
- advance 三段式（邻接表 + 守卫解耦 + 不可变变更）借 OMC `transitions.ts`
- 三类 gate（review / decision / acceptance）+ request_id 锁 + escalate 不 force-accept

---

## 4. ECC 借鉴（语言规范 / AgentShield）

ECC 的语言规范库已由 `kdev-secure-coding` plugin 在做（python-security-coding 等），不在 kdev-core 范围。AgentShield 远期可考虑独立 plugin。

---

## 5. 借鉴边界

| | 借 | 不借 |
|---|---|---|
| 范本 | mode / Team Pipeline / Notepad 生命周期 / 6 类信息分类 / transitions 守卫分离 | TS 源码 fork |
| 运行时 | 无 | OMC 3.3MB TS 运行时 / tmux / SQLite / provider 三路由 / installer / lockfile spin-wait |
