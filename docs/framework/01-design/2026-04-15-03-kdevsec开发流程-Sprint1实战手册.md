---
status: draft-v1
createdAt: '2026-04-15'
target: kdevsec Sprint 1（1→N 验证，对标 token-statistics Sprint 0）
startDate: '2026-04-16'
endDate: '2026-05-07'（4 周估算）
owner: ly
related:
  - docs/01-design/2026-04-15-02-KDev架构设计v3.0.2修订.md
  - ~/.claude/plugins/cache/kdev-agents/kdev-memory/0.1.1/skills/kdev-memory/SKILL.md  # 已从 kdev-engineering-memory 重命名为 kdev-memory，作为 kdev-agents 插件 v0.1.1 发布
  - /home/lyadmin/Projects/token-statistics/.kdev/conventions.md
---

# kdevsec Sprint 1 实战手册（第一稿）

> **本手册的目的**：给智能体和用户一份**可执行的日级操作指引**，从明天（2026-04-16）开始用 skill 组合跑 kdevsec，同时验证 BMAD × Superpowers 交接契约。
>
> **不是**设计文档，是操作手册。遇到与 v3.0.2 冲突处以 v3.0.2 为设计准绳，以本手册为执行路径。

---

## 零、前置盘点（今晚 1-2 小时，明天开跑前必做）

### 0.1 kdevsec 现状

- **形态**：brownfield，基于 RuoYi-Vue3-FastAPI v1.8.1
- **技术栈**：Vue3 / Element Plus / Pinia（前端）+ FastAPI / SQLAlchemy / PostgreSQL / Celery（后端）
- **已有**：`codes/ruoyi-fastapi-backend|frontend|test` 三个子项目 + `docs/00-规范`、`docs/01-需求`、`docs/02-设计` + `specs/001-rdm-cq-project-sync`、`specs/003-sr-kdevsec-001-ar-split`
- **已用过**：speckit（`.specify/`）、superpowers（`.superpowers/`）、但未走完一条完整 KDev 流程

### 0.2 今晚必做（阻塞明天开跑）

**任务 A：初始化 `.kdev/` 记忆骨架**

```
调用：Skill(kdev-memory)   # 注意：原 kdev-engineering-memory 已重命名 + 重打包为 kdev-agents 插件 v0.1.1
传入：project_root=/home/lyadmin/Projects/kdevsec
产出：.kdev/ 目录 + CLAUDE.md 触发规则段（追加到现有 CLAUDE.md 末尾）
```

完成后检查 `/home/lyadmin/Projects/kdevsec/.kdev/` 必须包含：
- `当前状态.md`、`决策日志.md`、`踩坑日志.md`、`执行日志.md`、`方法论铁规.md`、`每日汇总/.gitkeep`

**注意 kdev-memory v0.1.1 新核心原则**（执行手册全程必须遵守）：
- 🔴 **实时落盘**：每完成一步、踩一次坑、做一次决策、接到一次评分，**立刻**写 `.kdev/` 对应文件，禁止"攒到会话末尾"
- 🔴 **每日汇总从 `.kdev/` 聚合，不翻会话**：用户说"写今天总结"时，必须读 `执行/决策/踩坑/改进/当前状态` 五个文件按日期筛条目拼装，**禁止**翻会话上下文回忆
- 🔴 **数据诚信**：实时落盘漏写的步骤，汇总里标 `Step N: 待补（会话中未及时落盘）`，**禁止**编造或回忆补

**任务 B：把 `.kdev/conventions` 继承自 token-statistics**

从 `/home/lyadmin/Projects/token-statistics/.kdev/conventions.md` 复制到 `/home/lyadmin/Projects/kdevsec/.kdev/方法论铁规.md` 作为 **v0 基线**。调整：
- §1 AR 编号规则保留（AR-<特性>.<序号>）
- §2 CSV schema 保留
- §6.3 踩坑即时落盘保留
- §7 端到端垂直切片保留
- §8 验收三件套保留
- §9.4 智能体受众跳评分保留
- §13 E2E 分层保留
- **新增 §14 worktree 对比实验纪律**（本手册 §5 的内容抄进去）

