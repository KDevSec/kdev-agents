# kdev-memory skill v0.4.0 与项目实践全面审计

**日期**：2026-04-22
**起因**：token-statistics 项目连续 7 天 Step 缺失 + 评分漏采（04-15~04-21），用户排查根因
**范围**：不止 CLAUDE.md 漂移——覆盖 skill 规则层 / 项目文件层 / 模型行为层 / hook 兜底层四个面
**对照项目**：
- `/home/lyadmin/Projects/token-statistics/` —— 老项目，skill 从 v0.1 一路用到 v0.4.0，sprint 0 时代的 conventions.md 仍沿用
- `/home/lyadmin/Projects/KDevSec/` —— 新项目，2026-04-21 刚按 v0.4.0 初始化

---

## 1. 问题症状全景

### 1.1 token-statistics 侧

| 症状 | 具体现象 | 严重度 |
|---|---|---|
| **Step 条目大段空白** | Step 7（2026-04-13/14）→ Step 8（2026-04-20/21），中间 **7 天零 Step 条目**，跨迭代 5/6/7/8 主体开发全漏记 | 🔴 |
| **Step 8 "顺畅度：待补"** 跨天遗留 | 写了 Step 但用户评分为空，违 conventions §9.3 "当前会话末尾主动追问" | 🔴 |
| **10 个用户参与决策零评分** | Q-053~Q-062（6 子问题灵码集成 + 5 个 collector 架构 + 1 账号改名清理 + 1 项目下拉归属），全是用户亲答问题/做裁决的节点，按 §9.4 判定必评，**全部未写 Step 未评分** | 🔴 |
| **本会话补登动作也漏 Step** | 2026-04-22 补登 4 天汇总是对话驱动 + 用户请求，按规则应记 Step 9 + 当场采分，实际两样都没做 | 🔴 |
| **4 天每日汇总缺失** | 04-18/19/20/21 无汇总，跨天会话 + SessionEnd hook 未触发的兜底空缺；本会话补完 | 🟡 |
| **WARN-未记录-2026-04-22.md 悬挂** | SessionEnd hook 兜底文件未被之前会话识别处理；本会话识别 + 发现其根源是 v1.3.1 release 脚本没更新 package-lock | 🟡 |
| **全部 27 条 G-NNN 零 triggers** | 踩坑日志所有条目无 `triggers:` 字段 → UserPromptSubmit hook 零自动召回 → 用户再提类似场景时 debug 走回头路 | 🟡 |
| **Sprint 0 conventions §9.4 豁免误读** | "智能体受众节点豁免逐节点评分"被优先吸收，"整体 meta + BLOCKED 必采"被忽略 → iter 5/6/7/8 subagent-driven 全程零评分 | 🔴 |
| **state.md 位置错 + 无 frontmatter + 过期两天 + 内容失真** | 在 `.kdev/state.md`（非 `.kdev/memory/当前状态.md`），updated_at 04-20 13:30，current_state 仍是 ITER8-KICKOFF（实际 iter 8 + 批次 1 都已完成） | 🟡 |
| **Step 编号硬绑 Sprint 0 状态机** | CLAUDE.md 编号规则把 Step 绑到 E1-AR~E7-ACCEPT；iter 5+ 用户明示"跳流程"后 Step 定义坍塌，没人重新定义边界 → 工作单元找不到 Step 归属 → 干脆不写 | 🔴 |
| **kdev-commit 邮箱策略 v0.1/v0.2 混乱** | CLAUDE.md 旧描述写 `ly-AI@noreply.local`（v0.1 策略，独立邮箱），实际 hook v0.2.0 已改为"沿用真实邮箱、区分维度改为 user.name"；2026-04-20 `c496d37` 已对齐 | ⚪ |
| **G-020 跨会话编号双义** | A 会话登记 G-020 为"cron 增量过严"，B 会话独立用 G-020 指"UI 隐藏交互时间"，两者指代不同事件；2026-04-20 G-026 澄清 + R-008 闸门规则 | ⚪ |

### 1.2 KDevSec 侧

