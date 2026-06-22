---
title: kdev 数字员工集群 — 单插件化 + 去第三方 + 一键 bootstrap 安装
date: 2026-06-18
status: 草案（待用户评审）
author: ly（设计对齐：opus 主控）
related:
  - 决策 Q-008（结构进底座 / 执行=agent 驱动）
  - roadmap-v1.0 §1.5.5 / §1.5.8（装机债 FF-2 / Q-018 / -v1 命名 / D6 激活滞后）
  - 2026-06-14 四插件整体架构接缝评审（合并消灭的 seam 清单）
  - OMC 范本：docs/framework/04-references/_repos/oh-my-claudecode/
model: opus（架构判断）
---

# 0. 重大决策更新（2026-06-18 追加）：独立新仓库 + idev 通用改名

**决策**：不在 kdev-agents 内就地改造，而是**新建独立仓库**承载数字员工集群，**前缀 `kdev` → `idev`**（通用产品名，去公司定制感）；**kdev-agents 原仓库及其 17 个插件保持不动**（冻结为 origin / legacy）。

**为什么更好**：① **零迁移风险**——不碰正在用的 `.kdev` dogfooding 与 memory 76 hook，kdev-agents 照常运行；② **clean-room 抽取**——idev 仓是一次干净的「port + rename + 单插件化 + 去第三方」一趟做完，不被旧多插件历史拖累；③ **productization 边界**——idev = 通用数字员工产品，kdev-agents 留作 KDevSec 内部工具 / 公司专属内容。

**对下文各节的 delta（下文一律按此 lens 读）**：
- 本设计从「在 kdev-agents 就地单插件化」改为「**把所需插件 port 进新 idev 仓库 + 改名 `idev:*` + 单插件化 + 去第三方，一趟做完**」。
- §3 边界划分**不变**（折进 / 独立照旧），只是落点从 kdev-agents → idev 新仓；命名空间 `kdev:*`→`idev:*`、python 包 `kdev_*`→`idev_*`、命令 `/kdev-*`→`/idev-*`。
- §4 去第三方矩阵不变（kdev-spec→**idev-spec**、kdev-qa→**idev-qa**、kdev-frontend-design 同）。
- §5 打包：插件根 `idev/`（在新仓）；结构同。§6 bootstrap：`npx idev` + idev 仓的 marketplace。
- §8 迁移：**风险从「保护 dogfooding」转为「port 保真」**——kdev-agents 冻结不动，新仓全新构建；memory/code-graph/secure-coding 被**复制**进 idev（renamed），kdev 原件冻结留存（两份但不并行演进，可接受）。

**Secondary 决策（2026-06-18 已拍）**：
- **D-R1 仓库名 + 前缀（✅ 已定 2026-06-18）**：前缀 `ieidev`，单插件 = `ieidev-team`，仓库 `KDevSec/ieidev-team`（KDevSec 组织新建）。ieidev 全网 100% free（npm 裸名 + GitHub handle + 仓库全可用）。**§0 全文中的 `idev` 一律指 `ieidev`（最终名）**；落地映射：namespace `ieidev-team:*`、python 包 `ieidev_*`、命令 `/ieidev-*`、记忆目录 `.ieidev/`、bootstrap CLI `npx ieidev-team`。
- **D-R2 记忆目录**：✅ 新仓 dogfood 用 `.idev/memory/`（跟着改名，命名一致）。
- **D-R3 公司专属内容**：✅ MVP **先把 secure-coding（含 KDevSec 规则）原样 port 进 idev**；「通用安全编码能力槽 + 公司规则外置注入」作**后续 productization 重构**，不进 MVP。

---

# 概要

把 kdev 当前的 **17 插件集群**重整为「**一个自包含的数字员工集群插件 `kdev`** + **5 个完全解耦的独立插件**」，并去掉员工对所有第三方 skill 的依赖（自研 / fork / 改接线替换），最后以 **OMC 式一条 bootstrap CLI 命令**收口安装体验。**（命名 / 落点按 §0：实际产物在 idev 新仓、用 idev 前缀。）**