**任务 C：接住已有状态 → 写入 `当前状态.md`**

从 `docs/01-需求` / `specs/` 盘点：
- kdevsec 的愿景（来自现有 CLAUDE.md §项目概述）
- 已有 FR/NFR（如存在则列出编号）
- specs/001、specs/003 的完成度（未完成？部分完成？）
- **选择 Sprint 1 第一个迭代的标的**（推荐：从 specs/003-sr-kdevsec-001-ar-split 切一个最小垂直切片）

写入 `当前状态.md`：
```
## 会话信息
- 项目：kdevsec
- Sprint：1（对标 token-statistics Sprint 0）
- 起始日期：2026-04-16

## 当前位置
- phase: 1
- 当前状态: SPRINT1-INIT
- 下一步: Week 1 Day 1 - /kdev:ir（brownfield 模式：基于已有愿景/FR）
```

**任务 D：把本手册 pin 到 kdevsec**

复制本手册到 `kdevsec/docs/workflow/kdevsec-Sprint1-实战手册.md`，作为 Sprint 1 全程操作指引。

---

## 一、Sprint 1 整体节奏（4 周）

```
Week 1  (2026-04-16 ~ 04-22)  ── P1 规划阶段上半段
         IR + SR + PRD（配件：bmad-create-prd 原子用法）

Week 2  (2026-04-23 ~ 04-29)  ── P1 规划阶段下半段
         Prototype + Review + PLAN
         🔬 第一次 worktree 对比实验（/kdev:plan）

Week 3  (2026-04-30 ~ 05-06)  ── Phase 2 Iter 1 执行
         🔬 第二次 worktree 对比实验（/kdev:ar 的架构设计）
         AR → align → dev（subagent-driven TDD）

Week 4  (2026-05-07 ~ 05-13)  ── Iter 1 收口 + 交接契约提取
         E2E + 验收 + gstack-cso 安全审计
         据两次对比实验数据提取 BMAD × Superpowers 交接契约 v1
```

**Sprint 1 出口条件**（对齐 v3.0.2 §七 + 本手册）：
1. kdevsec 完成 1 个迭代端到端垂直切片（不要求 Sprint 1 做完 MVP）
2. 两次 worktree 对比实验全部完成，数据进执行日志
3. 交接契约 v1 写回 kdev-agent 项目
4. `.kdev/` 记忆骨架全程零违反 conventions
5. 人受众节点顺畅度均值 ≥ 4.0（基线：token-statistics Sprint 0 3.9）

---

## 二、Week 1：P1 规划上半段（IR / SR / PRD）

### Day 1（04-16）：/kdev:ir — 初始需求

**目标**：基于 kdevsec 已有愿景（CLAUDE.md §项目概述）+ RuoYi 底座定义 Sprint 1 的需求边界。**不是从零探索**，是"澄清并结构化已存在的认知"。

**操作**：
```
Skill(superpowers:brainstorming)
prompt 要点：
  - "我是 kdevsec 项目，已有 RuoYi 底座，需要澄清 Sprint 1 第一个迭代的需求边界。
    不要走到 writing-spec 阶段，只做 5-8 轮问答收敛需求。"
  - 把 CLAUDE.md §项目概述 + docs/01-需求 关键片段作为 context 喂进去
产出：docs/01-需求/Sprint1-IR.md（追加而非覆盖已有文件）
记录：
  - .kdev/执行日志.md 追加 Step 1（必填：执行事实 + 模型自评含扣分项）
  - 末尾 STOP，采集用户评分（1-5 + 一句话）
```

**退出条件**：需求边界清楚到能列 10-15 条候选 FR。

---

### Day 2（04-17）：/kdev:sr — 结构化需求 + 粗粒度 AR

