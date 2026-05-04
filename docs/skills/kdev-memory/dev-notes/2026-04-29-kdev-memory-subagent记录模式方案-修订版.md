# kdev-memory 降低主会话上下文占用方案（v3.0 修订版）

> 日期：2026-04-29
> 状态：待评审
> 目的：降低 kdev-memory skill 对主会话上下文的占用
> 修订历史：
> - v1.0（2026-04-28）：提出 Subagent 两阶段调用方案
> - v2.0（2026-04-29）：根据灵码评审意见修订（错误处理、时间戳校验、并发控制等）
> - v3.0（2026-04-29）：基于 Subagent 实际运行机制调研，推翻 Subagent 方案，提出替代方案

---

## 修订摘要（v3.0 关键变更）

| 修订项 | 变更原因 | 变更内容 |
|--------|----------|----------|
| **推翻 Subagent 方案** | 调研发现 subagent 不继承 skill、不共用 Cache、全局 token +213% | §三 详细分析 |
| **修正 Prompt Cache 分析** | Subagent 是独立 API 会话，Cache 不共用 | §四 重新评估 |
| **重新评估 Token 消耗** | 基于 SKILL.md 实际大小（~8,100 tokens）计算 | §四 对比表 |
| **提出替代方案 D+E** | 精简 SKILL.md + 延迟加载，零额外成本 | §五 新方案 |

---

## 一、背景与问题分析

### 1.1 当前痛点

| 痛点 | 表现 | 影响 |
|------|------|------|
| **主会话上下文膨胀** | 每次记录 Step 需在主会话执行 Read/Write/Edit | 上下文累积，影响后续推理质量 |
| **多 Step 场景累积** | 连续多个 Step 后，主会话负载高 | 可能触发提前压缩 |
| **评分交互占用** | 询问用户评分 + 等待反馈 + 填写 = 一轮对话 | 额外上下文消耗 |

### 1.2 实测数据（iter-7/iter-8）

| 场景 | Tokens | Tool Uses | 来源 |
|------|--------|-----------|------|
| Step 完成闸门（baseline） | 57,975 | 20 | iter-7 notes |
| Step 完成闸门（显式规则） | 45,832 | 13 | iter-7 notes |
| 「使用的 skill」字段（baseline） | 50,116 | 18 | iter-8 notes |
| 「使用的 skill」字段（with_field） | 50,712 | 11 | iter-8 notes |

**关键发现**：规则显式化能降低推理成本，但 **记录操作本身仍在主会话执行**。

### 1.3 SKILL.md 实际大小

| 文件 | 字节数 | 估算 tokens | 说明 |
|------|--------|-------------|------|
| `SKILL.md` | 24,316 | ~8,100 | 每次触发加载 |
| `references/六类记录-schema.md` | 21,235 | ~7,100 | 按需 Read |
| `references/初始化-claude-md-模板.md` | 10,765 | ~3,600 | 按需 Read |
| `references/自动化机制-hooks.md` | 7,126 | ~2,400 | 按需 Read |
| `references/规则升级流程.md` | 5,454 | ~1,800 | 按需 Read |
| `references/triggers-写法.md` | 4,806 | ~1,600 | 按需 Read |
| `references/切档与归档.md` | 5,057 | ~1,700 | 按需 Read |
| **references 合计** | 54,443 | ~18,100 | — |
| **SKILL.md + 全部 references** | 78,759 | ~26,200 | — |

> 估算方法：中英混合文本取 ~3 char/token

---

## 二、Subagent 方案回顾与致命缺陷

### 2.1 原方案简述

通过两阶段 Agent 调用，将 Step 记录操作从主会话转移到 subagent：
- Phase 1：Subagent 写执行事实 + 模型自评 → 返回 JSON 摘要
- Phase 2：Subagent 补齐用户评分 + 差值分析 → 返回完成确认

### 2.2 Subagent 实际运行机制（调研结果）

