# 2026-04-24 kdev-memory：.kdev/ 是否 git 托管的立场反转 — 过程 vs 产物分家

**提出日期**：2026-04-24
**提出语境**：token-statistics 项目 Step 15（方案 A 示范）后、iter-9 合 master 冲突期间的方法论讨论
**相关 skill**：kdev-memory（v0.1.0 以来的核心哲学假设）
**优先级建议**：P0 — 触及 kdev-memory README 核心定位，v0.7 前应处理
**关联 dev-notes**：
- [2026-04-24 多会话同项目编号冲突](2026-04-24-多会话同项目编号冲突.md)（方案 V 隐含相邻思路，但未触碰 git 托管前提）
- [2026-04-22 skill 使用记录与体验评分维度缺口](2026-04-22-skill使用记录与体验评分维度缺口.md)
- [2026-04-24 step 粒度从 phase 到自然停顿点的认知演进](2026-04-24-step粒度从phase到自然停顿点的认知演进.md)

---

## 核心结论（TL;DR）

经过 token-statistics 项目 Step 12~15 的一系列踩坑（G-028 账本竞态 + 建议 8 分支污染 + 建议 9 记忆基线分叉 + R-014 / R-015 立规 + merge 冲突现场），用户最终提出一个**推翻 kdev-memory 初版核心前提**的主张：

> **`.kdev/` 是记录过程的，不是最终产物；团队要共享的应该是产物（在 `docs/`），而不是过程。因此 `.kdev/` 整个不应 git 托管。**

这个主张的力道在于——**它从根本上消解了 G-028 / R-014 / R-015 / 建议 8 / 建议 9 所试图解决的所有问题**：不托管就没 merge 冲突、没账本竞态、没多会话/多成员并发协作问题。

但它直接对立于 kdev-memory 初版 README 的一条哲学主张："`.kdev/memory/` 是项目资产，应该进 git"。

本文档记录这次立场反转的完整链条 + 下游影响清单，作为 kdev-memory v0.7（或下一个大版本）重定位的原料。

---

## 一、问题起源：一系列补丁的终点

### 1.1 起因事件（token-statistics Step 12 起的连锁）

| Step | 日期 | 事件 | 产出规则 |
|---|---|---|---|
| Step 12 | 2026-04-22 | collector v1.3.2 Windows 安装修复；主控在 `iter-9/multi-tenant-auth` 分支上做独立热修 commit（`d4de3a7`），准备切 master 发版时被用户刹车 | **R-014**：非当前分支任务默认 worktree 隔离 |
| Step 15 | 2026-04-23 | T-23 修复后讨论"切分支时记忆怎么记"，现场示范"方案 A 双 worktree 模型"发现 git 不允许同 branch 两个 worktree 的限制，退化为"同一 worktree 代码/记忆分 commit" | **R-015 + 建议 9**：记忆落盘分 commit + 基线分叉良性冲突处理 |
| 2026-04-24 merge | 2026-04-24 | iter-9 合 master 的 merge 产生 4 个 `.kdev/` 冲突文件，正是建议 9 预测的"基线分叉"现场 | 触发用户新一轮反思 |

### 1.2 用户观察：问题不在冲突，而在前提

用户追问的关键两步：

**第一步**（Step 15 结尾）：

> "像这种需要切分支的情况，如何进行记忆记录呢"

→ 产出建议 9 + R-015（**补丁**方向：双 worktree 协作 / 同 worktree 分 commit）

**第二步**（merge 冲突期间）：

> "如果把 .kdev 不用 git 托管，是不是就不需要考虑之前担心的问题了"

→ 提出**釜底抽薪**方向

**第三步**（追问团队场景）：

> "如果 git 托管了，那么团队的不同成员在各自电脑上的记忆文件就混乱了"

→ 暴露托管假设在多成员场景下的根本不合理

**第四步**（结晶出哲学原则）：

> "我觉得不需要拆分语义，目前来看 .kdev 就是给个人使用的，至于能够团队共享的那部分，需要单独拿出来，放到其他目录里去共享，而不是在 .kdev 里，因为 .kdev 是记录过程的，而不是最终产物"

→ **过程 vs 产物分家原则** — 本次立场反转的核心

---

## 二、现状核查：kdev-memory 现有立场

### 2.1 Hook 层：**无强制**