**目标**：产出 SR CSV + 粗粒度 AR CSV（按特性分组，粗估工作量）。

**操作选择**：
- **配件 skill 路径**（推荐）：手写 SR CSV + 粗 AR CSV，只从 bmad-create-prd 借 FR/NFR 模板（看 `~/.claude/skills/bmad/create-prd/` 的 FR/NFR step 文件，拷格式不启 12 step）。
- **整块路径**（保留，视需求复杂度）：若 FR 数 > 30 或用户希望走完整 PRD 流程，启 `Skill(bmad-create-prd)`，接受 12 step preamble 约 50k token 代价。

**产出**：
- `docs/01-需求/Sprint1-PRD.md`（BMAD 格式，或手写）
- `docs/01-需求/Sprint1-SR.csv`
- `docs/01-需求/Sprint1-AR粗粒度.csv`

**🔑 决策记录**：选配件还是整块路径，进 `Q-NNN` 并记录理由（token 成本 / 复杂度评估 / 用户偏好）。

---

### Day 3-4（04-18~04-19）：Review + 修订

**操作**：
```
Skill(gstack-plan-ceo-review)  # 轻量产品方向评审
→ 跳过 ceo-review 整块流程，只用"范围挑战 + 10-star 对齐"两项原子能力
→ 产出：docs/02-设计/Sprint1-CEO评审.md
```

**HARD-GATE**：用户批准 SR + PRD + 粗 AR 后才进 Week 2 原型阶段。不批准则回 Day 1-2 修订。

---

### Day 5（04-20）：缓冲 / 收口

- 处理前 4 天遗留的修订
- 每日汇总 Week 1 写入 `每日汇总/2026-04-20.md`（作为 Week 1 收口）
- 更新 `当前状态.md`：下一步 = Week 2 P1-PROTOTYPE

---

## 三、Week 2：P1 规划下半段 + 第一次 worktree 对比实验

### Day 6（04-23）：/kdev:prototype — 高保真原型

**操作**：
```
Skill(frontend-design)  # 底座 skill，整块调用
prompt 要点：
  - "基于 Sprint1-SR 和 PRD，产出 HTML 原型（覆盖全愿景，不受 Sprint 1 迭代范围限制）"
  - 参考 kdevsec 技术栈（Vue3 + Element Plus 风格）
产出：docs/02-设计/ui-prototypes/phase1-overview.html
记录：Step 2 + 用户评分
```

### Day 7（04-24）：/kdev:review — 合并评审

**操作**：
- 复查原型 + SR + AR 对齐
- Q-NNN 确认是否原型覆盖到未来 Growth 功能
- HARD-GATE：用户批准三件套（SR / AR 粗 / 原型）

---

### Day 8-10（04-25~04-27）：🔬 **第一次 worktree 对比实验**（/kdev:plan）

**实验目标**：验证 BMAD epics-and-stories 整块调用 vs 手写 epic 的交接质量差异。

#### 实验纪律（抄自 §5，必须遵守）

- 两 worktree **同一 base commit** 分叉
- 两边**同一份 SR + AR 粗 + 原型** 作为输入
- 执行日志**独立采集**（不互相查看评分）
- 禁止在实验期间把任一 worktree 的产物混入另一边
- 实验结束后在主干汇总指标，不选胜者，**目的是提取交接契约**

#### 具体操作

**Step A：建立 worktree**

```bash
cd /home/lyadmin/Projects/kdevsec
git checkout -b sprint1-iter0
git worktree add ../kdevsec-wt-A -b sprint1-wt-A-bmad
git worktree add ../kdevsec-wt-B -b sprint1-wt-B-manual
```

**Step B：worktree-A 跑 BMAD 整块**

```
cd /home/lyadmin/Projects/kdevsec-wt-A
Skill(bmad-create-epics-and-stories)
  输入：Sprint1-SR + Sprint1-AR粗粒度.csv
  产出：docs/03-开发/Sprint1-epics-and-stories.md（BMAD 格式）
  注意：bmad 可能要 config.yaml（G-002 复发风险）→ 手动 config 绕过
记录：worktree-A 独立执行日志段（命名 Step 3-A）
```

