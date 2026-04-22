# 2026-04-22 审计修订对账（session 结束态）

**对应审计**：[2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md](./2026-04-22-skill-CLAUDEmd模板漂移审计-token-statistics与KDevSec对照.md)
**session 日期**：2026-04-22
**范围**：仅针对 kdev-memory skill 的修订（审计 §5.1 + §6），项目级修复（§5.2 / §5.3）留给项目侧 session 处理

---

## 本 session 产出（已 commit，4 个 commit）

| commit | 内容 | 对审计的覆盖 |
|---|---|---|
| [5e9c94d] | Phase 1 重构：SKILL.md 734 → 254 行 + 6 references/ | 铺垫——给规则层改进留 context 预算 |
| [705d378] | skill-quality eval 线 + 8 场景 + 首轮基线数据 | 铺垫——为审计所有 P0/P1 验证提供工具 |
| [3cda481] | 审计文档 + skill 官方开发流程归档 | 证据保存 |
| [573c157] | **CLAUDE.md 接口 / 实现解耦 + iter-3 验证** | **核心改进**——审计 §6 盲区 1 / 4 根治 |

## 审计问题对账表

### §5.1 skill 规则层改进

| # | 审计项 | 原优先级 | session 后状态 | 依据 / 备注 |
|---|---|---|---|---|
| P0-1 | Step 完成闸门（四段必填） | P0 | **🟡 待 discriminating eval 验证** | iter-3 eval-5 两版本都守住坦白报告 → 说明当前 SKILL.md §核心运作原则 + §每日汇总的动作路径 已隐含闸门功能。真要改，应先设计能区分新老 skill 的 eval，否则改完跟不改没差 |
| P0-2 | "公布→问→锁定"动词链 | P0 | **🟡 待验证** | iter-2/3 subagent 都按预期执行自评 + 用户评分序列，动词链不改也做到了。建议只在 discriminating eval 跑出差异后才动 SKILL.md |
| P0-3 | 豁免动作化（meta + BLOCKED 必采） | P0 | **🟡 当前 eval 未覆盖** | 需要新增 subagent-driven 批次场景 eval（eval-8 候选）才能验证是否真必要 |
| P0-4 | Step 定义脱离状态机 | P0 | **✅ 已隐含** | 新 SKILL.md "一个工作单元 = 一个 Step 候选"实际已表达；若未来发现项目仍按状态机绑 Step，可加显式声明 |
| P1-5 | SessionStart brief 加欠评 Step 告警 | P1 | **🟡 待做** | 需要扫执行日志最近 N 条 Step 的"用户评分时分戳空/污染样本/待补"。估时 1h |
| P1-6 | Stop hook check-step-completeness | P1 | **🟡 待做** | 扫今日 Step 字段齐全度，软提醒 / strict 模式下 exit 2。估时 1h |
| P1-7 | CLAUDE.md 版本漂移检测 | P1 | **✅ 方案升级** | 原方案（标记文件 + 一键重写）升级为：基于 `claude_md_contract` 的 lint + 用户确认 diff patch。估时 4.5h，设计见下 |
| P2-8 | 升级指南 vX→vY | P2 | **🟡 解耦后优先级降** | 解耦后 CLAUDE.md 不会像以前那样频繁变，升级指南本身很少用。除非有具体项目反馈，否则不做 |
| P2-9 | subagent-driven 批次 meta 自动注入 | P2 | **🟡 待数据驱动** | 需要先 P0-3 验证过再决定 |

### §6 对 skill 长期演进的 5 个盲区

| 盲区 | 本 session 状态 |
|---|---|
| 1. SKILL.md 没有"项目升级时重写 CLAUDE.md"的路径 | **✅ 解耦 + `claude_md_contract` 从根源消除漂移；lint 机制规划中** |
| 2. skill 假设"规则写对 = 执行到位"忽略行为闸门 | 🟡 iter-3 显示 skill 本体够用，真要加闸门需 discriminating eval 先证明必要性 |
| 3. 豁免单向弹性无底线 | 🟡 待 eval-8 subagent-driven 批次场景验证 |
| 4. hook 兜底只扫文件层面不扫语义层面 | 🟡 P1-5/6 待做 |
| 5. Step 粒度定义绑项目状态机 | **✅ 新 SKILL.md 已隐含"工作单元 = Step"** |

### §5.2 token-statistics 项目级修复

全部 8 项属于 token-statistics 项目内部修复，**不在本仓库 session 范围**。建议 token-statistics 项目开独立 session 处理——届时本仓库提供的 `claude_md_contract` lint 机制（若已实现）会自动告诉该项目"CLAUDE.md 缺哪几行"。