| 症状 | 具体现象 | 严重度 |
|---|---|---|
| **Step 1 污染样本事件** | 模型自评段写了 + 诚实标注"未当场采集，不计入差值统计" + 扣分项明确列出；但用户评分时分戳为 `—` | 🟡 |
| **缺 Step 完成闸门硬表达** | CLAUDE.md 写"当场采集不允许延后"——是动作顺序要求，不是完成判定要求 | 🟡 |
| **改进建议.md 漏 R-001** | Step 1 污染样本是典型改进信号（差值算不出但漏采本身是信号），改进建议.md 仍为空骨架 | ⚪ |

### 1.3 共性

- 两项目都暴露**模型"写完自评段就认为 Step 完成"**的行为惯性——规则对齐与否都没堵住
- 两项目都缺**"用户评分段时分戳未填 = Step 未完成"的硬闸门**——skill 现有文案是格子语言不是闸门语言
- 两项目的 Step 1（KDevSec）/ Step 8（token-statistics）是同一类失守的两种表现：KDevSec 诚实标"污染样本"，token-statistics 写"待补"蒙混——KDevSec 做得比老项目好，但本质一致

---

## 2. 规则层对照：8 个干扰点

| # | 干扰点 | token-statistics | KDevSec | 干扰根源 |
|---|---|---|---|---|
| 1 | Step schema 四段式 vs 简化版 | ❌ CLAUDE.md L65-87 只有"顺畅度/用户评价/GAP"三字段 | ✅ L39 明列"执行事实 + 模型自评（含扣分项）+ 用户评分" | 简化版让"填个数就算合规"；skill 原意"四段式 + 时分戳锁定"被拆解 |
| 2 | "每步结束后"动词 | ❌ "主动向用户征询"（请求式） | ✅ "模型先自评+列事实，再让用户打分；**当场采集不允许延后**" | "征询"被模型吸收为可选；"模型先自评"前置动作被省略 |
| 3 | §9.4 智能体受众豁免误读 | ❌ conventions.md 表格里"豁免逐节点"被优先吸收 | ✅ 无 conventions.md 包袱 | 禁止规则（不允许完全不评）不是动作指令，模型不会主动产出 meta 评 |
| 4 | 当前状态.md 位置/frontmatter/时效 | ❌ `.kdev/state.md`（老路径）+ 无 frontmatter + 两天前 + 失真 | ✅ `.kdev/memory/当前状态.md` + 完整 YAML frontmatter + last_updated 今天 | hook 拿不到 frontmatter → brief 注入不准 → AI 开局无警觉 |
| 5 | triggers 字段 | ❌ 27 条 G + 8 条 Step 零 triggers | ✅ Step 1 已加；CLAUDE.md L29/L46 明确要求 | UserPromptSubmit hook 扫不到关键词 → 再次踩坑 + 再次漏 Step |
| 6 | hook 行为响应 | ❌ CLAUDE.md 一条没写 | ✅ L21-31 完整列 WARN / brief / checkpoint / recall + 触发表呼应 | AI 看到 hook 注入不识别 → 兜底失效 |
| 7 | Step 编号硬绑状态机 | ❌ 绑 E1-AR~E7-ACCEPT；iter 5+ 跳流程后 Step 定义坍塌 | ✅ 全局递增跨迭代延续（Q-001 明确） | 项目脱离 Sprint 0 后，Step 没有跟上 skill v0.4.0 的"工作单元 = Step"宽粒度 |
| 8 | CLAUDE.md 与项目状态同步 | ❌ MVP 完成态仍是 Sprint 0 产物 | ✅ 新建同步 | 规则段沉淀多版本 + 项目阶段迁移无人回炉 |

**命中率**：token-statistics 8/8 规则层；KDevSec 0/8 规则层 + 1.5/8 行为层。

---

## 3. 问题分类（五类十四条）

### 类别 A：规则文件漂移

| A1 | CLAUDE.md Step schema 是简化版（三字段）不是四段式 |
| A2 | CLAUDE.md "每步结束后"动词用"征询"（请求式）不是"公布→问→锁定"（强制式） |
| A3 | CLAUDE.md 无 hook 行为响应段（WARN / brief / recall / checkpoint / 归档提醒都没写） |
| A4 | CLAUDE.md Step 编号硬绑项目状态机（E1-AR~E7-ACCEPT），跳流程后坍塌 |
| A5 | conventions.md §9.4 豁免条款只写禁止项不写动作项（没明确"meta + BLOCKED 必采"） |
| A6 | kdev-commit 邮箱策略 v0.1→v0.2 升级时 CLAUDE.md 未同步（已后补修复） |