核查范围：kdev-memory v0.6.0（当前最新 marketplace 版）所有 hooks：

```
session-start-brief.sh
session-end-check.sh
stop-check.sh
pre-compact-check.sh
user-prompt-trigger.sh
post-write-check.sh
```

用到 `git` 命令只有三处：

1. `git rev-parse --is-inside-work-tree` — 判断是不是 git 仓库（**不是就静默退出**，说明 skill 对非 git 仓库友好）
2. `git status --porcelain` — 看工作区是否 dirty（用于 SessionEnd / Stop 阶段生成 WARN 兜底）
3. `git status --porcelain` — PreCompact 阶段写 checkpoint 时附带工作区快照

**没有任何一处检查 `.kdev/` 是不是被 git tracked**。

结论：**hook 层对 ".kdev/ gitignore" 完全兼容，无需改动**。

### 2.2 README 层：**明确主张 commit**（哲学级）

`plugins/kdev-memory/README.md` 第 11~17 行对比表：

| 解决的问题 | 典型方案 | 记什么 | 存哪里 |
|---|---|---|---|
| 用户个人化画像（跨项目） | Claude Code 内置 auto memory | 用户偏好、协作习惯、外部系统指针 | `~/.claude/projects/<hash>/memory/`（用户机全局） |
| 会话流回放（让 Claude 记住昨天聊了啥） | 第三方会话压缩类插件 | 压缩后的会话 JSONL 摘要 | 项目内 gitignore 目录（本机私有） |
| **工程过程档案（kdev-memory）** | kdev-memory | 结构化决策/踩坑/Step/评分/改进信号 | **`.kdev/memory/`（跟代码 commit）** |

差异化设计点第 3 条（原文）：

> **可跟代码一起 commit**：项目内的工程决策/踩坑属于**项目资产**，应该进 git（不是只存在于个人机器）

**这是一个 skill 级的哲学定位**，不是技术强制。但它引导了所有使用者默认把 `.kdev/` commit 进 git，也就是本次立场反转要推翻的前提。

### 2.3 kdev-commit SKILL：无相关约束

grep 全文无 `.kdev` 相关字样 — kdev-commit 只管 commit 身份（ly-AI 后缀），不关心 `.kdev/` 是否被 commit。

### 2.4 项目 CLAUDE.md 模板：隐含假设托管

token-statistics 项目 CLAUDE.md "智能体自动记录规则"章节里的 **触发规则表** 假设每步更新都会 commit（"每完成 Step 都要顺手更新 `.kdev/memory/当前状态.md`" 等），没有显式说"托管 or 不托管"，但字里行间把 `.kdev/` 当作和代码同等待遇的仓库文件。

---

## 三、立场反转：旧设计 vs 新主张

### 3.1 两套哲学的正面对撞

| 维度 | 旧设计（kdev-memory v0.1~v0.6） | 新主张（2026-04-24） |
|---|---|---|
| `.kdev/` 本质 | 工程过程档案 = **项目资产** | 过程记录 = **个人草稿簿** |
| 团队共享方式 | 通过 git 共享（所有人共用 `.kdev/`） | 不共享过程；**只共享结晶后的产物**（`docs/`） |
| 产物在哪里 | `.kdev/memory/改进建议.md` 本身是产物 | 改进建议是**草稿**；产物是 `docs/05-报告/实战项目总结-KDev-Agent参考.md` 这种定稿 |
| 多会话并发应对 | R-014 / R-015 / 建议 8 / 建议 9（层层补丁） | **不需要补丁**：不托管就没 merge 冲突 |
| 多成员协作应对 | 未覆盖（README 中"团队共享"是假设，实际会撞） | **不纳入 `.kdev/` 职责**：个人用 `.kdev/`，团队协作用 `docs/` |
| 换机器迁移 | `git clone` 自动带 `.kdev/` | 手动 `scp .kdev/` 或 `rsync`（Claude Code 若有 sync 机制未来可补） |
| 历史追溯 | `git log --all -- .kdev/` 追溯条目演化 | 本机 append-only 文件本身就是时序记录 |

### 3.2 哲学原则（新主张）

**"过程（process）≠ 产物（result / artifact）"**：

