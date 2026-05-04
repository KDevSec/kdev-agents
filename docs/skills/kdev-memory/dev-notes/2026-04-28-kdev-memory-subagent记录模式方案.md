# kdev-memory Subagent 记录模式方案

> 日期：2026-04-28
> 状态：待评审
> 目的：在现有 kdev-memory skill 中增加可选的 Subagent 记录模式，降低主会话上下文占用

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

### 1.3 问题本质

```
当前模式：
主会话 = 工作 + 记录 + 交互
        ↑ 所有操作都在同一个上下文

期望模式：
主会话 = 工作 + 交互（轻量）
Subagent = 记录（独立上下文，用完即弃）
```

---

## 二、改造目标

### 2.1 核心目标

| 目标 | 指标 | 当前 | 期望 |
|------|------|------|------|
| **降低主会话上下文占用** | 主会话 tokens/Step | ~500-800 | ~100 |
| **保持 Prompt Cache 命中** | Cache 命中率 | N/A | 高（共用 SKILL.md） |
| **零额外 skill 维护** | skill 文件数 | 1 | 1（改造而非新建） |
| **行为一致性** | Step 四段完整性 | 100% | 100% |

### 2.2 不改变的内容

- Step 四段必填 schema（执行事实 + 模型自评 + 用户评分 + 差值分析）
- triggers 召回机制
- hooks 行为（Stop/SessionStart/PreCompact 等）
- `.kdev/memory/` 目录结构
- 文件格式规范

---

## 三、方案设计

### 3.1 架构对比

#### 当前模式（直接执行）

