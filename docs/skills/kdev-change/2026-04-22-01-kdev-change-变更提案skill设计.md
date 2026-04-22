# KDev Change：变更提案 skill 设计规划

**状态**：规划中（未实现）
**起源**：2026-04-22 在 token-statistics 项目中发现 PRD/SR 漂移现象后，讨论借鉴 OpenSpec 思路为 KDev-Agent 体系新增两个 skill 的方案
**适用**：本 doc 是设计规划，不是已落地 skill；实现前需按 §6 未决策项对齐后再进 `superpowers:writing-skills`

---

## 1. 背景：为什么要这个 skill

### 1.1 实战触发案例

token-statistics 项目（KDev-Agent 的 Sprint 1 实战载体）跑完 8 轮迭代后，在迭代 9 规划阶段发现：

- `docs/01-需求/01-SR需求列表.csv` 只有 3 行，停留在 MVP 范围（迭代 1-3）
- 迭代 4-8 交付了 9 条新能力域（成员详情 / 安全加固 / 部署运维 / 会话时长 / 多工具支持 / 灵码集成 / collector 升级 / 原始数据架构 / ...）**全部没有回写到 SR CSV**
- PRD、特性清单、验收矩阵等需求层文档同样停留在 MVP 态
- 后果：要回答"系统现在有多少个特性"这种 audit 问题，必须手工扫描 8 份 `迭代N-AR需求列表.csv`——这是典型的 PRD/SR 漂移

### 1.2 漂移的结构性原因

KDev-Agent 现行执行链路：

```
新需求 → superpowers:brainstorm → 技术设计方案.md
      → superpowers:writing-plans → 迭代N-实现计划.md + 迭代N-AR需求列表.csv
      → E4-E5-E6 实现
      → E7-ACCEPT 验收
      → [漂移发生的位置：没人负责把能力回写到 SR/PRD/特性清单]
```

每个迭代的产出都是**局部一致**（AR 覆盖实现、实现通过 E2E），但**全局一致性**（SR CSV 和特性清单仍是 MVP 真相）靠"智能体自觉"维护。靠自觉就是不靠谱。

### 1.3 目标

通过两个新 skill，把"全局一致性"变成**流程纪律**而非自觉：

- **前置纪律**：新需求必须先产出 CHANGE 提案，声明"我要改哪些 SR / 新增哪些能力域"，才能进 brainstorm
- **后置纪律**：迭代 E7-ACCEPT 通过后，必须按 CHANGE 提案回写 SR CSV / 特性清单 / PRD 增补，否则 E7 不算完

---

## 2. 灵感来源：OpenSpec

OpenSpec（github.com/Fission-AI/OpenSpec）是一个"spec-driven development with AI"工具，核心工作流：`openspec change` 创建变更提案 → review → `openspec apply` 合并到 specs。

### 2.1 值得借鉴（4 个核心思想）

| 思路 | KDev 适配 |
|---|---|
| **变更提案先行，实现后置** | 新需求先写 CHANGE-NNN.md 声明影响面，再进 brainstorm/spec/plan |
| **Delta 思维** | CHANGE 只描述"这次改什么"，不重画整个 spec；主 PRD 保持冻结 |
| **显式生命周期** | `proposed → approved → implementing → applied` 状态机，E7 前必须 apply |
| **一 change 一文件** | 单独可 review、可 grep、可回滚、可索引；不和其他 change 纠缠 |

### 2.2 不借鉴（2 个因地制宜）

| 元素 | 不采用理由 |
|---|---|
| OpenSpec 的 `specs/` + `changes/` 目录结构 | KDev 已有 `docs/01-需求/` 体系（IR / SR / PRD / AR 四级），强行并列会分裂 |
| 独立 CLI 工具链（`openspec init/change/apply`）| KDev 的执行体是"智能体 + skill"，skill 就是 CLI；引入独立 CLI 是多余层 |

---

## 3. 适配 KDev-Agent 项目的典型流程

### 3.1 当前链路（漂移发生点 ⚠️）

```
新需求
  ↓
superpowers:brainstorm
  ↓
docs/02-设计/迭代N-技术设计方案.md
  ↓
superpowers:writing-plans
  ↓
docs/03-开发/迭代N-实现计划.md + docs/01-需求/迭代N-AR需求列表.csv
  ↓
E4-E6 实现
  ↓
E7-ACCEPT ⚠️ SR CSV / 特性清单 / PRD 增补 无人同步 → 漂移
```

### 3.2 改造后链路（新增 2 个触点 🆕）