目标三条，互相牵制，本设计是它们的解：

1. **去第三方自包含**：员工引用的 `spec-kit:*` / `frontend-design:*` / `gstack:*` / `webapp-testing` 全部用 kdev 自有资产替换，集群对外部 skill 零依赖。
2. **单插件化（集群侧）**：员工干活所需的引擎 + 记忆底座 + 能力 skill 收进一个 `kdev` 插件，安装即完整、一次性还清跨插件接缝债。
3. **一键安装**：借鉴 OMC，一条 `npx kdev` bootstrap CLI 编排「装官方 CC + 加 marketplace + 装插件 + setup」，**不重打包 Anthropic 的 CC 包**。

同时保住一条硬约束：**多人仍能各自独立开发 / 发布不同 skill**（见 §7）。

---

# 1. 背景与驱动

- kdev 现状：17 个独立插件、~24 skill、28 agent、~10 命令、81 hook 脚本（其中 kdev-memory 独占 76）、3 个 `python -m` 调起的 python 包（kdev_core / kdev_team / kdev_hud），外加 kdev-code-graph 的 kdev_ingestor。
- **接缝债**：2026-06-14 接缝评审查出的漂移（events 双账 / handoff schema / scope 半迁移 / 激活错位）多数是「插件之间的契约漂移」；**收成单插件会一次性消灭其中大半**。
- **装机债**：FF-2（PYTHONPATH 靠 `find ~` 脆）、Q-018（依赖未声明）、marketplace `-v1` 命名错位、D6（激活滞后无兜底）——单插件化后大半作废。
- **与 OMC 的两处不同**：① kdev 是多插件集群（OMC 单插件）；② kdev 是 Python（OMC 是 TS 编译进 dist），有 `python -m` 可移植性问题，OMC 没有。

# 2. 设计总览

| 维度 | 决策 |
|---|---|
| 集群粒度 | **一个自包含 `kdev` 集群插件**（引擎 + 记忆底座 + 能力 skill + 新建/fork 替换），**对外部 skill 与独立插件零运行时依赖** |
| 独立插件 | design-flow / coding-flow（方法论标准件，与集群完全解耦）+ commit / bugfix / explorer（横切工具），各自独立开发与发布 |
| 去第三方 | spec-kit→自研 kdev-spec；frontend-design→fork kdev-frontend-design；gstack-qa→自研 kdev-qa；plan-eng-review→现有 reviewer-design 覆盖；webapp-testing→现有资产改接线 |
| 安装形态 | Layer1 `npx kdev` bootstrap CLI（编排官方安装）+ Layer2 `/kdev-setup` 残余接线；瘦 installer，能力交给 plugin manifest 原生提供 |

> **「零依赖」的准确含义**：集群对**第三方 skill** 与**独立插件**零运行时依赖（去第三方目标达成）。仍保留两条**基础设施依赖**——`understand-anything`（marketplace 级，code-graph 带入）+ `playwright MCP`（运行时，kdev-qa/ui 测试用），二者由 `/kdev-setup` + 依赖级联兜底（§6.2），非本设计要消除的对象。

# 3. 集群边界（核心决策）

## 3.1 划界原则（按落定的讨论结论）

一个插件**折进集群**，当且仅当满足任一：
- 是员工干活的**底座**（编排底座 kdev-core / 记忆底座 kdev-memory）——缺了员工跑不完整；
- 是员工**运行时引用的能力 skill**（test/secure/code-graph 等）；
- 是为替换第三方而**新建/fork**的能力（kdev-spec / kdev-qa / kdev-frontend-design）。

一个插件**保持独立**，当且仅当：
- 它脱离集群仍**独立有用**（commit / bugfix / explorer），或
- 它的**编排职能已被员工吸收**、集群只需其少量静态资产（design-flow / coding-flow，见 §3.4）。

## 3.2 折进集群 `kdev`