### §5.3 KDevSec 项目级修复

全部 3 项属于 KDevSec 项目内部修复，**不在本仓库范围**。

### §3 A6 kdev-commit 邮箱策略

**验证**：kdev-commit 的 SKILL.md + block-unattributed-commit.js + plugin.json 全部已对齐 v0.2.0 策略（真实邮箱，不拼 `@noreply.local`）。SKILL.md 第 118 行显式标注了 v0.1.0 → v0.2.0 的迁移。

**残留问题**：token-statistics 项目的 CLAUDE.md 里可能还写着 v0.1.0 策略——这是**项目 CLAUDE.md 漂移**，不是 skill 问题。等 `claude_md_contract` lint 实现后能自动识别。

---

## 本 session 新发现（审计未列）

| 问题 | 发现时机 | 建议 |
|---|---|---|
| **eval REPORT.md 被 subagent harness 拦截** | iter-2 / iter-3 | 下次 eval 迭代把 assertion 从"REPORT 叙述"改成"sandbox 状态证据"；或改 subagent prompt 明确要求写 REPORT.md 到 outputs/ 根 |
| **其他 skill 缺 `claude_md_contract`** | 本 session | kdev-commit 当前无贯穿 session 铁规，不需要 contract；未来若新 skill 有贯穿铁规，应复用该模式 |
| **iter 命名约定确立** | 本 session | `YYYYMMDD-NN-<purpose>`，写入 skill-quality/README.md |
| **iter-3 grader 报告时 eval-0 old_skill 意外暴露 2 条 FAIL** | iter-3 grade | 证明新 assertion 有 discriminating 能力——是好信号，不是 bug |

---

## `claude_md_contract` lint 方案（下一步规划）

### 架构

```
插件升级（静默）
  ↓
skill 的 references/初始化-claude-md-模板.md 里的 claude_md_contract 可能变了
  ↓
用户下次新会话 → SessionStart hook
  ↓
跑 hooks/claude-md-lint.py：比对 contract vs 项目 CLAUDE.md
  ├─ 有漂移 → <kdev-memory-brief> ⚠️ 段告诉用户缺哪几行
  │          + 提示："召唤 kdev-memory 说'修 CLAUDE.md 漂移'"
  │          → skill 生成精确 diff patch
  │          → 用户审 → Claude 执行
  └─ 无漂移 → brief 正常
```

### 边界

- Hook 只**检测**（纯只读），真正的**修改**走 skill → 用户批准 → Claude 执行
- 只管辖 `## 智能体自动记录规则` 章节，其他内容一概不碰
- 用户在规则段内加的自定义行不覆盖（append-only 原则）
- 无 contract 变更的实现级升级（90%）完全静默，不打扰用户

### 估时拆分

| 工作项 | 估时 |
|---|---|
| `hooks/claude-md-lint.py` | 2h |
| SessionStart hook 集成 lint | 0.5h |
| `references/初始化-claude-md-模板.md` 加"修漂移"流程章节 | 0.5h |
| SKILL.md 加新召唤触发词 | 0.3h |
| eval-8 "接口漂移修复"场景 + 验证 | 1h |
| 合计 | **~4.5h** |

---

## 下一 session 推荐的入口（按 ROI 排序）

1. **实现 `claude_md_contract` lint**（~4.5h）— 审计 P1-7 的真正落地 + kdev 生态可复用的架构
2. **P1-5/6 hook 语义扫描**（~2h 合计）— 补 Stop / SessionStart 的 Step 字段完整度检查
3. **设计 P0-1 的 discriminating eval**（~1-2h，不动 SKILL.md） — 看闸门规则是否真必要
4. **跑 eval-6 跨会话续航**（~10 分钟，已有 fixture）— 补齐 skill description 覆盖
5. **若 P0-1 eval 显示有差异 → 再动 SKILL.md 本体**（不动 CLAUDE.md 规则段——那是接口）

---

## 项目级修复（独立 session）

以下不在本仓库 session 范围，提示相关项目 owner：

- **token-statistics 项目**：等 `claude_md_contract` lint 实现后，该项目 SessionStart 会自动报告 CLAUDE.md 漂移 —— 届时按 lint 提示逐行 patch；§5.2 其他 7 项按项目节奏自行处理
- **KDevSec 项目**：§5.3 全部 3 项按项目节奏处理；`claude_md_contract` lint 也会帮助标记漂移（如有）
