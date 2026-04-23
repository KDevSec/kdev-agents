# iter-8 notes：v0.6.0 候选——「使用的 skill」事实字段 + Step 粒度指引

**日期**：2026-04-24
**目的**：discriminating eval 回答"事实层加「使用的 skill」字段是否有效？"
**scope 定义源**：[`docs/skills/kdev-memory/dev-notes/2026-04-22-skill使用记录与体验评分维度缺口.md`](../../../../../docs/skills/kdev-memory/dev-notes/2026-04-22-skill使用记录与体验评分维度缺口.md)（方案 A）
**附带 scope**：Step 粒度指引（三停顿信号）+ todos 跟随记约定（都放 references，不进 SKILL.md 主文）

---

## 结果速览

| config | pass rate | tokens | tool_uses | 结论 |
|---|---|---|---|---|
| baseline（v0.5.1） | 7/11 (≈64%) | 50116 | 18 | fail 3 项 + partial 1 项，全部指向「schema 缺字段」这一根因 |
| with_field（v0.6.0 候选） | **11/11 (100%)** | 50712 | 11 | 零 fail，完全符合设计预期 |

**决策**：合入。经济性分析见 §3。

---

## 1. 改动范围

### 1.1 SKILL.md 主文（每次触发加载成本）

- L68 闸门字段枚举：加「使用的 skill」一词（**+0 行**，同行扩）
- L149 速览段 §3：扩括号加粒度 anchor + 「使用的 skill」（**+0-1 行**，主要是单行重写）
- **主文净增：+1 行**（287 → 286，实际从 grep -c 看功能表达更清晰）

### 1.2 references/六类记录-schema.md（按需 Read，不进每次加载）

- §3 字段示例加 `- 使用的 skill：[...]`
- §3 新增「使用的 skill 字段语义」段（~10 行）：N/A / 无 / 硬规 / 用途
- §3 新增「Step 粒度：自然停顿点」段（~20 行）：三信号 + 三映射 + 反模式
- §3 新增「闸门触发时机」一段（~3 行）：看三个停顿信号
- §7 body 示例加「进行中 Step 的 todos 分解」段（~8 行）
- §7 「更新时机」列表加一条：TodoWrite 3+ 条时落 body；Step 完成时清空
- **references 净增：+44 行**（268 → 311）

---

## 2. 为什么 baseline 会 fail

baseline 的 schema（v0.5.1）执行事实段只列 4 字段：工具调用 / 报错 / 绕路 / token 消耗感。**没有「使用的 skill」字段**。

baseline subagent **忠实遵循 schema**——它没有凭空加字段，而是把 skill 名塞到「执行」**叙述段**里：

```
### 执行
- 用 bmad-create-architecture 出架构草案（指数退避 + 死信 + 幂等 key）
- 用 subagent-driven 起了 3 个并行 subagent 实现
```

这是 skill 行为正确，但 **schema 层的缺口**导致信息降级：
- 结构化查询不可能（"用了哪些 skill"变成 grep 任务）
- 跨 Step 聚合分析无锚点
- Step 53（纯对话驱动）只能在「执行」段写一行"未触发任何 skill"自由文本

baseline subagent **主动识别了这个局限**：

> "结构化查询视角下这两个 skill 的使用事实**不可见**，只能靠叙述文本 grep。"

这是方案 A 存在价值的强证据——不是 skill 没做好，是 schema 不让它做好。

---

## 3. 经济性分析（iter-7 框架）

跟 iter-7 不同：iter-7 是 **behavior 等价 + 成本下降**（Step 完成闸门章节），这次是 **behavior 质量提升**。

| 维度 | 成本 | 收益 |
|---|---|---|
| SKILL.md 主文 | +1 行净（每次触发 ~+25 token 加载） | 暴露字段存在 + 粒度 anchor |
| references 增量 | +44 行（按需 Read，零每次成本） | 完整字段语义 + N/A 规则 + Step 粒度指引 |
| 一次性 | 文档写作 + 1 轮 eval 验证 | 结构化落盘 skill 信号 → 跨 Step 聚合可行 |

