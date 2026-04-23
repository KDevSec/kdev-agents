# 2026-04-24 TodoWrite 跨会话接力缺口 + 三档方案

**提出日期**：2026-04-24
**提出语境**：kdev-memory v0.6.0 scope 讨论中，用户追问"CC 列了很多 Todos 时，是否应该记录下来，否则后面压缩或中间打断就没了"
**相关 skill**：kdev-memory（v0.6.0 及以后）
**优先级建议**：P2（低频痛点；先做文档级约定观察 2 周再决定是否升级成 hook）

---

## 背景

Claude Code 的 TodoWrite 工具维护一份 session 内的任务列表。用户反馈一个实际场景：

> 有个大的需求，拆分了 20 个 todo，分为 4 个 phase 来完成。这时候可能每个 phase 停下来打个分比较合适，不适合每个 todo 停下来，也不是所有 phase 完成了再停下来。

核心问题可以拆成两半：

1. **Step 粒度**：phase、todo、整需求——Step 闸门应该在哪个粒度触发？（这半已在 v0.6.0 解决，见 [开发历程.md §4.6](../开发历程.md) 和 [六类记录-schema.md §3](../../../../plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md)）
2. **TodoWrite 数据持久化**：todos 列表本身会不会丢？丢了之后跨会话接力怎么办？**这份 dev-note 只讨论第二半**

---

## 真实痛点频率判定

问题来源场景（按频率倒序）：

| 场景 | TodoWrite 丢失概率 | 频率估计 |
|---|---|---|
| 跨 session 跳（用户关会话、明天再来） | 100% | 高（每天） |
| 长时间空转 + 压缩（5 min 缓存窗口外） | ~50%（context 粗压缩会损信号） | 中（每周几次） |
| 崩溃 / `/clear` / 断电 | 100% | 低（每月几次） |

**真实痛点**只有场景 1——当前状态.md body 要求"描述当前正在做什么、预期下一步"，但**粒度过粗**。它回答"当前 Step 是啥"，不回答"当前 Step 已做 a/b/c、剩 d/e"。

---

## 三档方案横比

### 方案 ①：不动（依赖 CC 自带保护）

- TodoWrite 存在 conversation context 里，压缩大多数保得住（5 min 缓存窗）
- 当前状态.md body 自由文本位置已经有"下一步计划"的说明空间
- **成本**：零
- **代价**：跨 session 接力时 todos 必然归零；用户每次新会话要重新拆解一次

### 方案 ②：当前状态.md body 加「进行中 Step 的 todos 分解」段（约定级）

- skill 约定：TodoWrite 首次 emit 3+ todos 时落这段
- 每次 todo 状态变化（完成 / 新增）顺手同步（和 `current_step` / `last_updated` 一起改，不单独起操作）
- Step 完成闸门过了 → 清空这段（可选：折叠进 Step 条目"执行"段留轨迹）
- **成本**：references 文档 +~8 行（一次性）+ 每次 TodoWrite 变化时 skill 多 2-3 行 prompt 负担
- **收益**：跨 session 接力时新会话能从 body 回读"当前 Step 已完成 a/b/c、剩 d/e"

### 方案 ③：PostToolUse matcher=TodoWrite hook（自动化）

- hook 把 TodoWrite list dump 到 `.kdev/memory/状态/todos-当前.md`
- Step 完成闸门触发时清空 / 归档到 Step 条目
- **成本**：hook 代码 ~50 行 + 每次 TodoWrite 都写文件（kdev-memory 类项目每天 20+ 次）
- **收益**：精准结构化，零遗漏

---

## 2026-04-24 session 决策：方案 ②，不做 ③

### 经济性分析（iter-7 框架应用）

- 方案 ③ 代码成本是**每次 TodoWrite 都写文件**——kdev-memory 类项目每天 20+ 次 = 每次成本
- 真实"跨 session 接力丢 todo"的痛点频率：周级（几次 / 周）——低频
- **高频代价换低频痛点 ROI 差**
- 方案 ② 代码成本**零**（只增加 skill 的一条自律约定）+ references 一次性 +~8 行文档成本

### 选择方案 ② 的具体落地（已在 v0.6.0 落地）

1. references/六类记录-schema.md §7「当前状态.md」body 示例加段：

   ```markdown
   ## 进行中 Step 的 todos 分解（可选，仅当前 Step 使用）

   Step 20（v0.6.0 skill 字段）分解：
   - [x] 改 references §3 字段模板
   - [x] 改 SKILL.md 速览段
   - [ ] 造 eval-11 fixture
   - [ ] 跑 discriminating eval
   - [ ] bump plugin.json + CHANGELOG
   ```

2. §7「更新时机」列表加一条：

   > **TodoWrite 首次 emit 3+ todos 时** → 落 body 的「进行中 Step 的 todos 分解」段；每次 todo 状态变化（完成/新增）顺手同步。用于跨 session 接力时回读"当前 Step 做到哪了"。单个 todo completed **不**触发 Step 闸门——闸门看三个停顿信号（见 §3）

3. §3「更新时机」关联："完成一个 Step → 清空 body 的「进行中 Step 的 todos 分解」段（或折叠进 Step 条目的"执行"段留个轨迹）"

---

## 留给 v0.7.x 的观察窗

方案 ② 跑 2-4 周后，看实际接力场景：

- 如果手动同步 todos 负担大 / 忘记同步频繁 → 升级方案 ③（PostToolUse hook 自动化）
- 如果跨 session 接力频率比预估高很多（每天 3+ 次以上）→ 升级方案 ③
- 如果手动方案工作良好、用户不觉得烦 → 维持方案 ② 作为长期方案

观察窗结束后在 v0.7.x 做二次决策，那时有真实数据不靠猜。

---

## 方法论启示

1. **新功能的"是否要做"和"怎么做"是两个问题**：本次 dev-note 回答"怎么做"，但"**是否要做**"的答案是"先做轻版本观察，别一上来写 hook"
2. **先做文档约定再做代码**：iter-7 的经济性框架第一次应用；第二次应用本来就该想到这点
3. **用户追问把隐藏场景挤出来**：用户不会直接说"TodoWrite 会丢数据"，而是先问"是不是要记"——AI 要主动把场景展开，然后再讨论方案
4. **低频痛点不值得高频代价**：20 次 / 天 × 几毫秒 = 每天秒级累计；换每周几次的"新会话回读 todos"便利 ROI 差