### 类别 B：文件组织偏差

| B1 | `.kdev/state.md` 位置错（skill v0.3.0+ 已移到 `.kdev/memory/当前状态.md`） |
| B2 | `state.md` 无 YAML frontmatter（hook 脚本化依赖失效） |
| B3 | `state.md` 更新频率不足（两天未更新，内容失真） |

### 类别 C：账本完整性缺口

| C1 | Step 条目 7 天大段空白（iter 5/6/7/8 主体开发全漏） |
| C2 | 用户参与节点无 Step（Q-053~Q-062 共 10 条决策全漏） |
| C3 | 智能体受众批次无 meta 评分（iter 5/6/7/8 subagent-driven 全程零评） |
| C4 | Step 写了但用户评分段空（Step 8 "待补"跨天遗留 / KDevSec Step 1 "污染样本"） |
| C5 | 27 条 G + 8 条 Step 零 triggers（召回全失效） |
| C6 | 4 天每日汇总缺失（04-18~04-21，跨天会话 + SessionEnd hook 兜底未生效） |

### 类别 D：模型行为惯性

| D1 | 模型写完自评段就认为 Step 完成，不主动公布分数问用户 |
| D2 | 模型看到 WARN 文件但不知道是 SessionEnd hook 兜底，不按流程处理（本会话靠我手动识别） |
| D3 | 模型吸收"豁免"两字后忽略"meta 必采"兜底要求 |
| D4 | 模型在对话驱动小任务（如本次补登）中默认不记 Step（"这事太小不算节点"的认知偏差） |

### 类别 E：hook 兜底薄弱

| E1 | Stop hook 不扫 Step 完整度（用户评分段空也不报） |
| E2 | SessionStart `<kdev-memory-brief>` 不报欠评 Step（启动时不告警） |
| E3 | WARN 兜底文件依赖 CLAUDE.md 显式引导才会被 AI 识别（CLAUDE.md 漂移就失效） |
| E4 | 无 CLAUDE.md 版本漂移检测（skill 升级后老项目拿不到收益） |

---

## 4. 根因分析

### 4.1 根因 1：规则层是"沉积物"不是"活文档"

skill v0.1 → v0.4.0 经历 6 版迭代，每版 CLAUDE.md 模板都有新内容（v0.3 加 frontmatter、v0.3.1 加 WARN 响应、v0.4.0 加归档提醒 + triggers 召回）。但：

- 老项目的 CLAUDE.md 是某版本写入后**冻结**的 snapshot
- skill 升级时**没有**"CLAUDE.md 漂移检测 + 重写提示"机制
- 老项目拿不到 skill 迭代的收益，反而规则层与 skill 脱节制造执行盲区

token-statistics 的 CLAUDE.md 就是 v0.2 时代产物，KDevSec 直接用 v0.4.0 模板 → 两者规则层同质性差异巨大。

### 4.2 根因 2：Step 完成判定无闸门（规则对齐也挡不住）

KDevSec 是规则层完美、执行层仍失守的反例：

- Step 1 模型诚实标"污染样本"（比 token-statistics "待补"好）
- 但仍然没拿到用户评分
- 原因：skill SKILL.md 把用户评分段定义为"格子"（有就填无就留空），没有定义为"闸门"（没填就不算 Step 完成）

模型面对 Step 时的两条执行路径：
- **路径 A（对）**：自评写完 → 公布分数给用户 → 问 → 等用户答 → 填入并锁时分戳
- **路径 B（模型默认）**：自评写完 → 用户评分段留"—"/"待补"/"污染样本" → 继续下一步

skill 没有机制判别哪条路径合规，模型默认走 B（更快、不打断用户、不需要用户介入）。

### 4.3 根因 3：豁免单向弹性无底线

conventions §9.4（以及 skill v0.4.0 对应表达）：

> 智能体受众节点豁免逐节点评分，改为整体 meta + BLOCKED 干预点评

模型吸收后优先拿走"豁免"（省事），忽略"meta + BLOCKED"（增事）。禁止项段"不允许跳过而无替代采集点"是**负面规则**，不会驱动模型主动生成 meta 评分。