**Step C：worktree-B 跑手写 + gstack 评审**

```
cd /home/lyadmin/Projects/kdevsec-wt-B
手写：docs/03-开发/Sprint1-迭代计划（基线）.md
  参考：token-statistics/docs/03-开发/01-迭代计划（基线）.md 格式
  要求：端到端垂直切片（R-001），每迭代产出用户可见价值
然后：
Skill(gstack-plan-eng-review)
  输入：手写迭代计划
  产出：评审反馈 → 修订后计划
记录：worktree-B 独立执行日志段（命名 Step 3-B）
```

**Step D：指标采集（进主干 `.kdev/` 的对比实验表）**

在 `.kdev/执行日志.md` 新增 `## 对比实验 E1：/kdev:plan`：

| 指标 | worktree-A (BMAD) | worktree-B (手写+gstack) |
|------|-------------------|-------------------------|
| 耗时（会话 wall-clock） | — 分钟 | — 分钟 |
| Token 消耗（输入+输出）| —k | —k |
| 产出 epic/story 数 | — | — |
| 用户评分 | —/5 | —/5 |
| 模型自评（含扣分项）| —/5 | —/5 |
| 下游消化度（预估：writing-plans 能直接消费吗）| —% | —% |
| 返工次数（评审后修订轮数）| — | — |

**Step E：主干合并决策**

- 用户对照 A/B 产出 + 指标，**决策选谁作为主干基线**
- 决策进 Q-NNN（必填理由）
- 落败 worktree 保留 1 周备查，期满删除
- **核心产物**：不是胜者，是"哪些字段 A 比 B 好 / 哪些字段 B 比 A 好"的清单 → 将写入交接契约

---

## 四、Week 3：Phase 2 Iter 1 + 第二次 worktree 对比实验

### Day 11-12（04-30~05-01）：/kdev:ar — 详细 AR + 第二次 worktree 对比

#### 🔬 第二次对比实验：架构设计

**实验目标**：验证 bmad-create-architecture 8 step 整块调用 vs 手写架构 + gstack-plan-eng-review 的交接质量。

**和第一次实验的差异**：这次焦点是**技术设计的深度和 writing-plans 消化度**，不是流程产出粒度。

```bash
# 基于 Week 2 选定的主干 sprint1-iter0 再分叉
cd /home/lyadmin/Projects/kdevsec
git worktree add ../kdevsec-wt-C -b sprint1-iter1-archA-bmad
git worktree add ../kdevsec-wt-D -b sprint1-iter1-archB-manual
```

- **worktree-C**：`Skill(bmad-create-architecture)` 8 step 完整跑（接受 ~40k token preamble）
- **worktree-D**：手写架构（参考 token-statistics iter4 手写成功案例）+ `Skill(gstack-plan-eng-review)`

**指标采集表**（进 `.kdev/执行日志.md` `## 对比实验 E2：/kdev:ar-架构`）：

| 指标 | worktree-C (BMAD-arch) | worktree-D (手写+gstack) |
|------|----------------------|-------------------------|
| 耗时 | — | — |
| Token 消耗 | — | — |
| 架构决策数（ADR 条目）| — | — |
| gstack 评审发现数 | — | — |
| **writing-plans 消化时"回查上游"次数** 🔑 | — | — |
| 下游 subagent 执行失败次数 | — | — |
| 用户评分 | — | — |

**🔑 "回查上游次数"是本次核心指标**——这直接衡量架构产物是否"自包含到能被 Superpowers 独立消费"。

---

### Day 13（05-02）：AR CSV 分解（主干）

合并 worktree-C 或 worktree-D 到主干后：
- 从技术设计 + SR 分解详细 AR CSV（8 列 schema，遵守 conventions §1/§2）
- 落到 `docs/01-需求/迭代1-AR需求列表.csv`
- 记录 Step 4