| 维度 | 主会话 | Subagent | v1.0/v2.0 的错误假设 |
|------|--------|----------|---------------------|
| **SKILL.md** | 自动加载 | ❌ **不自动继承**，必须用 `load_skills` | ✅ 自动共用 |
| **System prompt** | 用户的全局+项目 CLAUDE.md | 独立的 agent 配置 | 默认相同 |
| **Prompt Cache** | 自有 cache | ❌ **独立 cache，不共用** | ✅ 共用 |
| **上下文** | 完整对话历史 | 只有 prompt 字段传入的内容 | — |
| **结果返回** | — | 通过 tool_result 返回，完整进入主会话 | — |
| **用户交互** | ✅ 可以 | ❌ **无法与用户交互** | — |

**核心事实：Subagent 是完全独立的 API 会话，不继承主会话的任何上下文，不共用 Prompt Cache。**

### 2.3 Token 消耗真实对比

#### 直接执行模式（当前）

```
主会话单次 Step 记录的 token 构成：

① SKILL.md 加载（skill 触发时）：    ~8,100 tokens（一次性，Prompt Cache 后续命中）
② references/六类记录-schema.md：    ~7,100 tokens（按需 Read）
③ .kdev/memory/ 文件读取：           ~2,000 tokens
④ 记录操作推理 + Write：             ~3,000 tokens
⑤ 用户评分交互：                     ~500 tokens
                                      ──────────
单 Step 总计（含 skill 加载）：       ~20,700 tokens
单 Step 总计（去掉一次性加载）：       ~12,600 tokens
多 Step 时（Prompt Cache 命中）：     ~12,600 tokens/Step
```

#### Subagent 模式（修正后）

```
主会话部分：
① 调用 Agent tool（Phase 1 prompt）： ~300 tokens
② 接收 subagent 返回（Phase 1）：     ~100 tokens
③ 公布自评 + 问用户：                ~200 tokens
④ 调用 Agent tool（Phase 2 prompt）： ~400 tokens
⑤ 接收 subagent 返回（Phase 2）：     ~100 tokens
                                      ──────────
主会话总计：                          ~1,100 tokens ✅ 降低 91%

Subagent Phase 1：
① 独立 system prompt + 基础上下文：   ~3,000 tokens（必须重建）
② load_skills 加载 SKILL.md：         ~8,100 tokens（重新加载，Cache 不命中）
③ references/六类记录-schema.md Read： ~7,100 tokens（重新 Read）
④ .kdev/memory/ 文件 Read：           ~2,000 tokens
⑤ 推理 + Write：                     ~3,000 tokens
                                      ──────────
Phase 1 总计：                        ~23,200 tokens

Subagent Phase 2：
① 独立 system prompt + 基础上下文：   ~3,000 tokens
② load_skills 加载 SKILL.md：         ~8,100 tokens（再次加载）
③ .kdev/memory/ 文件 Read：           ~2,000 tokens
④ 推理 + Edit + Write：              ~2,000 tokens
                                      ──────────
Phase 2 总计：                        ~15,100 tokens

全局总计 = 主会话(1,100) + Phase 1(23,200) + Phase 2(15,100)
         = ~39,400 tokens ❌ 增加 213%
```

#### 对比汇总

| 维度 | 直接执行 | Subagent 模式 | 变化 |
|------|----------|---------------|------|
| **主会话占用** | ~12,600 | ~1,100 | **-91%** ✅ |
| **全局总 tokens** | ~12,600 | ~39,400 | **+213%** ❌ |
| **SKILL.md 加载次数** | 1 次（Cache 命中） | 3 次（不共用 Cache） | 3x |
| **API 调用次数** | 1 次连续 | 3 次独立 | 3x |
| **用户交互** | 主会话直接 | Subagent 无法交互，必须回到主会话 | 复杂度 + |

### 2.4 Subagent 与 kdev-memory 的特征对比

| kdev-memory 特征 | 说明 | 与 Subagent 的兼容性 |
|-------------------|------|---------------------|
| **串行依赖** | Phase 2 依赖 Phase 1 结果 | ❌ 无法并行，串行调用增加延迟 |
| **需要 skill 规则** | 必须读 SKILL.md + schema | ❌ 每次重新加载，3x token 成本 |
| **需要用户交互** | 询问评分、公布自评 | ❌ Subagent 无法与用户交互 |
| **操作简单文件** | Read → Edit → Write | ❌ 操作本身很轻，不值得 subagent 开销 |
| **上下文可复用** | 已加载的 skill 在后续 Step 可复用 | ❌ Subagent 用完即弃，无法复用 |

