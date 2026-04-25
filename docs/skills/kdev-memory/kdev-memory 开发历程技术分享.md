# kdev-memory 开发历程技术分享

> 一个工程记忆及打分skill插件从 0.1.0 到 0.6.0 的演进故事。
>
> 日期：2026-04-20
> 仓库：[KDevSec/kdev-agents](https://github.com/KDevSec/kdev-agents)
> 插件：[plugins/kdev-memory/](../../../plugins/kdev-memory/)

---

## 1. 真实起源：从 token-statistics 实战验证项目

kdev-memory **不是凭空设计出来的**。它是在开发另一个项目——token 用量统计工具——的过程中，作为"顺手做的打分和记录工具"起步的。

### 1.1 当时真正的任务

那时候的主目标是：

- **实战验证 多agent/skill标准开发流程SOP 可行性**： 手动编排 BMAD / Gstack / Superpowers 三个插件，走完一个完整项目（IR → SR → AR → PLAN → TDD → E2E → Deploy 全流程）
- **两件具体的任务**：
  1. **流程顺畅度打分**——流程节点每步结束都让用户打分，采集"哪个 skill 好用、哪步流程流畅、哪个效果不好"的原始数据
  2. **为多agent/skill标准开发流程SOP踩坑**——看真实跑起来有哪些问题

记忆制度本来不是目的——它只是为了**完成这两件任务**而搭出来的脚手架。


### 1.2 两个任务的真实踩坑

所有节点的分数分布并不平均，存在**两个 3 分低点**——它们各自把一类痛点曝光出来：

**低分故事 1：迭代 4 Step 2，LLM 跳过 brainstorm 节点（3/5）**

迭代 4 要进入 brainstorm 节点，LLM 一看"需求范围已经定了"就想直接上设计。**是用户硬把它拉回来**，才进行了讨论。问题是**选项本身是用户主导出来的，不是 LLM 主动提的**。

这条信号后来变成 kdev-agent 的一条改进建议："**LLM 有跳过提议权，但没有跳过决定权**"。

**低分故事 2：迭代 1 Step 11-12，E7-ACCEPT "无法感受如何验收"（3/5）**

迭代 1 交付物全是后端 + CLI（采集器 + 配置），测试 38/38 过、验收报告写得漂亮，用户原话却是"这一步无法感受如何验收"——因为**没有一个端到端能看到的东西**。
根因不是验收节点本身，而是**迭代拆分做了水平切片**（迭代 1 做完所有后端 → 迭代 2 做存储 → 迭代 3 才做 UI），不是**垂直切片**（每迭代产出一个能端到端看见的最小闭环，哪怕很粗糙）。这条变成 kdev-agent P1-PLAN 节点的硬约束："每迭代至少产出一个用户可感知的最小闭环"。

### 1.3 最早长什么样

翻 `/home/lyadmin/Projects/token-statistics/.kdev/` 的历史，2026-04-10 的第一版目录是：

```
.kdev/
├── state.md              # 流程状态
├── questions-log.md      # 决策追溯
├── gotchas.md            # 踩坑
├── sprint0-journal.md    # 每步记录（含评分）
├── sprint0-playbook.md   # Skill 编排操作手册
└── daily-logs/           # 每日汇总
```

粒度和现在的 kdev-memory 已经非常接近——但**命名完全是英文 + 面向 一次性**的。一看就是"为了这个项目造的临时工具"。

到了 2026-04-13 前后，这套脚手架被证明足够稳，用户决定把它**中文化 + 通用化**：

| 原名（英文、专属） | 后来（kdev-memory 插件） |
|---|---|
| `state.md` | `当前状态.md` |
| `questions-log.md` | `决策日志.md` |
| `gotchas.md` | `踩坑日志.md` |
| `sprint0-journal.md` | `执行日志.md` |
| `daily-logs/` | `每日汇总/` |
| `conventions.md §11 + R-NNN` | `改进建议.md` |

改名只是表层，底层是把项目私有的规范抽象成可复用的制度。

### 1.4 什么时候决定"应该做成插件"

触发点是一个具体瞬间：token-statistics 跑到迭代 3 左右，用户说了一句——

> "这套 `.kdev/` 打分和记录机制别的项目能用得上吧？能不能装一下插件就有了？"

这时候意识到两件事：

1. **机制已经验证**过了，不是凭空设计——有真实数据在背书
2. **手工搭建门槛太高**——每个项目都要写 CLAUDE.md 触发规则段 + 手动建目录 + 记住编号规则

于是 2026-04-16 有了 kdev-memory 0.1.0：从 专属的脚手架，抽象成**所有项目装了就有**的插件。

### 1.5 为什么这个起源很重要

起源决定了这个插件的**边界**：

- ✅ **擅长**：长周期项目、实战验证项目、方法论验证、跨项目经验归纳——**因为它就是为了这些场景做出来的**
- ❌ **不适合**：一次性脚本、单会话任务、用 Jira/Linear 已经承接决策和缺陷的项目——**硬套就是过度工程**

这也解释了为什么核心设计里那么多**硬规则**（实时落盘、不翻会话、原始胜于提炼）——**它们都是在 token-statistics 里被"靠印象补写的评分完全失真"这类具体教训逼出来的**，不是先验设计。


### 1.6 后来才意识到：这个痛点其实是普遍的

把 kdev-memory 抽出来以后，才看清一件事：实战验证项目暴露的失忆问题，**其实是所有长周期项目都有**。

> 周一，你开一个 Claude Code 会话做项目 A，花两小时讨论技术选型，最后选了 B 方案，理由是"团队下个月要接 C"。
>
> 周三，你开新会话继续做项目 A，随口问："这里用 A 还是 B？" Claude 礼貌地给你一份全新的对比清单，倾向 A。
>
> 周五，你跑同一个 `pnpm install` 命令，它花 15 分钟帮你 debug 出"workspace 根目录要加 `-r`"——和上周二它自己踩过的那个坑一模一样。

这是多迭代、长周期项目里智能体的**结构性失忆**。问题不在模型聪不聪明——问题在于：

- **会话压缩**一来，早期细节直接没；
- **新会话**不会主动读昨天的记录；
- 就算有 `CLAUDE.md`，它是"规则"，不是"项目现状"；
- 官方自动 `memory` 机制更偏"用户偏好"，不是"工程日志"。

token-statistics 的实战验证只是**把这个普遍问题在一个具体项目里压缩暴露**出来了。

---

## 2. 定位与核心目标

很多记忆类插件做着做着就变成了"给 AI 上一套 庞然大物： 仪表盘 + 向量检索 + 摘要引擎等等"。我们一开始就给自己定好了核心目标：

### 2.1 核心目标

前两行是**机制**——决定 skill 怎么写记录；后两行是**任务**——这套机制要换来的产品价值。

| 机制 / 任务 | 本质 | 起源 / 为什么 |
|---|---|---|
| **实时落盘** | 每做完一步、踩一坑、做一决策、接一次评分，立刻落到 `.kdev/memory/` 对应文件——后台动作，不攒到会话末尾、也不等用户提醒 | 不实时落盘的三种后果：会话被压缩 / 崩溃 → 数据全丢；靠回忆写比实时差一个量级；评分过夜补录 → 第二天分数失真 |
| **每日汇总从文件聚合，不翻会话** | 写"今日总结"严格按"读 5 个 `.kdev/memory/*.md` → 按今日日期筛选 → 拼装写入 `每日汇总/YYYY-MM-DD.md`"路径；**严禁**回翻会话、让用户复述、凭印象 | 决定 skill 是否成立——靠回忆写就退化成"会话末尾写点总结"，毫无价值；按文件拼装则速度快、信息准、可审计 |
| **跨会话续航** | 让新会话 30 秒内接上昨天的工作 | token-statistics 实测：SessionStart 注入 ~700 token 索引，Claude 按需展开后总水位约 34k（拆解见下） |
| **保留踩坑证据** | 把"LLM 写得快但用户看着累"这类当场分歧**原样保留**成可引用的记录 | token-statistics 的 [`改进建议.md`](../../../../token-statistics/.kdev/改进建议.md) 反过来喂给 kdev-agent v3.0.1 改进架构——这是实际发生的用法，不是抽象设想 |

**文件是第一真相，会话是它的副本（Spec 思想）。** 上面四件事都是这一条原则的展开。

> **34k 是怎么拆出来的**（怕被误解成"kdev 一开场就吃 34k"，先把账算清楚）
>
> **基础税 ~27k（与 kdev 无关，卸了也省不掉）**：Claude Code system prompt 9.2k + deferred 系统工具名字列表 20.7k + 常驻工具 schema 1.7k + MCP 工具名字（playwright / context7 / Google Drive）7.3k，去重后约 27k。**80% 的开销在这里**。
>
> **Skill metadata 扫描 ~10.9k**：100+ 个已装 skill 的 description 全量扫一遍，kdev-memory + kdev-commit 加起来只占 ~290 token（2.7%）。
>
> **kdev-memory 真正贡献的部分 ~6-7k**：
> - CLAUDE.md 里的 schema / 编号规则 / 评分机制 / 触发表 ≈ 5-6k
> - SessionStart hook 注入的 `<kdev-memory-brief>`（待办 + 今日进度 + frontmatter 字段 + 最近 Step·Q·G 标题）≈ 0.5-0.8k
> - skill metadata ≈ 0.3k
>
> Claude 看完 brief 之后会按用户的实际问题决定要不要 Read `当前状态.md`、最近几份 `每日汇总/*.md`、相关的决策 / 踩坑切片——这部分**不是开场强塞，而是按需展开**。如果新会话只是问个简单问题，可能停在 brief 不再展开。
>
> **结论**：kdev-memory 在 34k 里实际占比 18-20%，剩下 80% 是 Claude Code 自己的固定开销。想瘦开场，先卸掉没在用的 MCP server 和 100+ 里没在用的 skill，比折腾 kdev 内部 ROI 高 3-5 倍。

### 2.2 否定的路线

| 否定的路线 | 为什么否定 |
|---|---|
| SQLite / 向量库 / FTS5（如 claude-mem） | 核心定位背离——我们要"文件落盘 + 人可读"，不要工具才能解码的黑箱 |
| 调用 LLM 做压缩摘要（如 claude-memory-compiler） | 和"实时落盘"定位冲突 |
| Continuous Learning 自动提取（如 ECC） | LLM 二次调用贵；原始证据比"提炼"更有价值 |
| 三层 notepad + 6 类 JSON 状态（如 OMC） | 文件碎片化、更适合子智能体间通信 |
| 在项目内强制执行"改进建议" | **记录和执行是两件事**，强制执行等于滥用 |

这些选择表面是技术选型，底层是产品定位——**我们要的是"诚实的项目日志"，不是"AI 大脑"**。

---

## 3. 版本迭代过程：从手工脚手架到 eval 驱动

> 这条线整体对照 [skill-官方开发流程.md](../../meta/skill-官方开发流程.md) 的 8 步走下来，每个版本对应流程里的一两步。下面按真实时序记，重点放在"这一版做了什么、为什么必须做"，细节实现挂回 commit / 子文档。

### 3.0 pre-plugin（2026-04-10 ~ 04-14）— 在 token-statistics 里跑通原型

没有插件、没有 hook，只有 `.kdev/` 目录 + 一份手写的 CLAUDE.md 触发规则段。这一阶段把后来插件版的核心原则全部验过：实时落盘（试过会话末尾回忆补写，分数偏高得离谱）、双评分雏形（用户和模型自评经常对不上）、改进建议不强制执行。

原型期的数据诚信度是整个项目里最高的——用户同时是设计者、使用者、审计者，三角色重叠让记录无法作弊；后来插件版的"反作弊"机制（时间戳锁定、强制扣分项、差值 ≥ 2 升 R）本质上都是在用结构补这层约束。

> 对应官方 §1 搞清楚开发目标 + §2 确认边界和进一步调研。这阶段是 skill 的"非正式 brainstorm"。

### 3.1 0.1.0（2026-04-15）— SKILL.md 初稿

- `.kdev/` 目录结构 + Step / Q-NNN / G-NNN / R-NNN 编号规则
- SKILL.md 定义触发词和记录 schema
- Stop hook 四态：未启用 → 静默 / 今天无汇总 → 提醒 / 执行日志今天空 → 提醒 / 其他 → 不打扰

这一版学到：**hook 必须能静默区分"启用 vs 未启用"项目**，否则装一次三天内就被卸。

紧接着 0.1.1（[`d3c8755`](https://github.com/KDevSec/kdev-agents/commit/d3c8755)）加了汇总过时检测——状态空间带"过时"这种时态语义，就必须显式处理，不能只看"有没有"。

> 对应官方 §3 写 SKILL.md 第一稿。

### 3.2 0.2.0（2026-04-18）— 加强hook触发

用户反馈炸出一个洞："我跑 Spec Kit 跑了两小时，Stop hook 提醒压根没被读到过。"诊断下来：Stop hook 的 stdout 软提醒只有"Claude 还要再工作一轮"时才会被读。Spec Kit 这种长 phase 跑完自然 idle 的场景完全失灵。

解法不是加强 Stop hook，而是**全时段铺闸**：

| 层 | Hook | 触发时机 | 作用 |
|---|---|---|---|
| 1 | SessionStart | 新会话启动 | 注入 `<kdev-memory-brief>` 摘要 |
| 2 | Stop | 每次要停下 | 软提醒（原四态） |
| 3 | Strict（opt-in） | Stop 时，需 `touch .kdev/strict` | 条件阻塞（执行日志空 + 工作区有变更 → exit 2） |
| 4 | PostToolUse | Write/Edit 后 | 命中里程碑白名单提醒 |
| 5 | PreCompact | 压缩前 | 写 checkpoint 快照 |
| 6 | SessionEnd | 切项目 / 关客户端 | 兜底写 WARN 文件 |

同时引入 `当前状态.md` 的 YAML frontmatter，让人 / 脚本 / Claude 三方共读，SessionStart 能秒报项目状态而不是去解析自由文本。

这版之前还做了一次横向调研（详见附录 A），看清六家上游各自的核心定位再确定差异化方向。

> 对应官方 §6 改进（读 transcripts 找漏的时相）+ §2 调研同类。

### 3.3 0.3.0（2026-04-19）— 记忆召回

0.2.0 跑了一阵暴露问题：记忆只是档案馆，不会主动浮现——用户再次跑 `pnpm install` 报错时，踩坑日志里明明有 G-012 记着一模一样的解法，但 Claude 不会主动读。

解法：

- **UserPromptSubmit hook + triggers 字面匹配**：用户 prompt → sanitize（strip 代码块/URL/路径，防误触）→ 扫 `.kdev/memory/` 里带 `triggers:` 的条目 → literal substring 匹配 → 命中注入 `<kdev-memory-recall>` 指针（只给编号 + 标题 + 路径，渐进式披露）→ Claude 自己决定读不读全文
- **命名空间化 `.kdev/memory/` + 零感知自动迁移**：SessionStart hook 启动时调 `migrate.sh`，检测旧结构就自动搬家，写 `MIGRATED-*.md` 清单给用户看

同时加了第一份 `evals/` 测试集（skill-creator 式的质量验证集），10 条测试 prompt：

```
✅ should-trigger 组：
  - "我跑 pnpm install 又报错了" → 应召回 G-012
  - "这个 aiohttp 的 proxy ClientDisconnected" → 应召回 G-014
  - "还在做采集器的核心循环" → 应召回 Step 23
  - "这个 API 怎么设计" → 应召回铁规
  - "项目架构决策" → 应召回 constitution.md

✅ should-NOT-trigger 组：
  - 用户贴代码块里有 "pnpm install" 字面量 → 不召回（sanitize 生效）
  - URL 里有 "workspace" 字样 → 不召回
  - 文件路径里有 "pnpm" → 不召回
  - 完全无关的话题 → 不召回
  - 字面搜索（"帮我在代码里找 pnpm"） → 不召回
```

配一份 `fixtures/project-state/` 完整测试项目状态。evals 不是跑着玩的——它固化了**什么算"召回正确"** 的契约，以后重构 hook 内部实现时这 10 条是回归锚点。这一组也是后来 0.5.x 引入 `skill-quality/evals.json` 第二条 eval 线的原型。

> 对应官方 §3 写 + §4 准备测试用例。

### 3.4 0.4.0（2026-04-20）— 按期归档

triggers 召回会让主文件随项目推进线性膨胀，长时间下来执行日志 1000+ 行、踩坑日志几十条 G-NNN，Read 效率和 trigger 扫描性能都吃力。

**按期归档**：执行日志按月、踩坑/决策按季度归档到 `.kdev/memory/归档/`。不设行数阈值（用日期边界更自然），Stop hook 跨期时提醒让用户确认再切（不自动搬）


### 3.5 0.5.x（2026-04-21 ~ 04-22）— eval测试集驱动迭代优化

到这一段出现一次方法论级跨越——从"凭功能需求改 skill"切到"用 eval 数据驱动改 skill"。

**起点**：SKILL.md 已经膨胀到 734 行，每次 skill 触发都拖着整份 700+ 进入上下文，渐进式披露口号喊了几版没真落地。
同时 token-statistics 项目反复出现"模型写完自评就把 Step 当完成了"的失守现象——根因不是 skill 本体逻辑有问题，而是 CLAUDE.md 旧的规则段已经跟 skill 实现脱节。 于是，通过skill-creator进行审计和迭代优化。

>eval 数据驱动改 = 改之前先建一套场景测试集（eval prompts），跑两版对比（baseline = 改前 / candidate = 改后），用数据看行为是不是真的变好——pass rate 升了没？token 降了没？有没有 regression？改动的依据是"数据说这么改更好"。

**两条 eval 线分工**：

```
evals/
├── evals.json                ← 测 hook 脚本（trigger-match 召回）— 改 hook 才跑
└── skill-quality/
    └── evals.json            ← 测 SKILL.md + references 的行为质量 — 改 skill 文档才跑
```

每场景独立 fixture（10 个 `eval-N-*/` 目录），每跑一轮新建 `iterations/<日期>-<序号>-<主题>/` 留下完整 with_skill / baseline 对比。

**7 轮 迭代 的关键动作**：

| iter | 修订内容 | 数据对比 |
|---|---|---|
| iter-1/2 Phase 1 重构 | SKILL.md 734 → 254 行，拆出 6 个 references；description 从 ~1400 字精简到 ~640 字 | 12 runs 100% pass（行为零损失），tokens 平均 -19.6%；with_skill 按场景动态读不同 reference，证明渐进式披露真在工作 |
| iter-3 接口 / 实现解耦 | CLAUDE.md 规则段重新定位为"skill 对外的稳定接口"——只放 3 条贯穿 session 铁规 + hook 注入标签 + 文件模式 + 召唤时机；触发表 / 评分细节 / 编号规则全搬到 SKILL.md / references。引入 `claude_md_contract` frontmatter 让接口**机器可读** | CLAUDE.md 57 → 38 行（-33%），edge case 零 regression。assertion 主动拒绝"实现细节偷偷溜回 CLAUDE.md" |
| iter-4 P1-7 contract lint | `hooks/lib/claude_md_lint.py`（纯 Python 无依赖）比对 skill contract vs 项目 CLAUDE.md，SessionStart brief 报漂移 + 提示召唤 skill 修 | with_skill 100% / baseline 75%——baseline 也合规但需"多轮裁决"，新版压成"单 diff 闭环" |
| iter-5/6 P1-5/6 Step 完整度 lint | `step_completeness.py` 扫执行日志找半残 Step（评分时分戳空 / 顺畅度占位 / 扣分项空）。brief 告警 + Stop 软提醒 + strict exit 2 阻塞。33 个新单元测试，累计 98 tests pass | 8/8 pass。亮点超出预期：skill 自发"坦诚反思"——承认 5/5 自评偏高、把真正的坑写进扣分项、引用 G-040 三方证据一致——**不编好听的** |
| iter-7 P0-1 Step 完成闸门 | 加 24 行硬闸门章节到 SKILL.md | 行为零差异（baseline 也能正确拦截诱导），但 -21% tokens / -7 tool uses。**初版判"不加"，user 反问点破后反转判"加"** |

> **iter-7 决策反转值得单独拎出来**——
> 初版结论："+22 行 SKILL.md 换 -21% tokens，行为又一样，不划算。" user 反问："**如果 baseline 换成 with_gate，效果一样还减少了 md 内容呢？**" 这一问点破：22 行是**一次性**写入成本（≈ +500 token 加载），12k tokens 是**每次触发**省的，按每天触发 20+ 次算每月净省 ~7M tokens。同一组数据换个算法得出反结论。
> 反转后正式合入闸门章节（260 → 286 行），iter-7 notes 加「决策反转修正」段**保留初版错误分析作为证据链**——不掩饰错误，给未来维护者留推理演进的轨迹比改干净更有教学价值。version bump 0.5.0 → 0.5.1（patch 级：只显式化已有隐含规则，行为不变）。

**审计问题修订完成度**：原 9 条建议最终落地 **7/8**，对于目前没项目暴露相关问题数据的，则不做防过度设计。

> 对应官方 §5 跑 evals + §6 改进 + §7 description 优化。

**这套 7 轮迭代 沉淀下来 3 条方法论**：

1. **eval 不是测试，是决策基础设施**——没 eval 之前，审计 §5.1 的 P0/P1/P2 都是"看起来对"的判断；有 eval 之后每条都被数据校准，包括 iter-7 的反转
2. **skill接口和具体规则要拆开**——任何写到项目 CLAUDE.md 的 skill 规则段都该用 `<plugin>_md_contract` frontmatter 声明接口，否则必然漂移
3. **成本/收益的衡量要明确"**——对成本 / 收益是一次性的，还是每次都付 / 每次都收？


### 3.6 0.6.0 ~ 0.7.1（2026-04-23 ~ 04-25）— 立场反转 + 跨平台 worktree 共享

这三个版本是一条完整的因果链：**实战踩坑 → 反转核心假设 → 补齐多 worktree 场景**。

**0.6.0**（04-23）：Step 执行事实段加「使用的 skill」字段（iter-8 discriminating eval 验证 11/11 vs baseline 7/11），Step 粒度指引（自然停顿点三信号），iter-7 reason-not-reasons 风格在 eval 上证明"列出错误模式"比"讲对的理由"省 -21% token、-35% tool uses。这是 eval 驱动迭代的稳定期，证明 iter-5~7 的方法论已经收敛。

**0.7.0**（04-24）—— 立场反转：`.kdev/` 从"跟代码 commit"改为"**本地过程目录默认 gitignore**"。触发链条：

1. G-028（多会话并发 Step 编号撞车）→ R-014 代码 worktree 隔离（补丁 1）
2. R-015 记忆 worktree 模型（补丁 2，退化为同 worktree 分 commit）
3. iter-9 合 master 时 `.kdev/` 4 个文件同时 merge 冲突——R-015 预测的"基线分叉"真实发生
4. 用户反思："如果 `.kdev/` 不 git 托管，是不是就不需要考虑这些问题了"
5. 团队场景追问："不同成员的记忆文件会混乱"
6. 结晶原则：**`.kdev/` 是过程记录，不是最终产物；团队共享的是产物，不是过程**

连带改造（一次合并发 release）：

| 模块 | v0.6 | v0.7 |
|---|---|---|
| README 立场 | "应该进 git" | "本地过程目录，默认 gitignore" |
| init 行为 | 只建文件 | 自动 append `.kdev/` 到 `.gitignore`（`KDEV_GIT_TRACK=1` 跳过） |
| SessionEnd WARN | `git status --porcelain` | `.last-flush` mtime 比对（不依赖 git） |
| Brief 欠评扫描 | 字面 grep "完成时间：—" | 销账识别（`status` 字段 + 启发式 `褪色补录` / `## Step M-` 兜底）+ 三层分层 P0/P1/P2 |
| 过程 → 产物 | 无 | `/kdev-memory-promote` 命令 + `promote_status` schema |
| 周总结 | 无 | `/kdev-memory-weekly` 滚动 7 天 + 四段骨架（过程资产 / 经验总结 / 问题教训 / 开发进展） |

教训：**核心假设被证伪时优先反转前提而不是继续打补丁**。R-014/R-015/建议 8/9 四层补丁都在"git 托管"错误前提下挣扎，反转后全部消解。

**0.7.1**（04-25）—— 补齐 worktree 共享的最后一公里：立场反转让 `.kdev/` 不托管之后，secondary worktree 默认看不到主 worktree 的记忆。新增 `hooks/lib/worktree-link.sh`：SessionStart hook 自动检测 secondary worktree，建 symlink（Linux/macOS）或 junction（Windows 用 `cmd /c mklink /J`，无需管理员权限）指向主 worktree 的 `.kdev/`。主 worktree 内切分支 **不特殊处理**——`.kdev/` gitignored 不被 git 切换影响，所有分支共用一份记忆；Brief 里加「当前分支」一行让 Claude 自觉分支语境。

**三版合起来的方法论**：

1. **skill 核心假设应在 README 里显式列出**（本例："`.kdev/` 应 git 托管"），便于证伪时精准定位
2. **skill 作者做 dog-fooding 是最重要的 validation 路径**——理论上的设计再合理都不如实战一次的反转信号
3. **跨平台要提前设计在 shell helper 里**——`stat -c` 配 `stat -f` 双 fallback、`date -d` 配 `date -v`、`ln -s` 配 `cmd /c mklink /J`，不是等 Windows 用户报 issue 再打补丁
4. **skill 迭代史应作为公开产物保留**——本章就是反转证据链的公开面

> 对应官方 §8 持续维护。立场反转是 "从产品哲学层面推倒重来"，跨平台补丁是"把同一产品在不同落地环境打磨"——两者都不是工艺活，是 skill 成熟度的真正标志。


### 3.7 横向调研要点（详细对比见文末附录 A）

0.2.0 设计前覆盖了 6 家上游：claude-mem（45k stars，SQLite + 向量库）、OMC（25k，三层 notepad）、ECC（143k，SQLite State Store）、claude-memory-compiler（LLM 编译摘要）、claude-reflect（纠正捕获）。

- **借鉴**：OMC 的 Session 去重 + stdin hang 保护、claude-memory-compiler 的 PreCompact 写盘范式、各家共识的 `hookSpecificOutput.additionalContext` 结构化注入
- **拒绝**：SQLite / 向量库（背离"文件落盘 + 人可读"）、调 LLM 摘要（违背实时落盘）、三层 notepad（碎片化）
- **差异化**：纯 Markdown + YAML、checkpoint 写纯快照、`additionalContext` 分档注入

调研不是为了抄最全的，是为了看清各家的核心定位再决定自己的差异化在哪——差异化不是功能数量，是**产品哲学**。

---

## 4. 几个可借鉴的设计范式

> 既是本插件用到的机制，也是写给其他插件作者的参考。

### 4.1 先在真项目里自用，不以"做通用插件"起步

#### 反例

"我觉得应该做一个通用的 XX 插件" → 凭空画 PRD → 开 repo → 设计数据模型 → 写 hook 框架 → 跑不起来 → 放弃。

#### 为什么这样对

- 真项目里用过 = **机制已经验证**，不是"我觉得会有用"
- 真项目里踩过的坑 = **文档里的每条规则都有来源**，不是抽象推演
- 用户主动要 = **需求信号真实**，不是你一个人觉得

#### skill-creator 对应

skill-creator 的 "Capture Intent" 阶段第一句话就是：

> The current conversation might already contain a workflow the user wants to capture (e.g., they say "turn this into a skill"). If so, extract answers from the conversation history first.

**它也不鼓励凭空造 skill——它鼓励从"已经在发生的工作流"里抽出来**。


### 4.2 description 是 skill 能否被自然召回的唯一锚点

这一条 **90% 的 skill 作者会踩**。

#### 问题

- 你写了很好的 SKILL.md 正文
- 用户说了一个应该触发它的 prompt
- Claude **不触发你的 skill**

原因几乎总是：**description 没包含用户的真实口语词**。

#### skill-creator 的一个具体技巧：积极触发的 description（官方叫 "Pushy Description"）

官方 SKILL.md 里有一段很直接的建议：

> Currently Claude has a tendency to "undertrigger" skills. To combat this, please make the skill descriptions a little bit "pushy". For instance, instead of:
>
> "How to build a simple fast dashboard to display internal Anthropic data."
>
> you might write:
>
> "How to build a simple fast dashboard to display internal Anthropic data. **Make sure to use this skill whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data, even if they don't explicitly ask for a 'dashboard.'**"

#### 检查清单

写完 description 后自问：

- [ ] 包含用户会说的 **3-5 个口语词**（中英文都要）
- [ ] 包含用户会说的**场景词**，不只是**功能词**
- [ ] 是否**积极触发**（有"make sure to use this skill whenever..."式引导）
- [ ] 用 `skill-creator` 的 `improve_description.py` 跑一遍


### 4.3 渐进式披露（Progressive Disclosure）

#### 反面

把 SKILL.md 写成一份 2000 行大纲：规则、示例、边界情况、FAQ、历史变更……所有内容一次性塞进去。

**后果**：Claude 每次触发都要读 2000 行，token 代价大；关键规则淹没在细节里。

#### 正面

分层披露：

- **SKILL.md 主体** = 核心规则 + 触发时机（~300-500 行封顶）
- **references/** = 可选的深度参考（Claude 觉得需要才 Read）
- **examples/** = 具体用例（按需加载）
- **scripts/** = 可执行脚本（不塞进 prompt）

#### 官方最佳实践

skill-creator 的 "Skill Writing Guide" 节：

```
skill-name/
├── SKILL.md (required)       ← 必须加载
│   ├── YAML frontmatter
│   └── Markdown instructions
└── Bundled Resources (optional)  ← 按需加载
    ├── references/
    ├── examples/
    └── scripts/
```

0.3.0 的 UserPromptSubmit hook 召回机制，**不**把踩坑日志的全文塞进上下文。它只注入：

```
<kdev-memory-recall>
相关记忆（本 session 首次召回，如无关可忽略）：

- G-012 "pnpm install 在 workspace 根目录会漏装子包依赖" → .kdev/memory/踩坑日志.md
- Step 23 "实现采集器核心循环" → .kdev/memory/执行日志.md
</kdev-memory-recall>
```

- 一条注入约 **30 token**，三条约 **100 token**
- Claude 判断相关自己 Read 全文，不相关一眼扫过就忽略
- **Read 的主动权在 Claude**——胜过强塞内容

这和 OMC 直接塞全文的做法形成对比。塞全文的问题：Claude 即便觉得不相关，也要花推理成本"绕过"那段内容；塞多了污染整个会话。

给智能体一个指针，胜过给它一本书。


### 4.4 减少外部依赖

整个 hook 层**不引入任何 Node / npm / pip 包**：

- Shell 脚本做大部分活（checkpoint、retention、milestone match、migrate）
- Python 3 做 JSON 解析和结构化匹配（`trigger-match.py` 518 行）
- **缺 python3** → UserPromptSubmit 静默降级；其他 6 层 hook 继续工作

插件的外部依赖越少，被放弃的概率越低。shell + 系统 Python 是"装 Linux 就有"的东西，不需要任何额外安装。

### 4.5 Hook / 触发机制按会话阶段覆盖

**只适用于需要 hook 的 skill / 插件。纯 skill 可以跳过这节。**

#### 反例

"发现 Stop hook 没触发，那就把 Stop hook 做得更健壮" → 但问题是**用户在会话自然 idle 的场景下 Stop hook 本来就没有下一轮上下文可以读提醒**，加强再多也没用。

#### 正面做法

**原则**：列出会话的不同阶段（新会话启动 / 活跃中 / 自然空闲 / 压缩前 / 结束 / 用户发 prompt），每个阶段**单独兜**，不要让一层承担所有。

**缺一层漏一种场景**——这个结论来自反复被用户反馈"xxx 场景下 hook 没触发"后才摸出来的。

#### Evals（测试集）是迭代循环的核心——skill-creator 自带全套工具

**这是 skill-creator 最容易被忽略的一部分。**

#### evals 不是"看着不错"的替代品

没有 evals：

- 改一版 → 凭感觉觉得变好了 → 其实上一版的一些功能回归掉了你不知道
- 改五版之后无法回答"和 v0.1 比到底好在哪"

有 evals：

- 每次改动跑一遍 → 量化前后差异
- 回归掉的功能一眼看出来
- 新功能是否真的有效可以证明

#### skill-creator 提供的 evals 套件

| 脚本 | 作用 |
|---|---|
| `run_eval.py` | 单个 prompt 跑 baseline + with-skill 对比 |
| `run_loop.py` | **Description Optimization**：按 5 轮 iteration 自动改 description（60/40 train/test split 防过拟合） |
| `aggregate_benchmark.py` | 多轮跑聚合（控制方差） |
| `generate_report.py` | 生成 HTML 报告给人看 |
| `quick_validate.py` | skill 写法的基础校验 |
| `package_skill.py` | 打包成 `.skill` 文件 |

### 4.6 实时采集失败证据 —— 别凭感觉改 skill

Skill 开发最容易踩的坑：**改完自己跑两遍感觉不错就发版**——结果用户用的时候才发现触发不了 / 触发了又乱输出。要避免这一点，就得在 §1 的自用阶段就**把失败场景的原始证据记下来**。

#### 三件必须**实时**记的事

1. **Claude 该触发却没触发** → 记下用户当时的完整 prompt
2. **Claude 不该触发却触发了** → 记下用户当时的完整 prompt（尤其是用户贴了代码/错误堆栈/文档的场景）
3. **Claude 触发了但输出不对** → 记下用户的反馈原话（"不是我要的" / "又漏了一条" / "应该 A 但它给了 B"）

为什么要**实时**：事后补写会失真（用户当时的原话、上下文细节都会被你"合理化"掉）。原始 prompt 和原始反馈是 §10 evals 的**唯一原料**——现在偷懒不记，以后写 evals 就没素材。

#### 这和 skill 开发怎么对应

| 场景 | 直接改什么 |
|---|---|
| 该触发没触发 | 改 §5 description（加关键词 / 积极触发措辞） |
| 不该触发却触发 | 加 sanitize 规则 / 缩窄 description |
| 触发了但输出不对 | 改 SKILL.md 正文的规则 / 加示例 |
| 某些时机下 hook 不生效 | 改 §7 hook 覆盖 |

**原话 = 定位信号**。记"用户说'又不触发了'"没用，记**当时用户的完整 prompt** 才能反推 description 哪个词没踩到。


#### 反例

"改完跑了几次感觉不错，发了" → 3 天后用户说"skill 还是不触发" → 回去翻聊天记录找当时的 prompt → 找不到 → 凭印象改 description → 再发一版 → 之前修好的场景偷偷回归了也不知道。


### 4.7 双评分机制：防止智能体的讨好式评分（引申——多模型评审skill）

每完成一个 Step，执行日志里要记两次评分：

```markdown
#### 模型自评（在接触用户评分前写入并锁定）
- 完成时间：2026-04-15 14:32    # 必须带分钟精度
- 顺畅度自评：4/5
- 本步最值得扣分的一点：G-012 的 pnpm 坑应该在初始化阶段就规避
  （强制要求：必须填一条扣分项，不允许空）

<!-- ---- 以下为锁定后的用户评分，模型不得回填修改上方自评段 ---- -->

#### 用户评分
- 完成时间：2026-04-15 14:35    # 必须晚于模型自评段
- 顺畅度：3/5
- 用户评价：subagent 写得快但字段名对不上 PRD，又得我返工
```

**反模式**：如果不锁定时间戳，智能体会先看用户评分再"自评"一个差不多的分数——这就是"讨好式满分"。时间戳是**唯一硬证据**，结构上两段紧挨着，没时间戳没法事后审计。

**反模式 2**：如果自评段不强制列扣分项，智能体会统统打 5/5。强制列一条扣分项，**让自我批评有个落点**。

**差值的信号意义**：
- 差值 = 0 或 1 且评价正面 → 健康
- 差值 = 1 且评价含负面文本 → 弱信号，聚合到 R-NNN 相近主题下
- **差值 ≥ 2 → 方法论漏洞**。典型症状："agent 写得很快但写出的东西用户看着累"

差值只**记录**，不强制在项目内闭环。项目内强制执行是滥用——它的价值是：未来某个 skill 作者跨项目 review 时，能从当时用户和 LLM 的分歧里提炼出新方法论。


---

## 5. 总结



kdev-memory 的核心原则：**文件是第一真相，会话是它的副本。实时落盘，汇总从文件聚合；记录而不强制执行；记忆召回给指针而不给全文。**

> 七层防线 / triggers 召回 / 双评分 / sanitize / YAML frontmatter / 命名空间 / 自动迁移 / claude_md_contract / Step 完整度 lint / eval 驱动迭代 都是为了让这条原则在真实长周期项目里不被任何边界情况打破。

---

## 附录 A：六家框架横向调研详细对比

0.2.0 设计之前做了一次横向调研，覆盖 6 家主流 Claude Code 记忆框架。原始文档在 [docs/design-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md](dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md)。

### A.1 对比总览

| 方案 | Stars | PreCompact | SessionStart | 存储 |
|---|---|---|---|---|
| **claude-mem** | 45k | PostToolUse 持续采集 + Stop 摘要 | 从 SQLite + 向量库 Progressive Disclosure | SQLite + FTS5 + Chroma |
| **claude-memory-compiler** | 125 | PreCompact/SessionEnd 调 Claude SDK 提取"有价值信息" | 注入编译后 `index.md` | 纯 Markdown |
| **claude-reflect** | 881 | 无专门 PreCompact | 注入纠正历史 | CLAUDE.md 同步 |
| **OMC (oh-my-claudecode)** | 25k | PreCompact checkpoint | 三层 notepad + 6 类 JSON | Markdown + JSON |
| **ECC (everything-claude-code)** | 143k | 无专门 PreCompact | SQLite State Store 加载 | SQLite |
| **kdev-memory** | — | **checkpoint 写纯 Markdown 快照 + source 分档注入** | **`additionalContext` 结构化注入分档摘要** | **纯 Markdown + YAML** |

### A.2 我们借鉴了什么

- **OMC 的 Session 去重思路**：`state/trigger-sessions.json` + TTL，避免同会话重复注入
- **OMC issue #240 的 stdin hang 保护**：所有读 stdin 的 hook 加 `timeout 1`
- **claude-memory-compiler 的 PreCompact 写盘范式**：压缩前总是写 checkpoint
- **各家一致的 `hookSpecificOutput.additionalContext`**：比裸 stdout 结构化得多

### A.3 我们明确拒绝的

| 路线 | 拒绝理由 |
|---|---|
| SQLite / 向量库 | "文件落盘 + 人可读"是核心卖点 |
| 调 LLM 做摘要 | 引入 API key、成本、延迟；违背实时落盘 |
| 三层 notepad + 6 JSON | 碎片化、膨胀 |
| regex 捕获纠正 | 属独立 concern，单独做 `kdev-correction` 更合适 |

再退一步看：调研不是为了抄最全的，而是为了看清每家的核心定位，然后决定自己和它们的差异化定位在哪。差异化不是功能数量，是**产品哲学**。

---

## 附录 B：相关资料

- 仓库：[KDevSec/kdev-agents](https://github.com/KDevSec/kdev-agents)
- 插件 README：[plugins/kdev-memory/README.md](../../../plugins/kdev-memory/README.md)
- SKILL 定义：[plugins/kdev-memory/skills/kdev-memory/SKILL.md](../../../plugins/kdev-memory/skills/kdev-memory/SKILL.md)
- CHANGELOG：[plugins/kdev-memory/CHANGELOG.md](../../../plugins/kdev-memory/CHANGELOG.md)
- 六家框架调研：[docs/design-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md](dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md)
- evals：[plugins/kdev-memory/evals/README.md](../../../plugins/kdev-memory/evals/README.md)

相关上游项目：
- [claude-mem](https://github.com/thedotmack/claude-mem) — SQLite + 向量库范式
- [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) — 三层 notepad + 6 类 JSON
- [claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler) — LLM 编译摘要
- [claude-reflect](https://github.com/BayramAnnakov/claude-reflect) — 纠正捕获
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — SQLite State Store