---

### Day 14（05-03）：/kdev:align（触发条件化）

**判断**：
- 若 Week 2 + Day 11-13 的决策已全部 Q-NNN 化 + 用户全采纳 → **跳过 align**，进 /kdev:dev
- 若仍有未定 UI / 规则 / 验收细节 → 跑 O-S-U-R-A 五步

**记录**：若跳过，在决策日志写 Q-NNN 说明理由（对标 Sprint 0 Q-049）。

---

### Day 15-17（05-04~05-06）：/kdev:dev — TDD 全循环

**操作**：
```
Skill(superpowers:writing-plans)  # 底座整块
  输入：迭代1-AR + 技术设计 + gstack 评审采纳
  产出：docs/03-开发/迭代1-实现计划.md（TDD 步骤）

Skill(superpowers:subagent-driven-development)  # 底座整块
  输入：实现计划
  产出：code + tests + 45+ commits（预估）+ 两轮评审修复
  分 Lane 执行（按独立性拆 worktree 再并行）
```

**期间必做**：
- **gstack-cso 早期介入**：kdevsec 是安全平台，Week 3 中段跑一次 `Skill(gstack-cso)` 对现有代码做安全基线扫描
- 主控遇架构 gap 级 bug → 立即落 G-NNN（R-006）
- 所有 subagent 实现 prompt 显式 `source ~/.nvm/nvm.sh` 避免 Node 版本问题（kdevsec 是 Python 项目，对应约束是 Python venv / requirements-pg.txt）

---

## 五、Week 4：Iter 1 收口 + 交接契约提取

### Day 18（05-07）：/kdev:e2e

```
有前端 UI：Skill(gstack-qa)  # 底座，对 kdevsec UI 跑真实浏览器测试
纯后端 API：手写 pytest + supertest 风格 E2E
记录：Step 5 + 用户评分
```

### Day 19（05-08）：/kdev:accept — 验收三件套（R-002）

**三条互补通路必须全跑**：
1. **verification-before-completion**：`Skill(superpowers:verification-before-completion)`
2. **dogfooding**：部署到本地 docker-compose + 用户真浏览器用一遍
3. **PRD 核对**：FR/NFR 全量对照 AR 实现，缺口进 Growth backlog

**产出**：`docs/05-报告/Sprint1-迭代1-系统验收报告.md`

### Day 20（05-09）：/kdev:security

```
Skill(gstack-cso)  # 底座整块
范围：kdevsec MVP 已实现代码 + 依赖 + 部署配置
产出：安全审计报告 → 进决策日志决定哪些修复入 Sprint 1、哪些推 Growth
```

### Day 21（05-10）：交接契约提取 🔑

**关键任务**：从两次 worktree 对比实验 + 全程执行日志中提取 **BMAD × Superpowers 交接契约 v1**。

**产出位置**：`/home/lyadmin/Projects/kdev-agent/docs/01-design/2026-05-10-01-BMAD-Superpowers交接契约v1.md`

**契约必含**（对照 v3.0.2 §1.6 占位）：
1. **字段级契约**：
   - `bmad-create-epics-and-stories` 输出 Markdown schema（epic / story / AC）→ KDev 迭代计划 CSV 字段映射
   - `bmad-create-architecture` 输出的哪些字段 writing-plans 真的在用、哪些被无视
   - AR CSV 8 列 → writing-plans TDD step 的机械化映射规则
2. **触发条件**：
   - 何时用 BMAD 整块（配件 → 底座升格条件）
   - 何时手写（配件保持 / 跳过）
3. **降级路径**：BMAD skill 失败时的 fallback（G-002 复发时怎么办）

### Day 22（05-11）：每日汇总 + Sprint 1 retro 预备

- 写 Sprint 1 全程汇总（对标 Sprint 0 回顾报告格式）
- 列未闭环 R 候选 + 未定 Q
- 准备下一会话做 `/kdev:recap`（对应 gstack-retro 原子能力）