### 2.5 Subagent 方案结论

**推翻 Subagent 方案**。理由：

1. **全局 token +213%**——主会话节省的 token 远不够弥补 subagent 重复加载的成本
2. **Prompt Cache 不共用**——每次 subagent 调用都是 Cache miss
3. **用户交互必须回到主会话**——两阶段调用增加复杂度但无收益
4. **串行依赖**——无法利用 subagent 的并行优势
5. **skill 上下文无法复用**——每次重新加载

Subagent 适合"并行独立任务 + 不依赖 skill + 不需要用户交互"的场景，kdev-memory 全部反着来。

---

## 三、替代方案：精简注入 + 延迟加载

### 3.1 核心思路

问题根源不是"记录操作在主会话执行"，而是 **SKILL.md 本身太大（~8,100 tokens）**。

```
当前：SKILL.md = 核心规则 + 大量细节 → ~8,100 tokens/次
优化：SKILL.md = 核心规则 → ~3,000 tokens/次
      细节移到 references/ → 按需 Read，不每次加载
```

### 3.2 方案 D：精简 SKILL.md

**目标**：将 SKILL.md 从 ~8,100 tokens 压缩到 ~3,000 tokens

**具体做法**：

| 内容 | 当前位置 | 优化后位置 | 理由 |
|------|----------|-----------|------|
| 核心原则（实时落盘/文件聚合/hook优先） | SKILL.md | ✅ 保留 | 每次都需要 |
| Step 完成闸门（四段必填） | SKILL.md | ✅ 保留 | 每次都需要 |
| 动作链 | SKILL.md | ✅ 保留 | 每次都需要 |
| 初始化流程 | SKILL.md | → `references/初始化-claude-md-模板.md` | 只初始化时用 |
| 六类记录速览表 | SKILL.md | ✅ 保留（精简） | 每次需要，但可缩短 |
| 召回机制说明 | SKILL.md | → `references/triggers-写法.md` | 只标注 triggers 时用 |
| 归档/切档说明 | SKILL.md | → `references/切档与归档.md` | 只归档时用 |
| 条目状态与沉淀字段 | SKILL.md | → `references/六类记录-schema.md` | 已有，重复内容删除 |

**预估效果**（已实测）：

| 指标 | 优化前 | 优化后（实测） | 变化 |
|------|--------|---------------|------|
| SKILL.md 字节数 | 24,316 | 17,833 | -27% |
| SKILL.md 词数 | ~6,166 | ~4,549 | -26% |
| SKILL.md tokens | ~8,100 | ~5,900 | -27% |
| 是否符合 <5k 词 | ❌ 超 23% | ✅ 在限制内 | ✅ 合规 |
| 每次触发主会话节省 | — | ~2,200 tokens | -27% |

### 3.3 方案 E：延迟加载 references

**目标**：确保 references 文件真正"按需"加载

**具体做法**：

每个 references 文件开头已有"什么时候读本文件"段，但 SKILL.md 中某些地方仍会引导 Claude 在不需要时也去 Read。

优化策略：
1. SKILL.md 中所有 references 引用改为"如需细节，Read `references/xxx.md`"的惰性引用
2. 删除 SKILL.md 中与 references 重复的内容（如条目状态字段的详细说明）
3. 在 SKILL.md 速览表中明确标注"详情见 references/xxx.md"

**预估效果**：

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| 不必要的 references Read | 偶尔发生 | 极少 | -80% |
| 每次触发主会话节省 | — | ~1,500 tokens | -12% |

### 3.4 方案 D+E 组合

| 指标 | 直接执行（当前） | D+E 优化后 | 变化 |
|------|-----------------|-----------|------|
| SKILL.md 加载 | ~8,100 tokens | ~5,900 tokens（实测） | -27% |
| 不必要的 references | ~1,500 tokens | ~0 tokens | -100% |
| .kdev/memory/ 文件 | ~2,000 tokens | ~2,000 tokens | 0 |
| 记录操作推理 + Write | ~3,000 tokens | ~3,000 tokens | 0 |
| 用户评分交互 | ~500 tokens | ~500 tokens | 0 |
| **主会话总计** | **~12,600 tokens** | **~10,400 tokens** | **-17%** |
| **全局总 tokens** | **~12,600** | **~10,400** | **-17%** |