**一次性文档成本（+1 主文 + 44 reference）vs 每次触发获得结构化数据**——长期 ROI 明显正。和 iter-7 同样的判断框架：一次性成本 ≤ 每次触发的长期收益。**合入 no-brainer**。

---

## 4. 额外发现

### 4.1 with_field subagent 的"补录感受褪色"备注

with_field subagent 在 Step 52 评分差异分析段自发加了：

> "本 Step 用户评分属**补录**，感受已有一定褪色，评分绝对值可信度略低于实时采集。"

这是 reference 的"感受会随时间褪色"一句被 skill 内化后的自然输出——**超预期的诚信**，说明 with_field schema 不只在字段层有效，在 skill 整体诚信文化上也保留了 baseline 的优点。

### 4.2 subagent 准确区分 N/A vs 无

with_field subagent 在 Step 53 引用 reference §3 字段语义定义：

> "用户原话：'纯对话驱动，全程没触发任何 skill'——精确落在 N/A 语义定义里"
> "区分于'无'：后者语义是'本该触发但没触发'（异常信号）。这里非异常。"

这是字段语义设计的意图被精准消费的证据。方案 A 的"N/A vs 无"区分不是过度设计。

### 4.3 tool_use -7 意外节省

with_field 的 tool_uses 是 11，baseline 是 18。差 -7。推测：schema 清晰后 subagent 一次定位到 references §3 就够，不用反复翻找。类似 iter-7 的"schema 显式化降低 tool use"现象。

---

## 5. 和 iter-7 的关系

- iter-7：SKILL.md 加 Step 完成闸门章节（+22 行），一次性成本换每次触发 -12k token
- iter-8：SKILL.md +1 行 + references +44 行，一次性成本换 behavior 质量提升（64% → 100%）

两次都是同一方法论：**一次性文档改动 vs 每次触发收益**的经济性决断。iter-8 成本更低（主文只 +1 行）、收益形态不同（不是省 token 而是加能力），但 ROI 方向一致。

---

## 6. 跟方案 B 的对照（决策回顾）

dev-note 里曾讨论方案 B（加 skill 体验感评分维度）。session 决策后采方案 A（单评分 + 事实层）。本次 iter-8 验证方案 A 的有效性：

- 用户"接口对齐花了点时间"负面文本被顺畅度 4/5 + 用户评价自由文本完整捕获
- 不需要独立"skill 体验感 N/5"维度——skill 正/负贡献自然融进顺畅度
- 跨 Step 按 skill 聚合分析靠事实层字段 + 单一评分维度已经足够

**方案 A 验证 PASS**，方案 B 无必要，dev-note 决策不反转。

---

## 7. 未纳入本 iter 的候选

- PostToolUse matcher=TodoWrite hook（自动在 phase 末端提醒闸门）：留 v0.7.x 观察手动约定跑 2 周的痛点
- 跨 Step "skill 体感"聚合分析召唤词（"分析 skill 体感 / skill 质量盘点"）：留 v0.7.x
- 多会话同项目编号冲突检测：留 v0.7.x（现在靠文档约定 + git 原生处理）

---

## 8. 相关文件

- 改动：[`plugins/kdev-memory/skills/kdev-memory/SKILL.md`](../../../skills/kdev-memory/SKILL.md)
- 改动：[`plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`](../../../skills/kdev-memory/references/六类记录-schema.md)
- fixture：[`plugins/kdev-memory/evals/fixtures/skill-quality/eval-11-skill-used-field/`](../../fixtures/skill-quality/eval-11-skill-used-field/)
- dev-note 源：[`docs/skills/kdev-memory/dev-notes/2026-04-22-skill使用记录与体验评分维度缺口.md`](../../../../../docs/skills/kdev-memory/dev-notes/2026-04-22-skill使用记录与体验评分维度缺口.md)