### Day 23-24（05-12~05-13）：缓冲 + /kdev:recap

```
Skill(gstack-retro)  # 底座整块
范围：Sprint 1 4 周 git 历史 + .kdev/ 全部记录
产出：docs/Sprint1-retro.md
最终产物：修订 v3.0.2 → v3.0.3（按本 sprint 学到的东西）
```

---

## 六、worktree 对比实验纪律（抄进 kdevsec/.kdev/方法论铁规.md §14）

1. **同 base 分叉**：两 worktree 从同一个 commit、同一份上游输入分叉，不允许各自"想到哪改到哪"
2. **独立采集**：执行日志按 `Step N-A` / `Step N-B` 分段；两边**不互相查看评分**直到指标表填完
3. **禁止污染**：实验期间任一 worktree 的产物不得混入另一边
4. **不选胜者**：实验终点不是"A 或 B 哪个好"，是"提取可写入交接契约的字段级观察"
5. **对照指标固定**：耗时 / token / 产出数量 / 下游消化度 / 返工次数 / 用户评分 / 模型自评（含扣分项）
6. **落败分支保留**：至少 1 周可回溯，期满删除
7. **每次实验必 Q-NNN**：实验发起 / 合并决策各一条决策记录

---

## 七、skill 调用速查（按阶段）

| 阶段 | KDev 命令 | skill 调用 | 类型 | 备注 |
|------|----------|-----------|------|------|
| Week 1 D1 | /kdev:ir | `superpowers:brainstorming` | 底座 | 到"边界清楚"退出，不走 writing-spec |
| Week 1 D2 | /kdev:sr | `bmad-create-prd`（配件）或手写 | 配件 | 配件模式只借 FR/NFR 模板 |
| Week 1 D3 | /kdev:review | `gstack-plan-ceo-review` | 配件 | 只借"范围挑战" |
| Week 2 D6 | /kdev:prototype | `frontend-design` | 底座 | 整块 |
| Week 2 D8-10 | /kdev:plan | **对比 A/B** | 实验 | A=bmad-create-epics B=手写+gstack |
| Week 3 D11-12 | /kdev:ar-arch | **对比 C/D** | 实验 | C=bmad-create-architecture D=手写+gstack |
| Week 3 D13 | /kdev:ar-csv | 本地模板 | — | 遵守 conventions §1/§2 |
| Week 3 D14 | /kdev:align | 本地对话 | — | 触发条件化 |
| Week 3 D15-17 | /kdev:dev | `superpowers:writing-plans` + `subagent-driven-development` | 底座+底座 | 整块 |
| Week 3 mid | - | `gstack-cso` | 底座 | 早期基线扫描 |
| Week 4 D18 | /kdev:e2e | `gstack-qa`（有 UI）或 pytest | 底座 | 分层 R-007 |
| Week 4 D19 | /kdev:accept | `superpowers:verification-before-completion` + dogfooding + PRD 核对 | 底座+模板 | 三件套 R-002 |
| Week 4 D20 | /kdev:security | `gstack-cso` | 底座 | 收口 |
| Week 4 D23-24 | /kdev:recap | `gstack-retro` | 底座 | 修订 v3.0.2 |
| 贯穿全程 | - | `kdev-memory`（v0.1.1，原 kdev-engineering-memory）| 自研 | 记忆骨架；实时落盘 + 聚合汇总 |

---

## 八、每日纪律（最低动作清单）

每天结束前必须完成（按 kdev-memory v0.1.1 规则）：

1. ✅ 每步完成后**立即**追加 `执行日志.md` Step N（含模型自评 + 扣分项）— 实时落盘
2. ✅ 用户评分**当场**采集（1-5 + 一句话），禁止延后；过夜补录视为数据失真
3. ✅ 差值 ≥ 2 → **立即**记 R-NNN 候选到 `执行日志.md` 末尾
4. ✅ 踩坑**即时**落 `踩坑日志.md` G-NNN
5. ✅ 决策**立即**落 `决策日志.md` Q-NNN（Q/G 全局递增）
6. ✅ 会话结束前写 `每日汇总/YYYY-MM-DD.md` — **从 `.kdev/` 聚合，禁止翻会话**
7. ✅ 流程状态变更**立即**更新 `当前状态.md`