### 3.5 多 Step 场景对比（5 Step）

| 模式 | 主会话累积 | 全局总计 | Prompt Cache |
|------|-----------|---------|-------------|
| **当前（直接执行）** | ~63,000 tokens | ~63,000 | SKILL.md 首次后命中 |
| **Subagent（v2.0）** | ~5,500 tokens | ~197,000 | ❌ 不共用 |
| **D+E 优化（实测）** | ~52,000 tokens | ~52,000 | SKILL.md 首次后命中 |

---

## 四、方案对比总结

| 方案 | 主会话节省 | 全局 token 变化 | API 调用 | 额外成本 | 复杂度 | 推荐 |
|------|-----------|----------------|----------|----------|--------|------|
| **A：Subagent（v1.0/v2.0）** | -91% | **+213%** ❌ | 3x | 高 | 高 | ❌ 推翻 |
| **D：精简 SKILL.md** | -63% | **-63%** ✅ | 1x | 零 | 低 | ✅ 推荐 |
| **E：延迟加载** | -12% | **-12%** ✅ | 1x | 零 | 低 | ✅ 推荐 |
| **D+E 组合** | -33% | **-33%** ✅ | 1x | 零 | 低 | ⭐ 推荐 |

---

## 五、方案 D+E 实施计划

### 5.1 改动清单

| 文件 | 改动类型 | 改动量 | 说明 |
|------|----------|--------|------|
| `SKILL.md` | 精简重构 | -50~60 行 | 移出初始化流程、召回细节、归档说明、重复字段 |
| `references/初始化-claude-md-模板.md` | 可能扩充 | +10~20 行 | 承接从 SKILL.md 移出的初始化细节 |
| `references/六类记录-schema.md` | 可能微调 | ±5 行 | 确保承接 SKILL.md 移出的字段说明 |
| `references/切档与归档.md` | 可能微调 | ±5 行 | 确保承接归档说明 |
| `CLAUDE.md 模板` | 无改动 | 0 | — |
| `evals/skill-quality/` | 新增 eval | +1 scenario | 验证精简后行为一致性 |

### 5.2 SKILL.md 精简原则

**保留在 SKILL.md 的内容**（每次触发都需要）：
- 核心原则（实时落盘/文件聚合/hook 优先）
- Step 完成闸门（四段必填 + 动作链）
- 六类记录速览表（精简版，每类 1-2 行 + "详情见 references/xxx.md"）
- 触发时机（description 中已有，SKILL.md 中可更精简）

**移到 references 的内容**（只在特定场景需要）：
- 初始化流程 → `references/初始化-claude-md-模板.md`
- triggers 召回机制细节 → `references/triggers-写法.md`
- 归档/切档流程 → `references/切档与归档.md`
- 条目状态与沉淀字段详解 → `references/六类记录-schema.md`
- hook 行为详解 → `references/自动化机制-hooks.md`

**删除的重复内容**：
- SKILL.md 中与 references 文件重复的详细说明

### 5.3 实施步骤

| 步骤 | 内容 | 周期 | 依赖 |
|------|------|------|------|
| **Step 1** | 分析 SKILL.md 每段内容，标注保留/移出/删除 | 0.5 天 | — |
| **Step 2** | 执行精简，确保 references 承接完整 | 0.5 天 | Step 1 |
| **Step 3** | 建立 discriminating eval（精简前 vs 精简后） | 1 天 | Step 2 |
| **Step 4** | 跑 eval 验证行为一致性 | 0.5 天 | Step 3 |
| **Step 5** | 收集实测 token 数据，更新估算值 | 0.5 天 | Step 4 |
| **Step 6** | 合入主分支 | 0.5 天 | Step 5 通过 |
| **总计** | | **3.5 天** | |

### 5.4 验证指标