| 类别 | 内容 |
|---|---|
| 引擎 | kdev-core（编排底座，`python -m kdev_core`）、kdev-team（员工 28 agent + node-table + staff.yml + kdev-flow-driver skill）、kdev-hud（观测，运行时 on/off） |
| 记忆底座 | **kdev-memory**（2 skill + kdev-step-recorder agent + 2 命令 + **76 hook**）——与 kdev-core 并列的员工地基，随集群常驻 |
| 能力 skill | secure-coding、test-points、test-cases、ui-autotest、api-autotest、uicase-to-apicase、env-recon、**code-graph**（含 kdev_ingestor py 包 + understand-anything 外部依赖 + install 脚本） |
| 新建 | **kdev-spec**（替 spec-kit specify+plan）、**kdev-qa**（替 gstack-qa，跑在 playwright MCP） |
| fork | **kdev-frontend-design**（fork frontend-design，Apache 2.0） |
| 搬入资产 | req-architect 实际消费的 5 个设计模板（共 246 行 md，来自原 design-flow references/，见 §5） |

> memory 折进的依据：`.kdev/memory/staff/<role>/` 的 per-员工 scope 本就是员工的记忆数据模型；memory 是「记忆底座」，与「编排底座」kdev-core 同源。代价（76 hook 随集群常驻、装集群即激活整套记忆制度）已被接受。

## 3.3 独立 · 与集群完全解耦

| 插件 | 角色 | 与集群关系 |
|---|---|---|
| design-flow | 需求设计方法论标准件（人手动线性跑） | **零引用**（见 §3.4） |
| coding-flow | 编码方法论标准件 | **零引用**（dev-engineer 已是其编排化身） |
| commit | AI commit 身份（5 hook） | 无关 |
| bugfix | 8 步修复流 + 禅道 | 无关 |
| explorer | 通用探索 subagent 派发 | 无关 |

## 3.4 为什么方法论 flow 独立**且解耦**（关键澄清）

design-flow / coding-flow 的本质是「**把多个 skill 串起来的编排器**」。但这个「串」的职能**现在已经是需求架构师 / 开发工程师的编排能力**（node-table + kdev-flow-driver + kdev-core 引擎）。实测 req-architect 对 design-flow 的引用拆成两类：

- **(A) 编排/SOP 蓝本类 9 处**（"复刻 design-flow 3 闸门""读 design-flow node-table"）——**纯历史说明，零运行时依赖**；req-architect 的 node-table 已把 SOP 实体化。
- **(B) 真内容依赖**——仅 **5 个模板文件、共 246 行 md**（stage1-sr-prompt 33 / stage1-sr-template 37 / stage3-prototype-prompt 55 / review-gate-prompt 72 / output-merge-rules 49）。

**结论：为 246 行模板去依赖整个 design-flow 插件不成立。** 处置：
1. 把这 5 个模板**搬进集群**，作为 req-architect 自有 reference 资产；
2. **删除** (A) 类 9 处蓝本引用（可保留为注释，但非依赖）；
3. specify/plan 替换（kdev-spec）放**集群**，不放 design-flow；
4. → **集群对 design-flow / coding-flow 依赖归零**，二者纯独立标准件存在。

> design-flow 解耦 + spec-kit 被移除后已近 legacy（被 req-architect 取代）。其保留 / 瘦身 / 弃用是**集群外的单独决定**，不阻塞本设计。

# 4. 去第三方：skill 替换矩阵

| 第三方 skill | 调用方·用途 | 替换策略 | 产物 / 复用 |
|---|---|---|---|
| `spec-kit:specify` | req-architect-decompose · SR→用户故事 | 🆕 自研 | **kdev-spec**（specify 能力，方法论沿用搬入的 SR 模板） |
| `spec-kit:plan` | req-architect-design · AR+原型→设计 | 🆕 自研 | **kdev-spec**（plan 能力，可与 specify 同一 skill 双模式） |
| `frontend-design:frontend-design` | req-architect-prototype · 高保真原型 | 🍴 fork 改名 | **kdev-frontend-design**（Apache 2.0，保留版权 + NOTICE 注明改动） |
| `gstack:gstack-qa` | dev-engineer-e2e · 系统化 QA/冒烟 | 🆕 自研 | **kdev-qa**，跑在 playwright MCP（受控运行时） |
| `gstack:plan-eng-review` | dev-engineer-plan · 计划评审自检 | ♻️ 免建 | 已有 **reviewer-design 的 g-plan-review gate** 做正式 plan 评审；自检并入或省 |
| `webapp-testing` | test-engineer-ui · 运行时 DOM 取选择器 | ♻️ 改接线 | 已被 **kdev-ui-autotest + kdev-env-recon + playwright MCP** 覆盖，改 agent 接线 |

