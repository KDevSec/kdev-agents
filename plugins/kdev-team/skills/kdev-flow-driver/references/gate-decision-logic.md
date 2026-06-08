# Gate 判定逻辑

编排器到 gate 节点时，需要判断 verdict。本文件定义每个 gate 的具体判据。

适用于 `dev-engineer`（开发工程师）员工的 coding-flow。其他员工会有自己的 gate 判定逻辑。

## Gate 总览

| Gate | 节点 | Kind | Reviewer | 阶段1 处理 |
|---|---|---|---|---|
| g-relevance | n1-relevance | decision | self | 自判 |
| g-plan-review | n4-plan-review | review | reviewer-expert | **deferred**（记 PASS --by deferred:阶段3-评审专家） |
| g-complexity | n5-complexity | decision | self | 自判 |
| g-verify | n8-verify | review | self | 自判 |
| g-code-review | n9a-code-review | review | reviewer-expert | **deferred** |
| g-e2e | n9b-e2e | acceptance | self | 自判 |
| g-sec-review | n10-sec | review | reviewer-expert | **deferred** |
| g-deploy | n12-deploy | acceptance | self | 自判 |

## Self-Review Gate 判据

### g-relevance（关联度，decision → high/low）

判断任务与当前代码库的关联程度，决定是否需要 worktree 隔离。

- **high**：任务与主分支代码有共享 schema / 共享目录 / 共享鉴权 / 直接在主分支上改就行
- **low**：任务独立性强、可能影响主分支稳定性、需要 worktree 隔离

典型判法：读考题/需求 → 看是否涉及"在已有项目里改"（high）vs "独立新功能/实验性任务"（low）。多数视觉改造 = high（直接在主分支改样式）。

### g-complexity（复杂度，decision → simple/complex）

判断任务复杂度，决定主控直接实现还是派 subagent。

- **simple**：单文件改动、< 5 个文件涉及、无需 TDD、主控 1-2 轮能做完
- **complex**：多文件/多页面改动、涉及全局主题/组件系统、需要 TDD 循环、需要多轮 increment

典型判法：读 PLAN.md 的 task 数 → ≤ 3 个 atomic task 且单模块 → simple；> 3 个 task 或跨模块 → complex。视觉改造几乎都是 complex（T0-T3 四个大任务）。

### g-verify（完成验证，review → PASS/FAIL）

判断当前 increment 的实现是否完成。验证清单：

1. `npm run build` 通过（零错误）
2. Lint 通过（零 error，warning 可接受）
3. UED 硬约束 grep 检查：
   - 无裸 hex/rgb 颜色（`grep -rn '#[0-9a-fA-F]\{3,8\}' src/` 除 CSS 变量文件外）
   - 无"登陆"错别字（`grep -rn '登陆' src/`）
4. 关键页面可访问（手动打开或截图确认不破版）

- **PASS**：以上全部通过
- **FAIL**：任一项不通过，回流到 n6b 修

注意：这是"完成验证"不是"质量评审"。只要功能做完了 + 基本约束满足就 PASS，不需要做到完美。

### g-e2e（Per-Increment E2E，acceptance → PASS/FAIL）

判断当前 increment 的端到端质量是否达标。需要先派 dev-engineer-e2e agent 做检查：

1. 视觉 diff：1366px + 1920px 截图 vs 原型图
2. 功能冒烟：登录页能打开 → 输入账号密码 → 点登录 → 进首页
3. UED §10 自检清单逐项勾选（CHECKLIST.md）

- **PASS**：视觉还原可接受 + 核心功能可用 + CHECKLIST 无硬伤
- **FAIL**：视觉偏差大 / 功能不可用 / CHECKLIST 有硬伤，回流到 n6b 修

### g-deploy（部署+金丝雀验收，acceptance → PASS/FAIL）

判断部署是否成功 + 金丝雀冒烟是否通过。需要先派 dev-engineer-deploy agent 部署，然后 e2e 做金丝雀检查：

1. 合并分支成功
2. 部署环境可达
3. 金丝雀冒烟：登录 → 首页 → 核心功能走一遍
4. 交付物齐全（PLAN.md / CHANGES.md / CHECKLIST.md / TEST-REPORT.md / RUN.md / screenshots/ / ued6-restyle.patch）

- **PASS**：部署成功 + 金丝雀通过 + 交付物齐全
- **FAIL**：部署失败 / 金丝雀不通过 / 交付物缺失，回流到 n6b

注意：如果是纯视觉改造无后端环境，金丝雀可能 env-blocked（无 MySQL → 无法起 FastAPI）。这时视觉部分能做到"npm run build 通过 + 截图还原"即可，功能冒烟标为 partial。视情况判 PASS（接受限制）或 FAIL（要求必须全功能）。

## Reviewer-Expert Gate（阶段1 全 deferred）

以下 gate 标记为 `reviewer: reviewer-expert`，阶段1 没有真人第三方评审，统一处理：

| Gate | 阶段1 处理 |
|---|---|
| g-plan-review | `record-gate --gate g-plan-review --kind review --verdict PASS --by "deferred:阶段3-评审专家"` |
| g-code-review | `record-gate --gate g-code-review --kind review --verdict PASS --by "deferred:阶段3-评审专家"` |
| g-sec-review | `record-gate --gate g-sec-review --kind review --verdict PASS --by "deferred:阶段3-评审专家"` |

不需要判断，不需要问用户，直接记 PASS + deferred 标注。不冒充第三方。

## Decision Gate 的 verdict 对应节点

方便编排器调 record-gate 时确认 to_node 是否合理：

| Gate | verdict | → 节点 |
|---|---|---|
| g-relevance | high | n3-plan |
| g-relevance | low | n2-worktree |
| g-complexity | simple | n6a-impl-inline |
| g-complexity | complex | n6b-impl-subagent |

## 回流规则

- g-verify FAIL → n6b-impl-subagent（重做实现）
- g-e2e FAIL → n6b-impl-subagent（重做实现）
- g-deploy FAIL → n6b-impl-subagent（重做实现）
- g-plan-review FAIL → n3-plan（重写计划，但阶段1 deferred 不会 FAIL）

回流最多 2 次（总共 3 次尝试），第 3 次引擎自动 escalate 为 blocked。