- **过程**：决策轨迹、踩坑现场、Step 体验评分、当前工作状态、Step N 的模型自评内容——这些是**个人视角**的现场采集，不构成交付物
- **产物**：规范、架构决策、设计文档、PRD、验收报告、技术债清单、对外输出的反思总结——这些是**结晶**后的交付物，才应该共享

两者合并在 `.kdev/` 里，就是**用个人视角的私密现场去假冒团队共享资产**，必然矛盾：
- 要么现场质量被"对外发布"约束所降（评分不敢写真话 / 踩坑不敢写糗事 → 失真）
- 要么共享语义被"个人视角"污染（别人看到"用户评分 3.5"，这个"用户"指谁？当前机器的 ly，还是接手的张三？）

### 3.3 `.kdev/` 现有内容按新原则归类

| 内容 | 过程 or 产物 | 新位置 |
|---|---|---|
| `执行日志.md` Step 条目 | 过程（个人 Step 现场） | `.kdev/`（本地） |
| `踩坑日志.md` G-NNN | 过程（个人踩坑视角） | `.kdev/`（本地） |
| `决策日志.md` Q-NNN | 过程（个人决策路径） | `.kdev/`（本地） |
| `改进建议.md` | 过程（反思草稿） | `.kdev/`（本地） — 结晶后写入 `docs/05-报告/实战项目总结-KDev-Agent参考.md` |
| `当前状态.md` + frontmatter | 过程（个人进度跟踪） | `.kdev/`（本地） |
| `每日汇总/` | 过程 | `.kdev/`（本地） |
| `conventions.md` §1~§10（硬规） | 混合体 — 规则像产物，但维护是过程 | 实用选择：**整体留 `.kdev/`**，团队版另开 `docs/08-开发规范.md` |
| `conventions.md` §11 R-NNN 演化史 | 过程（规则来源） | `.kdev/`（本地） |

**结论**：**按新原则过滤，`.kdev/` 下基本全是过程**，没有真正必须托管的产物。产物类内容本就该在 `docs/` 下（本项目已经是这种结构）：PRD / SR / AR CSV / 技术设计 / 验收报告 / 实战总结 / 技术债清单。

---

## 四、立场反转对 kdev-memory 的下游影响

### 4.1 插件层面（kdev-memory 本体）

| 位点 | 改动 |
|---|---|
| `plugins/kdev-memory/README.md` 第 11~17 行对比表 | 最后一列从"**`.kdev/memory/`（跟代码 commit）**"改为"**`.kdev/memory/`（本地过程目录，默认 gitignore；可选托管但不推荐）**" |
| README 差异化设计点第 3 条 | "可跟代码一起 commit" → "**本地过程目录，换机器用 scp/rsync 迁移；git 托管为可选项（单人项目勉强可用，多会话/多成员强烈不推荐）**" |
| README"命名空间约定"章节 | 加一段"为什么默认 gitignore：过程 ≠ 产物" |
| README"核心机制"段 | 不用动 — 实时落盘 / 智能召回 / 双评分等都和是否 git 托管正交 |
| `docs/skills/kdev-memory/开发历程.md` | 加一段 "v0.7 立场反转"（见下方 §4.3 草稿） |
| `docs/skills/kdev-memory/kdev-memory 开发历程技术分享.md` | 同上补章节 |

### 4.2 Hook 层面：仅一处需要调整

**SessionEnd WARN 逻辑** — 当前基于 `git status --porcelain` 看 `.kdev/` 是否 dirty：

```bash
# 当前（简化版示意）
PORCELAIN=$(git status --porcelain -uall)
if [[ "$PORCELAIN" == *".kdev/"* ]]; then
  生成 WARN-未记录-$(date +%F).md
fi
```

`.kdev/` gitignore 后 `git status --porcelain` 不再返回 `.kdev/` 行 → **WARN 永远不触发**。需要改成**基于文件 mtime**：

```bash
# 新方案
CHECKPOINT_FILE=.kdev/memory/.last-flush  # 新增隐藏文件，每次 Step 完成 touch 一次
MODIFIED_AFTER_FLUSH=$(find .kdev -type f -newer "$CHECKPOINT_FILE" 2>/dev/null)
if [[ -n "$MODIFIED_AFTER_FLUSH" ]]; then
  生成 WARN-未记录-$(date +%F).md
fi
```

或者更简单：**SessionEnd 不再依赖 git**，改用"会话开始 snapshot 所有 `.kdev/` 文件 mtime → 会话结束前对比 → 有新增但未通过 user-prompt-trigger 提示的 → WARN"。