**检验是否合规的硬指标**：写当日汇总时如果发现需要回头翻会话才能填某 Step → 说明前面违反了规则 1，标 `待补（未及时落盘）` 并复盘下次为何漏写。

---

## 九、失败回退路径

| 信号 | 动作 |
|------|------|
| bmad skill config.yaml 缺失（G-002 复发）| 手工写 config 绕过；记 G-NNN；不改路径 |
| worktree 实验的 A/B 两边都失败 | 退回手写路径，记 G-NNN + Q-NNN 说明原因；取消本次对比实验 |
| /kdev:dev subagent 耗时超预期（> 2 天）| 降级 lane 数量；拆成更细 AR 再跑 |
| 用户评分连续 2 次 ≤ 3 | 暂停当前节点，开专项讨论会话（非本手册工作流）|
| 技术栈不兼容（FastAPI / RuoYi 版本锁）| 记 G-NNN；锁版本；继续 |
| Sprint 1 Week 4 仍未进 /kdev:dev | 收口当前 phase，写中止 retro，重排 Sprint 2 |

---

## 十、本手册与 v3.0.2 的关系

- 本手册 = v3.0.2 的**执行实例**，主要服务 kdevsec Sprint 1
- 发现与 v3.0.2 冲突时：
  - 设计层冲突（如 14 命令定义）→ 以 v3.0.2 为准
  - 操作层冲突（如本手册某步用错 skill）→ 以本手册修订 + 进 R-NNN
- Sprint 1 Week 4 交接契约提取后，会反哺 v3.0.2 成 v3.0.3

---

## 附录 A：文件命名映射（中文记忆 + 英文 ID）

| 已有（token-statistics Sprint 0）| 新项目对等（kdevsec Sprint 1）|
|-------|-------|
| `.kdev/sprint0-journal.md` | `.kdev/执行日志.md` |
| `.kdev/questions-log.md` | `.kdev/决策日志.md` |
| `.kdev/gotchas.md` | `.kdev/踩坑日志.md` |
| `.kdev/state.md` | `.kdev/当前状态.md` |
| `.kdev/conventions.md` | `.kdev/方法论铁规.md` |
| `.kdev/daily-logs/` | `.kdev/每日汇总/` |
| `.kdev/kdev-v3.0.1-改进建议.md` | `.kdev/改进建议.md` |

**Q/G/R 编号在 kdevsec 从 001 起**（不继承 token-statistics 编号）。

## 附录 B：与 kdev-agent 的协作边界

- **kdevsec 项目内产物**：SR / PRD / AR / 实现代码 / 测试 / 验收报告 / `.kdev/` 全部记录
- **需回写到 kdev-agent 的产物**：
  - `docs/01-design/2026-05-10-01-BMAD-Superpowers交接契约v1.md`（Week 4 D21）
  - `docs/01-design/2026-05-13-01-KDev架构设计v3.0.3修订.md`（Week 4 D24，基于 retro）
  - `docs/02-reviews/2026-05-XX-Sprint1回顾报告.md`（对标 Sprint 0 回顾格式）

## 附录 C：今晚前置任务清单（阻塞明天开跑）

- [ ] 任务 A：初始化 `.kdev/` 骨架
- [ ] 任务 B：复制 token-statistics/.kdev/conventions.md → kdevsec/.kdev/方法论铁规.md + 新增 §14
- [ ] 任务 C：盘点已有 docs/ specs/ 写入 当前状态.md
- [ ] 任务 D：复制本手册到 kdevsec/docs/workflow/

全部完成后，明早（2026-04-16）直接从 §二 Day 1 开跑。