```
新需求
  ↓
🆕 kdev-change-propose            ← 前置触点：产出 CHANGE-NNN.md
  ↓
superpowers:brainstorm
  （brainstorm 阶段读 CHANGE-NNN 作为输入之一）
  ↓
docs/02-设计/迭代N-技术设计方案.md
  ↓
superpowers:writing-plans
  ↓
docs/03-开发/迭代N-实现计划.md + docs/01-需求/迭代N-AR需求列表.csv
  ↓
E4-E6 实现
  ↓
E7-ACCEPT
  ↓
🆕 kdev-change-apply              ← 后置触点：按 CHANGE 影响声明回写 SR/清单/PRD
  （生成 diff → 用户审核 → commit）
```

### 3.3 典型节奏示例（token-statistics 迭代 9）

```
Day 0:   kdev-change-propose → 产出 CHANGE-009-multi-tenant-auth.md
         状态：proposed

Day 0:   brainstorm（带 CHANGE-009 context）→ 技术设计方案 v1
         CHANGE 状态：approved（spec 经用户审定后）

Day 1-8: writing-plans / 实现 / 测试
         CHANGE 状态：implementing

Day 9:   E7-ACCEPT 通过
         kdev-change-apply → 生成 SR/清单/PRD diff → 用户 y/n → commit
         CHANGE 状态：applied（填 applied 日期 + SR commit hash）
```

---

## 4. 为什么是**两个** skill 而不是一个

| 维度 | 前置（propose） | 后置（apply） |
|---|---|---|
| 触发时机 | 新需求刚到，进 brainstorm 之前 | E7-ACCEPT 验收通过之后 |
| 时间间隔 | 同一天 | 迭代周期后（通常 5-15 天）|
| 输入 | 用户口述 + 现 SR CSV / 特性清单 | CHANGE 提案 + 迭代全部产物 |
| 输出 | 单页 CHANGE-NNN.md | SR CSV diff + 清单 diff + PRD 增补 diff + commit |
| 失败恢复 | 提案重写即可 | 需要判断"实现是否偏离提案"，可能回头改 CHANGE 或 scope |

合一的 skill 会要求调用者先选"你这次是 propose 还是 apply？"——增加认知负担，且两种模式的内部流程差异很大，没有代码复用红利。

---

## 5. skill 形态提案

### 5.1 `kdev-change-propose`（前置）

**描述**：新需求到来时，生成一份 CHANGE-NNN.md 影响分析提案，声明对 SR / 特性清单 / PRD / FR 的影响面。作为 brainstorm 的前置输入。

**触发词示例**：
- "我有一个新需求想提案"
- "起一个 CHANGE"
- "propose 一个变更"
- "新特性：XXX"

**工作流**：
1. 扫描当前 SR CSV / 特性清单 / PRD / 迭代计划基线，建立上下文
2. 和用户对话澄清：
   - 动机（为什么现在做 / 不做的代价）
   - 预期影响面（新增哪些 SR / 修改哪些 / 废弃哪些）
   - 特性清单影响（新增能力域 or 扩展已有 or 跨域）
   - FR 影响（大特性才追加）
   - 向后兼容性（API / DB / 配置）
   - 粗粒度验收边界 3-5 条
   - scope 外明确不做
3. 产出 `.kdev/changes/CHANGE-NNN-<slug>.md`（或 `docs/01-需求/变更提案/`，见 §6.1）
4. 建议下一步：`superpowers:brainstorming` 带此文件作为上下文

**CHANGE 编号规则**：全局递增 3 位数字（CHANGE-001, CHANGE-002...），不按迭代重置。支持跨迭代提案。

### 5.2 `kdev-change-apply`（后置）

**描述**：迭代 E7 验收通过后，按 CHANGE-NNN 的影响声明对比实际产出，生成 SR CSV / 特性清单 / PRD 增补的 diff，审核后 commit。

**触发词示例**：
- "E7 通过了，apply CHANGE-NNN"
- "迭代 N 收尾"
- "CHANGE-NNN 落闭环"

**工作流**：
1. 读 CHANGE-NNN 的"影响声明"章节
2. 读迭代 N 的 AR CSV / 实现计划 / 实际 commit 历史
3. 对比：
   - AR 是否覆盖 CHANGE 声明的 SR 变更？（反之，有没有 AR 属于 scope creep 但 CHANGE 里没声明？）
   - 实际交付形态是否和提案一致？
4. 生成 diff 补丁：
   - SR CSV 追加 / 修改行
   - 特性清单追加条目（能力域粒度）
   - PRD 增补追加章节（若有新能力域）
5. 展示给用户 → y/n/局部修改
6. 确认后应用 diff → `git add` 目标文件 → commit（ly-AI 身份）→ 更新 CHANGE-NNN 状态为 `applied`（填 applied 日期 + SR commit hash）

