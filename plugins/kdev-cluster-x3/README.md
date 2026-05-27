# kdev-cluster-x3

> KDev 多智能体集群 **X3 矩阵式方案**（轻组长 / 组长当顾问 PM）的实施 plugin。

## 状态

| 项 | 值 |
|---|---|
| 当前阶段 | **Phase 1 骨架**（v0.0.1）|
| 设计依据 | [X1 vs X3 对比文档 v0.2](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md) §3 |
| Worktree | `feature/cluster-x3` 分支独立开发，与 X1 互不冲突 |
| 下一步 | Phase 2 用 `superpowers:writing-plans` 写实施计划 → 用 `skill-creator` 实施 |

## 架构（X3 矩阵式 / 轻组长）

```
                主控员
                  │
       ┌──────┬───┴───┬──────┐
       ▼      ▼       ▼      ▼
    需求    开发    测试   审查
    组长    组长    组长   组长       ← 不路由（PM 顾问）
       │      │       │      │
       └━━ 后台监听 events.log ━━┘
                                      （阶段聚合 / blocked 介入）
   主控员直接派工作 agent（快路径）
   ┌─────────────────────────────┐
   │需求5员│开发6员│测试4员│评审10员│   ← 工作 agent 可直接派评审员（评审池共享）
   └─────────────────────────────┘
```

**通信规则**：
- 用户↔主控员
- 主控员直接派工作 agent（快路径，2 跳）
- 主控员调组长（慢路径：阶段聚合 + 异常）
- 工作 agent 直接派评审员（不经组长）
- BLOCKED → events.log 写事件 → hook 自动派组长介入

## 组长的 4 meta 职责（不做路由）

1. **监督**：后台监听 events.log
2. **标准**：维护本组 system prompt 模板和评审标准（落在 `standards/`）
3. **聚合**：阶段完成时出本组总结报告
4. **应急**：组员 BLOCKED 时通过 hook 自动介入

## 目录结构

```
kdev-cluster-x3/
├── .claude-plugin/plugin.json
├── README.md
├── agents/         # 1 主控员 + 4 组长 + 25 工作 agent（共 30 个 agent definition）
├── skills/         # /kdev:start-feature, /kdev:hud, /kdev:status, kdev-statusline.sh
├── standards/      # ★ 必需：评审 checklist + system prompt 模板（组长 meta 资产）
└── hooks/          # ★ on-blocked.sh：监听 events.log 自动派组长（X3 特有）
```

## Agent 清单（待 Phase 2 填充）

### 主控层
- 主控员（懂快/慢路径双判断）

### 需求组
- 需求组长（顾问/聚合）+ 需求澄清师 + 需求规格师 + 需求拆解师 + 原型设计师 + 方案设计师

### 开发组
- 开发组长（顾问/聚合）+ 环境对齐员 + 实施计划师 + TDD 实现员 + E2E 验收员 + 安全扫描员 + 部署上线员

### 测试组
- 测试组长（顾问/聚合）+ 测试点设计师 + 测试用例渲染员 + UI 自动化工程师 + API 自动化工程师

### 审查组（评审标准统一 + 终审聚合）
- 审查组长 + SR 评审员 + 原型评审员 + 方案设计评审员 + 代码评审员 + 质量评审员 + 安全评审员 + 测试设计评审员 + CEO 视角评审员 + 架构评审员 + 终审聚合员

## 评审节点接入（13 个评审节点）

详见对比文档 §5 评审节点接入清单：
- **需求阶段**：R2 SR / R3 AR / R4 原型 / R5 方案设计
- **开发阶段**：D1 计划 / D2 TDD 增量（代码+质量并行）/ D4 安全 / D5 部署前
- **测试阶段**：T1 测试点设计 / T2 用例渲染
- **最终阶段**：F1 CEO+架构（并行）/ F2 终审聚合

8 阻断 / 3 告警 / 2 抽查。

## 实测目标

跑 [sop_test0518](https://github.com/KDevSec/sop_test0518) 的"产品管理三层模型（产品线/项目/版本）"功能，对比 X1 plugin 在同一需求上的表现。详见对比文档 §8 实测计划。