实际后果：iter 5/6/7/8 四个迭代（每个都用 subagent-driven-development）**全零评分**——既没逐节点评，也没 meta 评。豁免单向弹性成了全程静默的许可。

### 4.4 根因 4：Sprint 0 状态机绑定失效后无替代方案

token-statistics CLAUDE.md 编号规则：
- Step N 对应"Sprint 0 流程表步骤编号"
- state.md 迭代 4 进度表里明列 Step 1~Step 8（PRD / brainstorm / 技术设计 / ...）

iter 5 用户明示"快速迭代" + iter 7/8 明示"不走流程"后：
- 没有 E1-AR~E7-ACCEPT 节点
- Step 编号失去映射规则
- **于是根本没人写 Step 条目** —— 不是忘了评分，是节点本身不存在

skill v0.4.0 的 Step 粒度是"一个工作单元 = 一个 Step"（含 skill 回合、对话驱动、技术债扫尾），**不绑状态机**。但项目从 Sprint 0 延续的 CLAUDE.md 没切过来。

### 4.5 根因 5：hook 兜底设计没覆盖"Step 半残"场景

Stop hook 现有检测项：
- 今日无汇总
- 汇总过时
- 执行日志今日空
- 跨日期漏汇总（04-18~04-21 跨天就是这个场景）

**不检测**：
- Step 条目用户评分段时分戳是否为空
- Step 条目执行事实段是否完整
- Step 数量是否匹配当日 skill invocations 数

所以 Step 写了但半残（Step 8 "待补" / KDevSec Step 1 "污染样本"），hook 认为文件层面合规 → 不报错 → AI 认为当日交差 → 评分债跨会话滚。

---

## 5. 修订建议（分层 + 分优先级）

### 5.1 skill v0.5.0 规则层改进（影响所有未来项目）

**P0 · 必做**

1. **SKILL.md 加"Step 完成闸门"章节**，定义硬判定：
   ```
   Step 完成判定：四段必填 —— 缺任一段视为未完成。
   - 执行事实段：工具调用/报错/绕路/token 感任一字段缺 → 未完成
   - 模型自评段：扣分项缺 → 未完成
   - 用户评分段：时分戳为 — 或空 → 未完成
     （标"污染样本"视为未完成，但比"待补"更诚实）
   - 评分差异分析段：两段时分戳都填后才能生成

   下一步工作前必须补齐或显式开 R-NNN 记录行为缺陷。
   ```

2. **"每步结束后"动词改为动词链**：skill 触发规则段模板现在写"征询"——改为：
   ```
   每步结束后 → 模型先写执行事实 + 自评（带扣分项）
             → 【公布自评分数给用户】
             → 【询问用户打分】
             → 【填入并锁定两段时分戳】
   四步任一缺失 = Step 未完成
   ```

3. **§9.4 式豁免动作化**：把现有文案"豁免逐节点评分，改为整体 meta + BLOCKED"改为正向动作项：
   ```
   subagent-driven / writing-plans / deploy 类节点：
   - 跳过每个 subagent 调用的逐节点评分
   - 但批次整体结束时【必须】收 1 次 meta 评分（用户对整批的顺畅度感受）
   - BLOCKED 干预点（主控被用户打断/纠正的时刻）【必须】单独评
   - 两个评分任一缺失 → 批次 Step 视为未完成
   ```

4. **Step 定义脱离状态机**：SKILL.md 明确写"一个工作单元 = 一个 Step 候选"，列举：
   - skill 回合（brainstorming / writing-plans / subagent-driven / gstack-* / kdev-commit 等）
   - 对话驱动工作（技术债扫尾、补登、评审、文档修订）
   - 项目阶段节点（向后兼容老项目的状态机模式，但不作为 Step 定义的唯一来源）

**P1 · 建议做**

5. **SessionStart `<kdev-memory-brief>` 加"欠评 Step 告警"**：启动时扫执行日志最近 N 条 Step，若有"用户评分时分戳为空"/"污染样本"/"待补" → brief 里⚠️列出 → 新会话第一件事补采或销账

