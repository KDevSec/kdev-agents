# Changelog · kdev-core

本插件遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [0.2.0] - 2026-06-11

### 重大变更（P-Core-FF：R1 存储层 feature-first 重构）

- **存储布局翻转**：`.kdev/flows/<flow>/<slug>/` → `.kdev/features/<slug>/`（功能当顶层）。
- **flow-state.json schema 重构**：新增 `stories[]`（用户故事，HUD 完成度分母）、`runs[]`（台账，跑完棒次摘要不可变）、`active{}`（当前单棒控制态：flow/run/current_node/status/gate_iters/config…）、`origin`/`relates_to`（slug 回链，v0.1）。两级 status（feature 级 + run 级）。布尔 stale-guard `active` 废弃，续跑由 `active{}` 生命周期推导。
- **events.jsonl 事实流水**：原内嵌 `history`/`phase_history` 挪到同目录 `events.jsonl`（append-only，行内带 actor + slug/flow/run）。新增 `kdev_core.events` 读写 API。
- **run 生命周期**：`complete_run`（折叠 active→runs[]+清空）、`start_run`（补活开新 run）、`close_feature`（显式收口 feature 级）。
- **stories API**：`add_story` / `set_story_status`。
- **handoffs/<员工>/ 目录约定**（最小：路径生成，协议留 P-B）。
- **迁移脚本**：`python -m kdev_core migrate`（幂等 + 同 slug 跨 flow 合并 + history→events）。
- **CLI**：保留 `<flow> <slug>` 兼容签名；新增 `start-run`/`add-story`/`set-story-status`/`close-feature`/`list-features`/`events`/`handoff-path`/`migrate`。
- **不变**：R2(`node_machine`)/R3(`gate`) 纯函数零改动——R1 做扁平内存/嵌套磁盘翻译适配层。

### 关联

Q-012（feature-first 存储重设计）/ Q-013（P-Core-FF 提前）。下游 P-A 需求架构师 + kdev-hud 共同前置。