```
┌─────────────────────────────────────────────────────────────────┐
│                     主会话上下文                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Step 完成                                                       │
│      ↓                                                          │
│  Read 当前状态.md ──────────────────────────────┐               │
│  Read 执行日志.md ──────────────────────────────┤               │
│  Write 执行事实段 + 模型自评 ────────────────────┤ ~500-800     │
│      ↓                                          │ tokens        │
│  公布自评给用户 ────────────────────────────────┤               │
│      ↓                                          │               │
│  问用户评分（等待反馈）─────────────────────────┤               │
│      ↓                                          │               │
│  Edit 用户评分段 ───────────────────────────────┤               │
│  Write/Edit 差值分析 ───────────────────────────┤               │
│  Edit 当前状态.md（更新 current_step）───────────┘               │
│                                                                 │
│  问题：所有操作在主会话上下文累积                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 新增模式（Subagent 记录）

```
┌──────────────────────────┐     ┌─────────────────────────────────┐
│     主会话上下文（轻量）   │     │     Subagent 上下文（独立）      │
├──────────────────────────┤     ├─────────────────────────────────┤
│                          │     │                                 │
│  Step 完成               │     │  Phase 1（写执行事实+自评）       │
│      ↓                   │ ──→ │  Read 当前状态.md                │
│  Agent(Phase 1) ─────────│     │  Read 执行日志.md                │
│      ↓                   │     │  Write 执行事实段 + 模型自评      │
│  收到自评结果 ───────────│ ←── │  返回 JSON                      │
│      ↓                   │     │      {step, score, timestamp}   │
│  公布自评给用户          │     │                                 │
│      ↓                   │     │  ─────────────────────────────  │
│  问用户评分              │     │                                 │
│      ↓                   │     │  Phase 2（补齐用户评分+差值）     │
│  Agent(Phase 2) ─────────│ ──→ │  Read 执行日志.md（定位 Step）   │
│      ↓                   │     │  Edit 用户评分段                │
│  收到完成确认 ───────────│ ←── │  Write/Edit 差值分析            │
│                          │     │  若差值≥2 → Write 改进建议.md   │
│  ~100 tokens             │     │  Edit 当前状态.md               │
│  主会话轻量              │     │  返回 JSON: {complete, gap}     │
│                          │     │                                 │
│                          │     │  ~400 tokens（用完即弃）         │
│                          │     │                                 │
└──────────────────────────┘     └─────────────────────────────────┘
```

### 3.2 具体调用流程

#### Phase 1：写执行事实 + 模型自评

```javascript
Agent({
  subagent_type: "general-purpose",
  prompt: `
    kdev-memory: 记录 Step 完成（Phase 1）

    项目: ${project_name}
    Step 编号: ${step_number}
    任务描述: ${task_description}
    工具调用次数: ${tool_calls_estimate}
    报错次数: ${error_count}
    绕路次数: ${detour_count}
    token 消耗感: ${token_feeling}（低/中/高/偏高）
    使用的 skill: ${skills_used}

    请按 SKILL.md 规范执行：
    1. Read .kdev/memory/当前状态.md 获取 current_step
    2. Read .kdev/memory/执行日志.md 确认最近条目格式
    3. Write 执行日志.md：追加「## Step ${step_number}」条目
       - 执行事实段（上述参数）
       - 模型自评段（含完成时间戳、顺畅度自评、扣分项）
    4. 返回 JSON（不要返回完整条目内容）：
       {
         "step_number": ${step_number},
         "self_score": ${1-5},
         "timestamp": "${YYYY-MM-DD HH:MM}",
         "deduct_reason": "${扣分项内容}"
       }
  `,
  description: "kdev-memory Phase 1: 写执行事实+模型自评"
})
```

#### Phase 2：补齐用户评分 + 差值分析

```javascript
Agent({
  subagent_type: "general-purpose",
  prompt: `
    kdev-memory: 补齐用户评分（Phase 2）

    Step 编号: ${step_number}
    模型自评: ${self_score} @ ${model_timestamp}
    用户评分: ${user_score} @ ${user_timestamp}
    用户评价: "${user_comment}"

    请按 SKILL.md 规范执行：
    1. Read .kdev/memory/执行日志.md 定位 Step ${step_number} 条目
    2. Edit 补齐用户评分段（完成时间戳 + 顺畅度 + 评价）
    3. 计算差值，生成评分差异分析段，Edit 写入
    4. 若差值 ≥ 2 或用户评价含负面关键词：
       Write .kdev/memory/改进建议.md 开新 R-NNN 条目
    5. Edit .kdev/memory/当前状态.md：
       - 更新 current_step: ${step_number}
       - 更新 last_updated: ${today}
    6. 返回 JSON：
       {
         "step_number": ${step_number},
         "complete": true,
         "gap": ${user_score - self_score},
         "r_number": ${若有R-NNN则返回，否则null}
       }
  `,
  description: "kdev-memory Phase 2: 补齐用户评分+差值分析"
})
```

### 3.3 SKILL.md 改造内容

**新增章节位置**：在 `§ Step 完成硬闸门` 的「动作链」小节后

```markdown
### 可选：Subagent 记录模式（降低主会话上下文占用）

当主会话上下文压力较高时，可通过 subagent 执行记录操作，保持主会话轻量。

#### 适用场景

| 场景 | 推荐模式 | 理由 |
|------|----------|------|
| 主会话上下文接近上限 | Subagent | 避免触发提前压缩 |
| 多 Step 连续执行 | Subagent | 减少累积占用 |
| 批量补录历史 Step | Subagent | 主会话只做交互 |
| 单 Step + 上下文充裕 | 直接执行 | 更简单，无额外调用 |

#### 两阶段调用

**Phase 1（写执行事实 + 模型自评）**：
- 主会话调用 Agent，传入 Step 概要信息
- Subagent 执行 Read + Write，返回自评摘要（JSON）
- 主会话收到 ~50 token 的返回，公布给用户

**Phase 2（补齐用户评分 + 差值分析）**：
- 主会话收集用户评分后，调用 Agent 补齐
- Subagent 执行 Read + Edit + Write（含 R-NNN 判断）
- 主会话收到 ~50 token 的完成确认

#### Prompt Cache 共用