6. **Stop hook 加 `check-step-completeness.sh`**：扫今日新增 Step 条目：
   - 用户评分段时分戳空 → 软提醒
   - 执行事实段字段缺 → 软提醒
   - strict 模式下升级为 exit 2 硬阻塞

7. **CLAUDE.md 版本漂移检测**：
   - skill 落一个 `.kdev/memory/.claude-md-version` 标记文件记录项目 CLAUDE.md 对应的 skill 版本
   - SessionStart hook 比对：当前 skill 版本 > 标记版本 → brief 里⚠️ "CLAUDE.md 可能是旧版本 skill 写入（vX.Y），当前 skill 已升级到 vA.B，建议重写"
   - 提供 `kdev-memory:upgrade-claude-md` skill 一键重写（用户确认后执行）

**P2 · 可选**

8. **SKILL.md 加"升级指南（vX → vY）"章节**：列出每版 CLAUDE.md 模板差异 + 迁移步骤（老项目升级路径显式化）

9. **引入"批次 meta 自动兜底采集"**：当 subagent-driven 批次结束时，skill 自动注入一个"请对本批整体顺畅度打分（1-5）+ 一句话感受"的标准 prompt，不能被模型省略

### 5.2 token-statistics 项目级修复

**P0 · 今天**

1. CLAUDE.md 全段重写：对齐 v0.4.0 skill 触发规则段模板
   - 四段式 Step schema
   - "公布→问→锁定"动词链
   - 加 hook 行为响应段（WARN / brief / recall / checkpoint / 归档提醒）
   - 编号规则改"全局递增跨迭代"（脱离状态机绑定）
2. conventions §9.4 禁止项段改正向动作项（见 5.1 第 3 条）
3. 本会话补登动作记为 Step 9 + 当场采评分（避免"修 bug 的同时制造新 bug"）
4. 处理 04-22 悬挂的 `package-lock.json`（与 v1.3.1 release 脚本 TODO 同根）

**P1 · 本周**

5. 迁移 `.kdev/state.md` → `.kdev/memory/当前状态.md` + 加 YAML frontmatter
6. 批量补 triggers：27 条 G + 8 条 Step 加 `triggers: [...]` 字段
7. 回补 Step（按 §9.4 新动作项补 meta）：
   - Step 5.5 迭代 5 meta（2026-04-15~16）
   - Step 5.6 迭代 6 meta（2026-04-17~18，含 OpenCode G-016/G-017）
   - Step 5.7 迭代 7 meta（2026-04-19，含 Q-053~Q-060 + G-018~G-022）
   - Step 5.8 迭代 8 transitions meta（2026-04-20，含 AR-12.1~12.7 + 灵码运维 Q-061）
   - Step 8 追补评分（若用户感受未完全褪色）

**P2 · 持续**

8. 把 "R-候选"（Step 8 发现的两条：技术债"已修"标覆盖文件清单 / 批次扫尾默认走 ii）闭环到 conventions §11

### 5.3 KDevSec 项目级修复

**P1 · 本周**

1. CLAUDE.md "评分机制要点"段加 Step 完成闸门硬表达（对齐 5.1 第 1 条）
2. Step 1 污染样本事件追加 R-001 到 [改进建议.md](../../../KDevSec/.kdev/memory/改进建议.md)：记"模型自评段完成 ≠ Step 完成"的行为惯性
3. 本会话按 skill 流程补一次 Step 1 延迟采集评分（区别于零采集）

---

## 6. 对 skill 长期演进的启示

### 6.1 盲区 1：SKILL.md 没有"项目升级时重写 CLAUDE.md"的路径

- skill 迭代了 6 版，但没有"老项目从 vX 升级到 vY 时怎么办"的章节
- CLAUDE.md 一旦写入就是 frozen snapshot，skill 演进在老项目无法兑现
- **改进方向**：5.1 第 7、8 条

### 6.2 盲区 2：skill 假设"规则写对 = 执行到位"，忽略行为闸门

- KDevSec 就是规则层完美、执行层仍失守的反例
- Step 1 的"污染样本"是模型诚实标注的（比 token-statistics "待补"好），但仍然没拿到用户评分
- **改进方向**：5.1 第 1、2、6 条

### 6.3 盲区 3：豁免单向弹性无底线