**真正从零自研**仅 2 个：kdev-spec、kdev-qa；**fork** 1 个：kdev-frontend-design；其余靠现有资产改接线。

**基础设施依赖（非第三方 skill，明示保留）**：kdev-qa / test-engineer-ui 依赖 **playwright MCP** 运行时——这是我们选择它替代 gstack daemon 的原因（标准、受控）。由 `/kdev-setup` 确保（§6.2）。

# 5. 打包形态（集群单插件结构）

```
plugins/kdev/                      # 集群插件根
  .claude-plugin/plugin.json       # 单一 version；keywords: digital-employee,cluster
  agents/                          # 28 员工 agent + kdev-step-recorder（memory）
  skills/                          # secure-coding/test-*/ui/api/uicase/env-recon/code-graph
                                   #  + kdev-spec + kdev-qa + kdev-frontend-design
                                   #  + kdev-memory 的 skill + kdev-flow-driver
  commands/                        # /kdev-* 合并 + 新增 /kdev-setup
  hooks/hooks.json                 # = kdev-memory 的 76 hook（唯一带 hook 的折进件）
  references/req-architect/        # 搬入的 5 个设计模板（246 行）
  pykdev/                          # 4 个 python 包统一根
    kdev_core/  kdev_team/  kdev_hud/  kdev_ingestor/
  install.sh / install.ps1         # code-graph 装机脚本归一（venv/ingestor）
```

要点：
- **hooks 合并简单**：折进集群的插件里**只有 kdev-memory 带 hook**（commit 的 5 hook 随 commit 独立）。故集群 `hooks.json` ≈ memory 原样 + `${CLAUDE_PLUGIN_ROOT}` 路径改写，无多源 hook 冲突。
- **4 个 python 包统一根 `pykdev/`**：消解 FF-2（不再 `find ~` 猜路径）；`python -m kdev_core` 等以集群根为 PYTHONPATH（由 `/kdev-setup` 落定，§6.2）。
- **命名空间统一 `kdev:*`**：所有 agent / node-table / dispatch-table 里的 `kdev-xxx:` 跨插件引用一次性改写为 `kdev:*`（与去第三方的重写同批进行）。
- **version 单一**：集群一个 version；memory 的高频迭代今后随集群版本走（取舍见 §7）。

# 6. 一键安装：bootstrap CLI 策略（借鉴 OMC）

## 6.1 两层模型

**Layer 1 — `npx kdev` bootstrap CLI**（薄编排，不重打包 CC）：
1. 探测 CC 是否已装；缺则**调官方渠道**装（`npm i -g @anthropic-ai/claude-code` 或官方 installer）——**绝不分发/重打包 Anthropic 的包**（license/商标 + 版本追逐，得不偿失）；
2. `/plugin marketplace add KDevSec/kdev-agents`；
3. `/plugin install kdev`（集群，自包含、无需为自身级联）；可选 `+ commit/bugfix/explorer/design-flow/coding-flow`；
4. 触发 `/kdev-setup` 做残余接线。

**Layer 2 — `/kdev-setup` 命令（集群内）**：做「plugin manifest 天生干不了」的残余（仿 OMC 萎缩型 installer）。

## 6.2 残余清单（瘦 installer，能力交给 manifest）