主会话和 subagent 读取同一个 SKILL.md（skill 内容自动注入），因此：
- **Prompt Cache 可以共用**
- 不需要维护两套 skill
- 升级改造而非新建

#### 行为一致性保证

Subagent 模式下：
- Step 四段必填完整性：✅ 不变
- 锁定铁规（用户时分戳 > 自评）：✅ 不变
- triggers 标注：✅ 不变
- R-NNN 触发条件：✅ 不变

唯一差异：**执行载体从主会话变为 subagent**，schema 和规则完全相同。
```

---

## 四、Token 消耗对比分析

### 4.1 单 Step 场景

| 操作 | 直接执行（主会话） | Subagent 模式 | 差值 |
|------|-------------------|---------------|------|
| Read 当前状态.md | ~100 tokens | Subagent 内 | 0 |
| Read 执行日志.md | ~150 tokens | Subagent 内 | 0 |
| Write 执行事实+自评 | ~200 tokens | Subagent 内 | 0 |
| 公布 + 问用户 | ~100 tokens | ~100 tokens | 0 |
| Edit 用户评分段 | ~100 tokens | Subagent 内 | 0 |
| Write/Edit 差值分析 | ~100 tokens | Subagent 内 | 0 |
| **主会话总计** | **~650-800 tokens** | **~100-150 tokens** | **-80%** |
| **Subagent 总计** | 0 | ~400-500 tokens | +400 |
| **全局总计** | ~650-800 | ~500-650 | **-15~20%** |

### 4.2 多 Step 场景（假设 5 Step）

| 模式 | 主会话累积 | Subagent 累积 | 全局总计 |
|------|-----------|---------------|----------|
| **直接执行** | ~3000-4000 tokens | 0 | ~3000-4000 |
| **Subagent** | ~500-750 tokens | ~2000-2500（独立，用完即弃） | ~2500-3250 |

**关键洞察**：
- 全局 tokens 略省（-15~20%）
- **主会话上下文占用大幅降低**（-80%）——这是核心价值
- Subagent 上下文用完即弃，不影响后续推理

### 4.3 Prompt Cache 命中分析

| 组件 | 直接执行 | Subagent 模式 | Cache 命中 |
|------|----------|---------------|------------|
| SKILL.md | 主会话加载 | 主会话 + subagent 都加载 | ✅ 共用 |
| references/*.md | 按需 Read | Subagent 内按需 Read | ✅ 共用 |
| .kdev/memory/*.md | 主会话 Read | Subagent 内 Read | ⚠️ 可能重复 |

**结论**：SKILL.md 和 references 文件可以共用 Cache，`.kdev/memory/` 文件可能被重复读取（但这是 subagent 的独立成本，不影响主会话）。

---

## 五、风险评估

### 5.1 技术风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **Subagent 调用延迟** | 中 | 低 | 用户评分交互本身就是等待，延迟可接受 |
| **Subagent 执行失败** | 低 | 中 | 主会话收到错误后可 fallback 到直接执行 |
| **两阶段时序错乱** | 低 | 中 | Phase 2 必须在 Phase 1 完成后调用，prompt 显式约束 |
| **Prompt Cache 重复加载** | 中 | 低 | SKILL.md 共用，references 文件按需加载 |

### 5.2 行为一致性风险

| 检查项 | 直接执行 | Subagent | 验证方式 |
|--------|----------|----------|----------|
| Step 四段必填 | ✅ | ✅ | discriminating eval |
| 锁定铁规 | ✅ | ✅ | Phase 1 返回 timestamp，Phase 2 校验 |
| triggers 标注 | ✅ | ✅ | Prompt 显式要求 |
| R-NNN 触发 | ✅ | ✅ | Phase 2 prompt 显式条件判断 |
| 文件格式规范 | ✅ | ✅ | Subagent 读同一个 SKILL.md |

### 5.3 用户体验风险

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| **交互延迟感** | 中 | 低 | Subagent 通常 < 5s，用户评分交互本身就是等待 |
| **模式切换困惑** | 低 | 低 | 默认直接执行，Subagent 为可选模式 |
| **错误反馈不直观** | 中 | 中 | Subagent 错误应返回结构化 JSON，主会话可解读 |

---

## 六、实施计划

### 6.1 改动清单

| 文件 | 改动类型 | 改动量 | 说明 |
|------|----------|--------|------|
| `SKILL.md` | 新增章节 | +30 行 | 在「动作链」后增加「可选：Subagent 记录模式」 |
| `references/六类记录-schema.md` | 无改动 | 0 | schema 相同 |
| `references/初始化-claude-md-模板.md` | 可选新增 | +5 行 | 环境变量控制说明（可选） |
| `evals/skill-quality/` | 新增 eval | +1 scenario | 验证 Subagent 模式行为一致性 |

### 6.2 实施步骤

| 步骤 | 内容 | 周期 | 依赖 |
|------|------|------|------|
| **Step 1** | 写方案文档（本文档） | 0.5 天 | — |
| **Step 2** | 方案评审 | 0.5 天 | Step 1 |
| **Step 3** | SKILL.md 新增章节 | 0.5 天 | Step 2 通过 |
| **Step 4** | 建立 discriminating eval | 1 天 | Step 3 |
| **Step 5** | 跑 eval 验证行为一致性 | 0.5 天 | Step 4 |
| **Step 6** | 根据 eval 结果调整 | 0.5 天 | Step 5 |
| **Step 7** | 合入主分支 | 0.5 天 | Step 6 通过 |
| **总计** | | **3.5 天** | |

### 6.3 评审要点

请评审时关注：

1. **方案必要性**：主会话上下文占用问题是否值得解决？
2. **技术可行性**：Subagent 两阶段调用是否有技术障碍？
3. **行为一致性**：如何确保 Subagent 模式和直接执行产出相同？
4. **用户体验**：交互延迟是否可接受？
5. **维护成本**：SKILL.md 新增章节是否清晰易懂？

---

## 七、备选方案

### 7.1 方案 B：纯 Hook 驱动（自动化）

**思路**：PostToolUse hook 检测 Step 完成信号，自动写记录。

**优点**：零主会话占用
**缺点**：
- Hook 无法做智能判断（评分、差值分析）
- 无法询问用户评分
- 违背 skill 设计原则（hook 只戳提醒，不做决策）

**结论**：不采用，违背现有架构原则。

### 7.2 方案 C：独立 kdev-memory-recorder skill

**思路**：新建一个专门的 recorder skill，主会话调用。

**优点**：职责分离清晰
**缺点**：
- 两套 skill 维护成本
- Prompt Cache 不共用
- 升级时需同步两套

**结论**：不采用，改造而非新建是更好的选择。

### 7.3 方案对比总结

| 方案 | 主会话占用 | 维护成本 | Cache 共用 | 推荐度 |
|------|-----------|----------|------------|--------|
| **A：现有 skill 改造** | 低 | 低 | ✅ | ⭐⭐⭐⭐⭐ |
| B：纯 Hook 驱动 | 最低 | 中 | N/A | ⭐⭐（违背原则） |
| C：独立 recorder skill | 低 | 高 | ❌ | ⭐⭐⭐ |

---

## 八、参考资料

- `plugins/kdev-memory/evals/skill-quality/iterations/20260423-07-p0-1-discriminating/notes.md`（token 节省证据）
- `plugins/kdev-memory/evals/skill-quality/iterations/20260424-08-skill-used-field/notes.md`（schema 显式化效果）
- `docs/skills/kdev-memory/dev-notes/2026-04-19-跨会话记忆与压缩保护-方案对比.md`（hook 边界原则）

---

## 附录：评审记录

| 评审人 | 日期 | 结论 | 备注 |
|--------|------|------|------|
| | | | |

---

*文档版本：v1.0*
*最后更新：2026-04-28*