- §9.4 豁免本意"减少过度打扰用户"，实际效果"整个批次零评分"
- 弹性只单向（跳过）没设底（meta + BLOCKED 必采）→ 实际总体采集率趋零
- **改进方向**：5.1 第 3、9 条

### 6.4 盲区 4：hook 兜底只扫文件层面不扫语义层面

- Stop / SessionStart / SessionEnd hook 现在只检查"文件存不存在、日期对不对"
- 不检查 Step 条目四段字段是否齐全、时分戳是否合法、数量是否匹配 skill invocations
- Step "半残"（写了但欠评）绕过全部兜底
- **改进方向**：5.1 第 5、6 条

### 6.5 盲区 5：Step 粒度定义绑项目状态机

- skill 假设 Step 粒度=工作单元（宽松），但项目 CLAUDE.md 常绑状态机节点（严格）
- 项目脱离状态机（如 token-statistics iter 5+ 跳流程）后，Step 定义消失，账本空白
- **改进方向**：5.1 第 4 条

---

## 7. 行动清单（优先级 + 负责工程 + 估时）

### skill / kdev-agents 工程

| 优先级 | 工作项 | 估时 | 影响面 |
|---|---|---|---|
| P0 | SKILL.md 加"Step 完成闸门 + 四段必填"章节 | 1h | 所有项目 |
| P0 | 触发规则段模板改"公布→问→锁定"动词链 | 0.5h | 所有项目 |
| P0 | §9.4 豁免表达改为"meta + BLOCKED 必采"动作项 | 0.5h | 所有项目 |
| P0 | SKILL.md 写明"Step 定义 = 工作单元"脱离状态机 | 0.5h | 所有项目 |
| P1 | SessionStart brief 加"欠评 Step 告警" | 1h | 未来新会话 |
| P1 | Stop hook 加 check-step-completeness | 1h | 未来新会话 |
| P1 | CLAUDE.md 版本漂移检测机制（标记文件 + brief 提示） | 3h | 所有项目 |
| P2 | SKILL.md 加"升级指南 vX→vY" | 2h | 老项目迁移 |
| P2 | subagent-driven 批次 meta 自动注入采集 prompt | 4h | 所有项目 |

### token-statistics 工程

| 优先级 | 工作项 | 估时 |
|---|---|---|
| P0 | CLAUDE.md 全段重写对齐 v0.4.0 模板 | 1h |
| P0 | conventions §9.4 同步改动作项 | 0.5h |
| P0 | 本会话补登动作记 Step 9 + 采分 | 0.2h |
| P0 | 处理 04-22 悬挂 package-lock.json | 0.1h |
| P1 | state.md 迁移 + 加 frontmatter | 0.5h |
| P1 | 批量补 27 G + 8 Step 的 triggers | 2h |
| P1 | 回补 iter 5/6/7/8 四条 meta Step + Step 8 评分 | 2h |
| P2 | Step 8 R-候选闭环到 conventions §11 | 1h |

### KDevSec 工程

| 优先级 | 工作项 | 估时 |
|---|---|---|
| P1 | CLAUDE.md 加 Step 完成闸门表达 | 0.2h |
| P1 | 补 R-001 到改进建议.md | 0.2h |
| P1 | Step 1 延迟采集评分 | 0.1h |

**估时总和**：skill 工程 13.5h / token-statistics 7.3h / KDevSec 0.5h / **合计 ~21h**

---

## 8. 证据链索引