### 4.3 开发历程文档补充章节（草稿）

以下是要追加到 `开发历程.md` 末尾的新章节草稿：

```markdown
## v0.7 立场反转：`.kdev/` 不再主张 git 托管

**背景**：kdev-memory v0.1~v0.6 的 README 主张 "`.kdev/memory/` 跟代码 commit —— 工程决策/踩坑属于项目资产，应该进 git"。2026-04-24 在 token-statistics 项目的实战中，这个主张被证伪。

**证伪链条**：
1. **G-028**：多会话并发时 Step 编号撞车（2026-04-22）
2. **R-014**：代码 worktree 隔离（补丁 1）
3. **R-015 + 建议 9**：记忆 worktree 模型（补丁 2，退化为同 worktree 分 commit）
4. **merge 冲突**（2026-04-24）：iter-9 合 master 时 `.kdev/` 4 个文件同时冲突 —— 建议 9 预测的"基线分叉"真实发生
5. **用户反思**："如果 .kdev 不 git 托管，是不是就不需要考虑这些问题了"
6. **团队场景追问**："不同成员的记忆文件会混乱"
7. **结晶原则**：**".kdev/ 是过程记录，不是最终产物；团队共享的是产物，不是过程"**

**反转内容**：
- 旧定位：`.kdev/` 是项目资产 → 应 git 托管
- 新定位：`.kdev/` 是个人过程草稿 → 默认 gitignore；产物抽到 `docs/` 等处共享

**意义**：过去所有"多会话/多成员并发记忆协作"补丁（G-028 / R-014 / R-015 / 建议 8 / 建议 9）都是在**错误前提**下的补丁 — 不托管后这些问题自动消失。dog-fooding 发现的一次设计前提错误比任何补丁都有价值。

**实战参考**：[token-statistics 迭代 9 期间 Step 12~15 记录](https://github.com/KDevSec/token-statistics/tree/master/.kdev/memory) + 本 dev-note。
```

### 4.4 token-statistics 本项目的同步改动

（不属于 kdev-memory 插件范畴，但本 dev-note 顺带列出）

| 位置 | 改动 |
|---|---|
| `.gitignore` | 加 `.kdev/` |
| git 索引 | `git rm -r --cached .kdev/`（保留历史，移出未来 track） |
| `CLAUDE.md` "智能体自动记录规则" | 加一行"`.kdev/` 本地过程，不 git 托管；换机器用 scp/rsync" |
| `.kdev/memory/改进建议.md` 的建议 8 / 建议 9 | 加 blockquote "2026-04-24 已被'.kdev/ 不 git 托管'方案替代，本建议保留作为推理路径归档" |
| `.kdev/conventions.md` §11 R-014 / R-015 | 同上加"已被替代"标注 |

---

## 五、和已有 dev-notes 的关联与对照

### 5.1 vs `2026-04-24-多会话同项目编号冲突.md`

前文已完整列出 6 方案（I 硬分片 / II 中缀时间戳 / III 换单调 ID / IV hook 级 assignment / V git 原生 + 文档约定 / VI 文件锁），倾向方案 V。

**本 dev-note 提出的"不 git 托管"方案是一个 *方案 V 的极端形态 + 更根本的前提重置***：

- 方案 V（git 原生）仍然假设 `.kdev/` 托管，只是鼓励各自分支各自冲突合并
- **本方案（不托管）** = 不共享 = 不冲突 = 根本不走 merge

换句话说：前文方案 V 在"托管"假设下做妥协，本方案直接**移除托管假设**。前文的分析仍然成立，但优先级应调整：

- 单人多会话场景：**本方案（不托管）** > 方案 V > 其他
- 多成员协作：**本方案明确排除这个 scope**，推荐"产物抽到 `docs/` 由 git 管，过程各自本地"

### 5.2 vs `2026-04-22-skill使用记录与体验评分维度缺口.md`

该 note 讨论的"评分维度缺口"（skill 使用感受没地方写）**仍然独立有效**，和本次立场反转正交 — 不管 `.kdev/` 是否托管，评分 schema 都需要扩维度。

### 5.3 vs `2026-04-24-step粒度从phase到自然停顿点的认知演进.md`