**特殊情况**：
- **实现偏离提案**：如果发现 AR/代码做了 CHANGE 里没声明的事，停下来问用户是"CHANGE 遗漏要补"还是"scope creep 应该回头改 CHANGE"
- **多次 apply 幂等性**：同一 CHANGE 多次 apply 要幂等——第二次只产出空 diff
- **跨迭代 CHANGE**：一个 CHANGE 可能分多次 apply（每迭代 E7 后 apply 一部分）

---

## 6. 未决策项（skill 实现前需对齐）

### 6.1 CHANGE 文件存放位置

| 选项 | 优点 | 缺点 |
|---|---|---|
| A. `.kdev/changes/CHANGE-NNN-<slug>.md` | 不污染 docs，和 `.kdev/memory/` 同族 | 藏在隐藏目录，外人不易发现 |
| B. `docs/01-需求/变更提案/CHANGE-NNN-<slug>.md` | 融入需求文档体系，可索引 | 增加 `docs/01-需求/` 子目录层级 |

**倾向**：A（`.kdev/changes/`）。理由：CHANGE 是过程档案（类似执行日志），不是交付物；和 `.kdev/memory/` / `.kdev/conventions.md` 并排更一致。

### 6.2 提案和迭代的绑定关系

| 选项 | 说明 |
|---|---|
| A. **1 迭代 = 1 CHANGE** 严格对应 | 简单，但限制大（小修订也要 CHANGE，重特性只能挤一个迭代）|
| B. **1 迭代 = N CHANGE** 允许多对一 | 小修订可共用迭代，灵活 |
| C. **CHANGE 可跨迭代** | 大特性可拆多轮；一个 CHANGE 横跨 iter 9 + iter 10（如 token-statistics 的垂直切片场景）|

**倾向**：C（最灵活）。理由：刚讨论的"垂直切片"天然就是跨迭代场景（CHANGE-009 多租户登录 = iter 9 交付 core + iter 10 交付 Web UI）。

### 6.3 apply 的自动化程度

| 选项 | 说明 |
|---|---|
| A. 全自动（生成 diff → 自动 commit）| 最快，但少一层审核 |
| B. 半自动（生成 diff → 用户 y/n → commit）| 和现在对话风格匹配 |
| C. 手动（只打印"需要改 X Y Z"，用户自己改）| 最弱，沦为提示工具 |

**倾向**：B（半自动）。理由：匹配用户"先审再落"的工作风格；diff 视角清楚，不突兀。

### 6.4 历史回填

问题：本次 token-statistics 的 SR-04~SR-13 已经由 subagent 回填（commit `cb979f8`），但**没有对应的 CHANGE-001~008 提案档案**。要不要补？

| 选项 | 说明 |
|---|---|
| A. 补齐 CHANGE-001~008 追溯档案 | 完整性好，但成本高（要读 iter 1-8 所有 spec/AR 逆向写） |
| B. 不补，迭代 9 起新流程，CHANGE-009 是第一份 | 接受"历史不完整"，降低成本 |

**倾向**：B。理由：过往迭代的 spec/AR 已经完整保留了"做了什么"的信息，CHANGE 的主要价值是"提案时声明的影响面"——这个在 iter 1-8 根本没有，追溯是虚构；未来起步于 CHANGE-009 更有意义。

---

## 7. CHANGE-NNN.md 模板（规范）

```markdown
# CHANGE-NNN: <title>

**状态**：proposed | approved | implementing | applied | abandoned
**创建**：YYYY-MM-DD
**绑定迭代**：迭代 N（或"迭代 N-M"跨迭代，或"未分配"）
**应用**：—（applied 时填日期 + SR / 清单 / PRD 增补的 commit hash）

## 动机

（2-3 段。为什么现在做、不做的代价、触发时机、相关已有 G-NNN 踩坑或 Q-NNN 决策）

## 影响声明

### 新增 SR
- SR-XX <描述>

### 修改 SR
- SR-YY <如何改；为什么改>

### 废弃 SR
- SR-ZZ <原因；是否保留历史行>

### 特性清单影响
- 能力域 N（<名字>）：新增 "xxx" / 扩展已有 "yyy" / 废弃 "zzz"

### FR 影响（可选，大特性才填）
- 新增 FR-NN: <描述>

### 向后兼容性
- **DB schema**：<影响点 + 迁移预案>
- **API**：<端点变化 / 弃用计划>
- **配置 / env**：<新增 / 废弃>
- **部署**：<运维链路影响>

## 粗粒度方案

（1 段。详细 spec 见 docs/02-设计/迭代N-技术设计方案.md）

## 验收边界（初始）

- [ ] <条件 1>
- [ ] <条件 2>
- [ ] <条件 3>

（实际 E2E 验收项见 docs/03-开发/迭代N-实现计划.md 中的验收标准段）

## 不做（scope 外）

- <项 1：不做的理由>
- <项 2>

## 引用

- Spec: [docs/02-设计/迭代N-技术设计方案.md]
- 计划: docs/03-开发/迭代N-实现计划.md
- AR: docs/01-需求/迭代N-AR需求列表.csv
- 关联 CHANGE（依赖 / 冲突）: CHANGE-XXX（如有）
- Brainstorm 起点: YYYY-MM-DD 会话
```