| 残余 | 为什么 manifest 干不了 | 处置 |
|---|---|---|
| statusLine（kdev-hud） | CC 插件 **不能自动注册 statusLine**（plugin.json settings 只认 agent/subagentStatusLine） | 写 `settings.json`；CC 不持续重拉 statusLine → 用缓存包装器 + `refreshInterval`（仿 OMC hud-cache-wrapper） |
| Python 可移植性 | `python -m kdev_core` 需包可 import | 落定 PYTHONPATH 指向 `pykdev/`；ingestor venv 由 install 脚本建 |
| playwright MCP | kdev-qa/ui 测试需浏览器运行时 | 探测/引导启用 playwright MCP（OMC 式 MCP 同步） |
| understand-anything | code-graph 外部依赖 | 集群 plugin.json 声明 `dependencies` + `allowCrossMarketplaceDependenciesOn`，靠级联；setup 兜底手动指引 |
| 版本追踪 / reconcile | 升级冲突保留 | 记录已装版本；reconcile 时保留用户改动 |

agents / skills / hooks / commands **全部交给 plugin manifest 原生提供**，installer 不碰。

## 6.3 与 OMC 的关键差异

OMC 是 TS 编译进 dist + 自带 node，无 `python -m` 问题；kdev 是 Python，**Layer2 必须解决 Python 可移植性**（统一 `pykdev/` 根 + setup 落 PYTHONPATH）是 kdev 特有、OMC 没有的残余。

# 7. 多人协作模型（硬约束的解）

**关键：开发协作 ≠ 分发打包，两轴解耦。**

- **集群虽是单插件，但 skill 目录隔离**：`skills/kdev-test-points/` vs `skills/kdev-qa/`，两人改不同 skill = 改不相交文件，git 自动合并、零冲突。
- **集群侧协作摩擦只在发版**：单一 version + 合并 hooks.json/plugin.json 偶发冲突 + 发版爆炸半径（任一 skill 改动 → 整包 bump + 全员 reload，G-004）。用 **CODEOWNERS 按目录划归属** + 约定化 bump 缓解。
- **独立插件保留完整独立开发/发布**：design-flow/coding-flow/commit/bugfix/explorer 各自 version、各自节奏。需要独立发布的能力优先留独立或拆出。

# 8. 迁移节奏与风险

- **分阶段、可回滚**：不一次性大爆破；每阶段独立可验、可回退。建议序：① 去第三方重写（kdev-spec/kdev-qa/fork + 接线，旧插件不动）→ ② 集群物理合并（搬 skill/agent/hook/py 包，命名空间改写）→ ③ bootstrap CLI + `/kdev-setup`。
- **保护 dogfooding `.kdev`**：迁移动用户正在用的工程记忆，须保 `.kdev/memory/` 数据不破；hooks 路径改写后先在隔离 worktree 验证再切。
- **旧插件名兼容期**：过渡期保留旧 marketplace 条目别名 / 重定向，避免下游 `/plugin install kdev-xxx` 断裂。
- **evals 兜底**：各能力 skill 的 evals + 员工 flow evals 在合并前后各跑一遍，证行为不破。

# 9. 影响的 canonical 文档（R-009 回写清单）

本 spec 收尾时须回写或加重定向锚：
- `.claude-plugin/marketplace.json`（15 条目 → 集群 1 + 独立 5；`-v1` 命名修正）
- roadmap-v1.0 §1.5.5/§1.5.8（FF-2/Q-018/-v1/D6 装机债作废，加「已被本 spec 解决」锚）
- kdev-team staff.yml 的 `flow_skill: kdev-coding-flow/design-flow`（解耦后语义变化）
- 各员工 agent 的 `kdev-xxx:` / 第三方 skill 引用（重写为 `kdev:*` / 自研件）
- CLAUDE.md 接口段（若插件名/命名空间变化影响记忆制度接口）

# 10. 范围外 / 未决

- **design-flow / coding-flow 的 legacy 命运**（保留/瘦身/弃用）——集群不依赖、不关心，单独决定。
- **kdev-spec 的 specify/plan 是一个 skill 双模式还是两个 skill**——实施计划阶段定。
- **bootstrap CLI 的发布渠道**（npm 包名 / GitHub release）——实施计划阶段定。
- **集群 version 与 memory 高频迭代的取舍**（是否给 memory 留独立快速通道）——观察后定。
