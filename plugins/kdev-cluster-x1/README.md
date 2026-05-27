# kdev-cluster-x1

> KDev 多智能体集群 **X1 群组原版方案**（严格层级 / 组长当路由 PgM）的实施 plugin。

## 状态

| 项 | 值 |
|---|---|
| 当前阶段 | **Phase 1 骨架**（v0.0.1）|
| 设计依据 | [X1 vs X3 对比文档 v0.2](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md) §2 |
| Worktree | `feature/cluster-x1` 分支独立开发，与 X3 互不冲突 |
| 下一步 | Phase 2 用 `superpowers:writing-plans` 写实施计划 → 用 `skill-creator` 实施 |

## 架构（X1 严格层级）

```
              主控员
                │
   ┌────┬──────┴──────┬────┐
   ▼    ▼              ▼    ▼
 需求  开发           测试  审查
 组长  组长           组长  组长
   │    │              │    │
 5员  6员            4员  10员
```

**通信硬规**：用户↔主控员；主控员↔4 组长；组长↔本组组员；跨组必经"组长→主控员→另一组长"三跳。

## 目录结构

```
kdev-cluster-x1/
├── .claude-plugin/plugin.json
├── README.md
├── agents/         # 1 主控员 + 4 组长 + 25 工作 agent（共 30 个 agent definition）
├── skills/         # /kdev:start-feature, /kdev:hud, /kdev:status, kdev-statusline.sh
├── standards/      # 评审 checklist + system prompt 模板（X1 可选）
└── hooks/          # X1 无特殊 hook（路由由组长 prompt 控制）
```

## Agent 清单（待 Phase 2 填充）

### 主控层
- 主控员

### 需求组
- 需求组长（路由）+ 需求澄清师 + 需求规格师 + 需求拆解师 + 原型设计师 + 方案设计师

### 开发组
- 开发组长（路由）+ 环境对齐员 + 实施计划师 + TDD 实现员 + E2E 验收员 + 安全扫描员 + 部署上线员

### 测试组
- 测试组长（路由）+ 测试点设计师 + 测试用例渲染员 + UI 自动化工程师 + API 自动化工程师

### 审查组（评审标准统一 + 路由）
- 审查组长 + SR 评审员 + 原型评审员 + 方案设计评审员 + 代码评审员 + 质量评审员 + 安全评审员 + 测试设计评审员 + CEO 视角评审员 + 架构评审员 + 终审聚合员

## 实测目标

跑 [sop_test0518](https://github.com/KDevSec/sop_test0518) 的"产品管理三层模型（产品线/项目/版本）"功能，对比 X3 plugin 在同一需求上的表现。详见对比文档 §8 实测计划。