**关键字段约束**：

- `影响声明` 的"新增 SR / 修改 SR / 废弃 SR"三段是 `kdev-change-apply` 的**执行合同**——apply 时严格按此清单生成 diff
- 如果 apply 时发现实现偏离合同（有 AR 做了但 CHANGE 没声明 / CHANGE 声明了但 AR 没覆盖），apply 会卡住并提问
- `向后兼容性` 段是客户沟通材料源（宣告弃用 / 迁移通知都从这里来）

---

## 8. 实施路径建议

在 skill 正式开发前，建议顺序：

1. **对齐 §6 四个未决策项**（用户和设计者 1 小时对话）
2. **在 token-statistics 手工跑一次试点**：
   - 手写 `CHANGE-009-multi-tenant-auth.md` 到 `.kdev/changes/`（迭代 9 已在 spec 阶段，可事后补）
   - 作为 apply 的测试对象
3. **进 `superpowers:writing-skills`** 写 `kdev-change-propose`（相对简单，对话 + 生成单文件）
4. **试跑 propose**：让它为"迭代 10 super_admin Web UI"生成 CHANGE-010，人工审核效果
5. **进 `superpowers:writing-skills`** 写 `kdev-change-apply`（更复杂，涉及 diff 生成 + 幂等 + 偏离检测）
6. **试跑 apply**：等迭代 9 E7 通过后，对 CHANGE-009 跑一次 apply，人工审核 diff 质量
7. **打磨 + 写 conventions.md R-010 / R-011 规则**：
   - R-010：每新需求必须先 propose CHANGE
   - R-011：每迭代 E7 通过后必须 apply 对应 CHANGE（或显式声明无影响）
8. **在 KDev-Agent 官方 README / playbook 里加入 CHANGE 流程章节**

---

## 9. 开放问题 / 未来工作

- **审计模式**：要不要再加一个 `kdev-change-audit`，扫描 SR CSV vs 所有迭代 AR，自动找漂移？还是作为 apply 的副作用？
- **多人协作**：如果项目多人开发，多个 CHANGE 并行提案会不会冲突？（token-statistics 是 1 人所以不紧急，但 KDev-Agent 官方体系要考虑）
- **CHANGE 链**：两个 CHANGE 之间有依赖（CHANGE-010 依赖 CHANGE-009 先 apply）怎么声明？加 "依赖 CHANGE-NNN" 字段？
- **撤销场景**：CHANGE-NNN 状态 applied 后，如果发现实现有问题要回滚，CHANGE 状态怎么处理？加 reverted 状态？
- **和 `.kdev/memory/决策日志.md`（Q-NNN）、`踩坑日志.md`（G-NNN）的关系**：CHANGE 是"面向未来的声明"，Q/G 是"面向过去的记录"。CHANGE 内部引用 Q-NNN / G-NNN 是否强制？
- **CHANGE 可视化**：未来能否生成一个"所有 CHANGE 及状态"的看板，类似 GitHub Projects？（先不做，YAGNI）
- **KDev-Agent 官方 skill 化路径**：这两个 skill 如果在 KDev-Agent 体系里成功，是否走官方 plugin 化？

---

## 10. 参考

- OpenSpec：github.com/Fission-AI/OpenSpec（Apache-2.0）
- token-statistics 漂移案例：
  - 原 SR CSV：commit `4e7c7cf` 之前，3 行 MVP
  - 回填结果：commit `cb979f8`（SR-04~SR-13）+ `829b986`（特性清单 + PRD 增补）
  - 触发 brainstorm：2026-04-22 迭代 9 规划对话
- KDev-Agent 现有 skill 生态参考：
  - `superpowers:brainstorming`（前置触点参考）
  - `superpowers:writing-plans`（后置写 plan 参考）
  - `kdev-memory`（记忆系统，并列触达）
  - `kdev-commit`（commit 身份规范，apply 阶段要遵循）

---

**下次回来继续开发时的入口**：
1. 读本文档全文
2. 按 §6 对齐 4 个决策（如果还没定）
3. 按 §8 实施路径第 2 步开始试点