### token-statistics 侧
- 执行日志 Step 7 / Step 8 + "顺畅度：待补"：[执行日志.md](../../../token-statistics/.kdev/memory/执行日志.md)
- Q-053~Q-062 决策全是用户参与节点但无 Step：[决策日志.md](../../../token-statistics/.kdev/memory/决策日志.md)
- §9.4 豁免条款：[conventions.md:259-274](../../../token-statistics/.kdev/conventions.md#L259-L274)
- 简化版 Step schema：[CLAUDE.md:65-87](../../../token-statistics/CLAUDE.md#L65-L87)
- Sprint 0 状态机绑定：[CLAUDE.md:125-135](../../../token-statistics/CLAUDE.md#L125-L135)
- 老位置 state.md：[.kdev/state.md](../../../token-statistics/.kdev/state.md)
- 零 triggers 踩坑日志：[踩坑日志.md](../../../token-statistics/.kdev/memory/踩坑日志.md)
- 4 天漏汇总 + 本次补登：[每日汇总 04-18/19/20/21/22](../../../token-statistics/.kdev/memory/每日汇总)
- G-020 编号双义 + R-008 闸门：[踩坑日志.md G-026](../../../token-statistics/.kdev/memory/踩坑日志.md)

### KDevSec 侧
- Step 1 污染样本事件：[执行日志.md](../../../KDevSec/.kdev/memory/执行日志.md)
- v0.4.0 对齐 CLAUDE.md：[CLAUDE.md](../../../KDevSec/CLAUDE.md)
- 正确 frontmatter：[当前状态.md](../../../KDevSec/.kdev/memory/当前状态.md)
- 空改进建议（待补 R-001）：[改进建议.md](../../../KDevSec/.kdev/memory/改进建议.md)

### skill 侧
- 当前版本 SKILL.md：`/home/lyadmin/.claude/plugins/cache/kdev-agents/kdev-memory/0.4.0/skills/kdev-memory/SKILL.md`
- 版本历史目录：`/home/lyadmin/.claude/plugins/cache/kdev-agents/kdev-memory/`（0.1.0 / 0.1.1 / 0.2.0 / 0.3.0 / 0.3.1 / 0.4.0）
- 本次审计与 2026-04-21 三方记忆方案对比文档互参：[2026-04-21-三方记忆方案对比](./2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md)

---

## 9. 2026-04-22 次日补登观察（KDevSec 侧延伸）

**起因**：2026-04-22 用户开新会话时一句"昨天的汇总还没记录？"触发本次补登。在补登过程中又暴露三个主文档未覆盖的具体机制，记录于此供 skill 后续迭代参考。

### 9.1 机制 1：工程记忆"初始化自举盲区"

主文档 §4.2 根因 2 已指出"Step 完成判定无闸门"导致 KDevSec Step 1 漏采。但 Step 1 漏采还有一个**初始化专属的亚机制**未被点名：

**现象**：kdev-memory skill 的初始化流程本身（切分支 → 建 `.kdev/memory/` 骨架 → 写 CLAUDE.md → 走 Q-001）是一个典型的**工作单元**，理应就是 Step 1。但：
- skill SKILL.md 的初始化章节只说"建骨架 → 走 Q-001 → 同步到 CLAUDE.md"，**没要求初始化完成时立刻写 Step 1 + 采分**
- 模型的默认理解：Step 1 是"项目第一个业务工作单元"，初始化动作归在"skill 元动作"而不是"项目工作单元"
- 于是初始化完成时模型不会触发"写 Step 1 + 采分"的动作链

**后果**：工程记忆启动过程自身零账本，一旦初始化会话跨日 / SessionEnd，Step 1 只能靠下一会话次日补记（即本次 KDevSec 经历的情况）。

**与 KDevSec §1.2 Step 1 污染样本的关系**：不是独立症状，而是**同一症状的上游触发器**。补"Step 完成闸门"硬规能堵住 Step N 漏采，但堵不住"Step 1 根本没被创建"这一步——因为闸门只在 Step 条目写出后才生效，对"从未被写"的 Step 无效。

**改进方向（主文档 §5.1 补充）**：
- SKILL.md 初始化章节显式加一条：**"骨架建好 + Q-001 答完的瞬间，立刻把初始化本身记为 Step 1，并走完公布→问→锁定四步"**
- 可作为 5.1 第 4 条（Step 定义脱离状态机）的附加条款："工作单元包含 kdev-memory 初始化自身"

### 9.2 机制 2：SessionEnd WARN 文件的"变更快照"噪声

本次 `.kdev/memory/WARN-未记录-2026-04-22.md` 列出的工作区变更快照除了本会话 AI 产出（`.kdev/memory/*` + `CLAUDE.md` 的新增）之外，还混入了 **5 个 `docs/workflow/*.md` 的删除项**——这些是**用户在本 AI 会话前就已做出的未提交变更**（可从本会话初始 `gitStatus` 快照验证）。

**问题**：AI 补记时无法仅凭 WARN 快照判断"这 5 个删除是谁的工作、对应哪个 Step"——它们不属于 Step 1（初始化），但出现在 Step 1 的补记快照里，容易诱导 AI 把本属于用户的历史工作错记为 AI 的 Step。

**实际处理**：本次 AI 识别到删除项不属于本会话 AI 产出，暂不补记，留待与用户确认后按"用户工作"或"独立 Step 0"归档。但这种识别依赖 AI 自己保留了初始 `gitStatus` 快照——**如果跨会话 resume 丢失了该上下文，AI 会错记**。

**改进方向**：
- SessionEnd hook 生成 WARN 时记录**本会话 AI 的文件变更范围**（通过 PostToolUse hook 累计 Write/Edit 的路径），而不是无差别 `git status`
- 或在 WARN 模板里把变更分两段："本会话 AI 变更" vs "会话开始前已存在的未提交变更"

### 9.3 机制 3：跨日/跨会话汇总兜底的实际失效路径

主文档 §4.5 列了 Stop hook 的跨日检测（"跨日期漏汇总"），并提示该兜底"跨天会话 + SessionEnd hook 兜底未生效"时会漏。本次 KDevSec 场景提供了具体失效链：

```
2026-04-21 18:59  Step 1 完成（但未写到执行日志.md）
2026-04-21 19:xx  会话 idle（未自然关闭）
2026-04-21 → 04-22 跨日切换（Stop hook 的"跨日期漏汇总"检测未触发——
              因为当时执行日志本身就空，没有 04-21 日期可被"漏汇总"）
2026-04-22 xx:xx  SessionEnd hook 触发（客户端关闭/切项目）
              → 生成 WARN-未记录-2026-04-22.md（兜底到位）
2026-04-22 新会话  SessionStart brief 提示 WARN 存在（兜底到位）
              → AI 进入会话但用户直接布置新任务（项目背景介绍）
              → AI 按"用户任务优先"原则接手新任务，先未处理 WARN
2026-04-22 用户主动问"昨天的汇总还没记录？" → AI 补记（本次触发）
```

**关键失效点**：
1. **Stop hook 跨日期漏汇总依赖"执行日志有昨日条目但无对应汇总"**——如果执行日志今日（当时即昨日）全空，它扫不到任何日期，不会报警
2. **SessionStart brief 虽然列了 WARN，但未建立"先处理 WARN 再接新任务"的强制语义**——CLAUDE.md 写了"优先处理不跳过"，但当用户**同时**给新任务时模型会优先响应用户，WARN 被推后
3. **跨会话 resume 时模型默认接上次上下文**，容易遗忘"昨天是昨天，今天是今天"的日期语义切换——本次是被用户提醒才意识到

**改进方向**：
- Stop hook 的"跨日期漏汇总"检测逻辑补一条"昨日有文件层面变更（git 可验）但执行日志昨日空" → 也报警
- SessionStart brief 注入时，把 WARN/欠评 Step 项从"⚠️ 提示"升级为"🔴 must-handle，在响应用户第一轮新任务前先处理或声明延后"
- CLAUDE.md 触发规则段里"看到 WARN 先处理"那句加一层明示："**即使用户同一消息里布置了新任务**，也要先向用户确认是先处理 WARN 还是先做新任务，不要默认吞 WARN"

### 9.4 与主文档 §6 盲区列表的映射

| 本节观察 | 对应主文档盲区 | 关系 |
|---|---|---|
| 9.1 初始化自举盲区 | §6.5 Step 粒度绑状态机 | 延伸：Step 粒度不只被状态机绑架，也被"业务 vs 元动作"心智模型绑架 |
| 9.2 WARN 快照噪声 | §6.4 hook 只扫文件层面不扫语义层面 | 同源：hook 的数据粒度不够细 |
| 9.3 跨日兜底失效链 | §6.4 + §4.5 | 补充：具体失效路径 + 改进方向三点 |

### 9.5 本节不改动的部分

- 主文档 §5 行动清单的 P0/P1/P2 分级**不动**：本节提出的改进方向可在 skill v0.5.1 或 v0.6 纳入，不抢 v0.5.0 P0 优先级
- 主文档 §1~§8 的评估结论**不动**：KDevSec 规则层命中率 0/8 + 行为层 1.5/8 的数据仍然准确；本节是对该结论的机制延伸，不是修正