Step 粒度问题也**独立于**托管问题。新定位下 Step 粒度仍然是核心设计。

### 5.4 vs `2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md`

CLAUDE.md 模板漂移问题**部分消解** — 如果 `.kdev/` 不托管，CLAUDE.md 里"智能体自动记录规则"那一整章的引导方向需要调整（不再强调 commit 时机、账本编号查重在多会话下的纪律等）。可以说本次反转触发了 CLAUDE.md 模板的新一轮改写需求。

---

## 六、待决策问题（给 KDevSec 下次设计会议）

1. **反转是否立即落地到 v0.7**？还是作为**文档层面可选说明**先保留（给用户自选）？
   - (a) 立即落地（READ改写 + hook SessionEnd 调整 + v0.7 release）
   - (b) 文档层面提供"两种部署模式" — 默认不托管 + 单人项目可选托管
   - (c) 观察期 — 等再一个实战项目验证后再动

2. **SessionEnd WARN 逻辑改写 — 基于 mtime 还是基于事件计数？**
   - (a) mtime 方案（上面 §4.2 草稿）
   - (b) 事件计数方案（hook 写入时 touch 计数文件，SessionEnd 比对）
   - (c) 放弃 WARN 兜底，依赖 user-prompt-trigger 主动落盘

3. **kdev-memory init 命令是否应该自动 append `.kdev/` 到项目 `.gitignore`？**
   - (a) 是（强制默认 gitignore）
   - (b) 提示但不强制（尊重用户选择）
   - (c) 不管（依赖用户阅读 README）

4. **团队版 kdev-memory 是否需要单独一个插件（kdev-team-memory）来处理"团队共享产物"**？
   - (a) 独立插件 — 明确只管"产物沉淀到 docs/"的链路
   - (b) 不另做 — 只是文档引导用户用 `docs/`
   - (c) 未来再看

---

## 七、本次反转的 meta 价值

这次立场反转本身就是 kdev-memory 方法论的**最佳证据样本**：

> **用户作为 skill 作者（KDevSec），在真实 dog-fooding 中用自己的 skill 踩坑、补丁、最终反转补丁的前提。这个链条留在 `.kdev/memory/` 执行日志 + 踩坑日志 + 改进建议里，正是 kdev-memory 最值得炫耀的能力 — "经验外溢"把个人实战沉淀成方法论改进。**

如果没有 kdev-memory 实时落盘、双评分、改进建议机制，这次反转可能只是"某天突然想到"；有了它之后，反转有完整的证据链（Step 12 用户评分 3.5 / 建议 8 / R-014 / Step 15 方案 A 现场 / merge 冲突现场 / 连环追问），能写成一份本 dev-note。

**反哺 KDev-Agent 的设计启示**：

- skill 作者自己做 dog-food 是最重要的 validation 路径（理论上的设计再合理，都不如实战一次的反转信号）
- skill 的**核心假设**应该在 README 里**显式列出**（本例："`.kdev/` 应 git 托管"），便于后续证伪时清晰定位
- 当核心假设被证伪，优先**反转前提**而不是**继续打补丁**（G-028 → R-014 → R-015 → 建议 9 是补丁链；反转"不托管"是重置）
- skill 迭代史应该作为公开产物保留（本例：开发历程.md 应主动记录这次反转，作为 v0.7 的立场声明）

---

## 附录 A：token-statistics 实战数据点

| Step | 日期 | 用户评分 | 关键信号 |
|---|---|---|---|
| Step 12 | 2026-04-22 | 3.5/5 | "多会话并发要开 worktree" → R-014 |
| Step 15 | 2026-04-23 | 4.5/5 | 方案 A 现场示范；但示范过程中发现 git 限制，现场退化 |
| 2026-04-24 merge | 2026-04-24 | — | 4 个 `.kdev/` 文件 merge 冲突 → 触发反转反思 |

完整记录见 [token-statistics/.kdev/memory/执行日志.md Step 12-15](https://github.com/KDevSec/token-statistics/blob/master/.kdev/memory/) 与 [改进建议.md 建议 8/9](https://github.com/KDevSec/token-statistics/blob/master/.kdev/memory/改进建议.md)。

## 附录 B：反转原则的一句话版本

> **`.kdev/` 记录个人如何走到了答案（过程），`docs/` 记录答案本身（产物）。过程对作者有价值，产物对团队有价值。**