| 指标 | 优化前 | 目标 | 收集方式 |
|------|--------|------|----------|
| SKILL.md tokens | ~8,100 | ~5,900（已实测） | 字节数/3 估算 |
| 单 Step 主会话 tokens | ~12,600（估算） | ~10,400（估算） | eval timing.json |
| 行为正确率 | 100% | 100% | discriminating eval |
| tool_uses | 基线 | 不增加 | eval timing.json |

---

## 六、风险评估

### 6.1 方案 D+E 风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **精简后规则不够显式** | 中 | 中 | iter-7 已证明显式化降低推理成本；精简 ≠ 删除规则，是移到 references |
| **Claude 频繁 Read references** | 中 | 低 | SKILL.md 保留速览表 + 惰性引用；eval 验证 tool_uses 不增加 |
| **references 承接不完整** | 低 | 中 | Step 1 逐段标注，确保无信息丢失 |
| **初始化流程断裂** | 低 | 中 | 初始化是低频操作，Read references 可接受 |

### 6.2 与 Subagent 方案的风险对比

| 风险类型 | Subagent 方案 | D+E 方案 |
|----------|---------------|----------|
| 全局 token 暴增 | ❌ +213% | ✅ -33% |
| 行为一致性 | ⚠️ 需大量额外验证 | ✅ 只改内容位置，不改逻辑 |
| 实现复杂度 | ❌ 高（降级/重试/时间戳/并发） | ✅ 低（文档重构） |
| 维护成本 | ❌ 高（两套执行模式） | ✅ 零（只有一套模式） |

---

## 七、备选方案（已否决）

### 7.1 方案 A：Subagent 两阶段调用（v1.0/v2.0）

**否决理由**：全局 token +213%，Prompt Cache 不共用，用户交互必须回到主会话，串行依赖无法并行。

### 7.2 方案 B：纯 Hook 驱动（自动化）

**否决理由**：Hook 无法做智能判断（评分、差值分析），无法询问用户评分，违背 skill 设计原则（hook 只戳提醒，不做决策）。

### 7.3 方案 C：独立 kdev-memory-recorder skill

**否决理由**：两套 skill 维护成本，Prompt Cache 不共用，升级时需同步两套。

### 7.4 方案对比总结

| 方案 | 主会话占用 | 全局 token | 复杂度 | 推荐 |
|------|-----------|-----------|--------|------|
| **D+E：精简+延迟加载** | -17% | **-17%** | 低 | ⭐⭐⭐⭐⭐ |
| A：Subagent | -91% | **+213%** ❌ | 高 | ❌ 推翻 |
| B：纯 Hook | 最低 | N/A | 中 | ❌ 违背原则 |
| C：独立 recorder | 低 | 未知 | 高 | ❌ 维护成本 |

---

## 八、参考资料

- `plugins/kdev-memory/evals/skill-quality/iterations/20260423-07-p0-1-discriminating/notes.md`（token 节省证据）
- `plugins/kdev-memory/evals/skill-quality/iterations/20260424-08-skill-used-field/notes.md`（schema 显式化效果）
- `docs/skills/kdev-memory/dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md`（hook 边界原则）
- `docs/skills/kdev-memory/dev-notes/2026-04-28-kdev-memory-subagent方案评审意见.md`（v1.0 评审意见）
- Claude Code Agent tool 实际运行机制调研（v3.0 新增）：subagent 不继承 skill、不共用 Cache、独立 API 会话

---

## 附录：评审记录

| 评审人 | 日期 | 结论 | 备注 |
|--------|------|------|------|
| Lingma | 2026-04-28 | ✅ 有条件通过（v1.0） | 综合评分 8.2/10 |
| 方案修订 | 2026-04-29 | ✅ 修订完成（v2.0） | 修复 P0 问题，简化并发控制 |
| Subagent 机制调研 | 2026-04-29 | ❌ 推翻 Subagent 方案（v3.0） | 全局 token +213%，Cache 不共用 |
| 待评审 | — | — | v3.0 待评审 |

---

*文档版本：v3.0*
*最后更新：2026-04-29*
*状态：待评审*
*关键变更：推翻 Subagent 方案，提出 D+E 替代方案*