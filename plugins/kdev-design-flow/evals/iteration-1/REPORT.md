# kdev-design-flow v0.1 Eval Test Report

**日期**：2026-05-08
**版本测试**：0.1.0（commit `4b7a827`）
**Eval 套件**：iteration-1
**模型**：trigger eval 用 haiku、behavioral 用 sonnet
**约束**：spec-kit 插件未安装在测试环境，主循环 E2E 不可跑

---

## TL;DR

- **Trigger 准确度：93.75%**（15/16）—— 唯一漏判 T07（`--resume` 场景被误归类到 `superpowers:executing-plans`）。零 false positive。
- **Behavioral 测试：1 PASS / 1 SOFT PASS / 1 FAIL**。FAIL 在 B02（`--resume` 不存在的 slug 时 SKILL.md 没有错误分支，会让用户撞到未捕获 traceback）。
- **核心结论**：v0.1 可以发布给个人用户体验，但**两个真实可见 bug 必须在 v0.2 修掉**：① description 让 `--resume` 不被 SKIP 漏掉；② SKILL.md 给 resume 模式补上 "flow-state.json 不存在" 的错误分支。

---

## 1. 测试范围与边界

### 1.1 测了什么

| 维度 | 用例数 | 方式 |
|------|--------|------|
| Trigger 准确度（description 是否在该触发时触发、不该触发时不触发） | 16 (8 should-trigger + 8 should-not-trigger) | 每个 query 派一个 haiku subagent，把 skill description 喂进 prompt，让它判 TRIGGER/SKIP + confidence |
| Boot sequence 边界行为（缺依赖 / resume 不存在 slug / 无效 review 模式） | 3 | 每个场景派 sonnet subagent，让它读 SKILL.md + 实际跑 `lib/` 辅助函数 + 记录观察到的行为 |

### 1.2 没测什么 + 原因

| 维度 | 跳过原因 |
|------|---------|
| 主循环 E2E（Stage 2/3/4 委派 spec-kit + frontend-design） | spec-kit 未安装；这是 v0.1 spec 里写好的"显式 v0.1 不验收的部分"，留给 post-install 真用户首跑 |
| Stage 1 SR 分析输出质量 | dep check 在它前面拦着；且产出质量是主观判断，更适合人工 review 而不是自动 eval |
| 评审闸门 PASS/FAIL 决策质量 | 同上，主观判断，且需要真实产物喂进去 |
| `--review=both` / `human` 的 AskUserQuestion 交互 | subagent 沙盒不能模拟 IDE 弹窗 |

---

## 2. Trigger Eval 详细结果

### 2.1 总体指标

```
Total queries:     16
Passed:            15 (93.75%)
Failed:             1
Precision:        100.0%   (TRIGGER 时永远对)
Recall:            87.5%   (8 个该触发的，捕到 7 个)
Mean confidence:    0.946  (subagent 对自己判断的平均把握度)
Mean latency:       10.2s  (haiku 单次)
Total tokens:    ~200K     (16 个 subagent 累加)
```

混淆矩阵：

|              | 实际 TRIGGER | 实际 SKIP |
|--------------|:------------:|:---------:|
| **判 TRIGGER** | 7  | 0 |
| **判 SKIP**    | 1  | 8 |

### 2.2 每个查询的判定

✅ = 判定符合预期 / ❌ = 漏判或误判

| ID  | Expected | Got      | ✓/✗ | 一句话场景 |
|-----|----------|----------|----|-----------|
| T01 | TRIGGER  | TRIGGER  | ✅ | 完整需求-原型-设计三段，前后端都用 |
| T02 | TRIGGER  | TRIGGER  | ✅ | "走一下 kdev 设计流程" + `--review=both` |
| T03 | TRIGGER  | TRIGGER  | ✅ | 老板让交完整方案（需求+用户故事+UI+技术设计） |
| T04 | TRIGGER  | TRIGGER  | ✅ | "需求到方案一条龙：积分商城" |
| T05 | TRIGGER  | TRIGGER  | ✅ | 完整三段 + `--review=human` |
| T06 | TRIGGER  | TRIGGER  | ✅ | 直接喊斜杠命令 `/kdev-design-flow` |
| **T07** | **TRIGGER** | **SKIP** | **❌** | **resume 中断的流程（slug=a3f8c2d1）** |
| T08 | TRIGGER  | TRIGGER  | ✅ | "完整需求分析+原型+设计" 多端配置同步 |
| T09 | SKIP     | SKIP     | ✅ | "我有个想法...值不值得做"（→ office-hours） |
| T10 | SKIP     | SKIP     | ✅ | 只要原型 mockup（→ frontend-design） |
| T11 | SKIP     | SKIP     | ✅ | brainstorming 用户故事边界（→ brainstorming） |
| T12 | SKIP     | SKIP     | ✅ | 执行已有 plan.md（→ executing-plans） |
| T13 | SKIP     | SKIP     | ✅ | 重构 user_login.py（无关任务） |
| T14 | SKIP     | SKIP     | ✅ | tweak spec-kit 的 prompt（不要误触） |
| T15 | SKIP     | SKIP     | ✅ | 用户明说"不要 spec-kit"（不适用） |
| T16 | SKIP     | SKIP     | ✅ | 只要用户故事模板（不需要全流程） |

### 2.3 唯一漏判分析：T07

**Query**：
> 我之前那个'消息推送中心'的设计流跑到一半被打断了，slug 应该是 a3f8c2d1，用 resume 模式接着跑

**Subagent reasoning**（原文）：
> "User is resuming an interrupted design flow, not initiating new one. Falls under executing existing plans, not triggering new design flow."

**根因**：description 的 SKIP 子句写的是"用户在执行已有计划（应让 superpowers:executing-plans 处理）"。但 kdev-design-flow 的 `--resume` 也是一种"执行已有的东西"——subagent 没区分清楚两者：
- "执行已有 plan"（plan.md 文件）→ executing-plans
- "恢复 kdev-design-flow 中断的流程"（flow-state.json）→ kdev-design-flow 自己

**影响**：用户用 `--resume` 时 description 没把这条路径"圈"进 TRIGGER 集合，可能导致 Claude 不调起本 skill 而是去找 executing-plans。这是真实生产里会复现的漏触发。

**建议修复**（v0.2 description）：

把当前的：
> 本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（ai / both / human，默认 ai = Claude 自评）。

改成：
> 本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（ai / both / human，默认 ai = Claude 自评）。**`--resume <slug>` 同样属于本 skill 范围**：用户提到要恢复某个之前被中断的设计流程（带 slug 或描述类似 "继续之前那个 X 的设计"）应该触发本 skill 而非 superpowers:executing-plans——后者处理 plan.md 文件的执行，不是 design-flow 的 flow-state.json。

---

## 3. Behavioral Eval 详细结果

### 3.1 B01 — 缺 spec-kit 时 hard-stop（✅ PASS）

**场景**：用户跑 `/kdev-design-flow 团队周报自动汇总`，但 spec-kit 没装。

**观察**：
- Step 0 解析 OK：`feature_name=团队周报自动汇总`、`review_mode=ai` (默认)
- Step 1 检测：spec-kit:specify 和 spec-kit:plan 都不在 Skill 列表
- 立即中断，输出**完全匹配** SKILL.md 模板的错误信息：
  ```
  ❌ kdev-design-flow 需要 spec-kit 插件，但当前环境未安装。
  请先运行：
      claude plugin install spec-kit
  然后重新触发 /kdev-design-flow。
  ```
- Steps 2-4 没有执行（正确）

**结论**：依赖检测路径完全按 SKILL.md 设计工作。

---

### 3.2 B02 — `--resume` 不存在的 slug（❌ FAIL）

**场景**：用户跑 `/kdev-design-flow --resume zzzz9999-fake-slug`（slug 不存在）

**观察**：
- Step 0 parse：正确识别 resume 模式 + slug
- 跳到"恢复模式"段（按 SKILL.md 设计，跳过 Step 1 的 dep check）
- 调 `read_state(workspace, 'zzzz9999-fake-slug')` → 抛 `FlowStateError: no flow-state.json at /tmp/.../zzzz9999-fake-slug/flow-state.json`
- **SKILL.md "恢复模式" 段只处理两个 status 分支（in_progress / aborted），没处理"文件根本不存在"的前置失败**
- 结果：`FlowStateError` 没被捕获，用户看到的是裸 Python 异常，没有可执行的下一步建议

**这是个真 bug**。`lib/flow_state.py` 里 `read_state` 已经抛了一个语义清晰的 `FlowStateError("no flow-state.json at <path>")`，但 SKILL.md 没告诉 Claude 怎么处理这个异常。

**建议修复**（v0.2 SKILL.md "恢复模式" 段）：

在现有内容前面加一条 step 0：

```markdown
## 恢复模式（`--resume <slug>`）

如果用户带 `--resume <slug>`：

0. 先尝试 `read_state(workspace, slug)`。如果抛 `FlowStateError`（文件不存在）：
   向用户输出（不要继续）：

   ```
   ❌ 找不到 slug "{{slug}}" 的流程记录。
   预期路径：.kdev/design-flow/{{slug}}/flow-state.json
   
   请检查：
   - slug 拼写是否正确（参考 .kdev/design-flow/ 下的子目录）
   - 是否在错误的工作目录下执行
   
   如要新建流程，去掉 --resume 并用：
     /kdev-design-flow <feature_name>
   ```

1. （原来的 step 1）校验 status...
```

**额外建议**（不阻塞 v0.2）：
- 加一个 `/kdev-design-flow --list` 列出当前目录下所有可恢复的 slug

---

### 3.3 B03 — 无效 `--review=psychic`（⚠️ SOFT PASS）

**场景**：用户跑 `/kdev-design-flow 用户登录 --review=psychic`

**观察**：
- Step 0 parse：SKILL.md prose 没明文要求"拒绝其他值"——`review_mode='psychic'` 直接传到 Step 2
- Step 2 `init_state` 调 `lib/flow_state.py` 的校验：
  ```
  ValueError: review_mode must be one of ['ai', 'both', 'human'], got 'psychic'
  ```
- `lib` 校验在写文件**之前**抛错（无副作用），所以**功能上是对的**
- 但 SKILL.md 没给"无效参数 → 怎么对用户说"的模板，质量取决于 Claude 临场发挥

**为何叫 soft pass**：rejection 行为正确（无脏状态写入），但用户体验依赖 Claude 当场措辞。SKILL.md 只为"缺 spec-kit"提供了完整模板，无效 `--review` 没有同等待遇。

**建议修复**（v0.2 SKILL.md Step 0）：

在 Step 0 参数解析里加一条：

```markdown
- 校验 `--review` 取值：必须是 `ai` / `both` / `human` 之一。如果不是，立即向用户输出：

  ```
  ❌ 参数错误：--review={{value}} 不是有效的评审模式。
  
  有效选项：
    ai      — Claude 自动评审（默认）
    both    — Claude 先评，然后由你确认
    human   — 完全由你手动评审
  
  请重新触发：/kdev-design-flow {{feature_name}} --review=ai
  ```

  然后停止，不进入 Step 1。
```

---

## 4. 跨用例发现

### 4.1 Slug 可读性问题

B03 报告显示 `slugify('用户登录') = 'd57d8006'`——纯 SHA-1 hash。

这个行为是 v0.1 设计里写明的（不依赖拼音库的 hash 兜底），但**实际效果挺糟**：
- 用户看不出 `d57d8006` 是哪个 feature
- `.kdev/design-flow/d57d8006/` + `.kdev/design-flow/00af4da9/` + `.kdev/design-flow/43f2ed6a/` 几个子目录摆在一起，没有 `feature_name → slug` 的索引
- 用户跑 `--resume` 时根本不知道该传啥 slug（与 B02 漏的 `--list` 功能强耦合）

**短期建议**：在 SKILL.md Step 2 init 之后，把 `feature_name → slug` 的映射 echo 出来给用户：
> 已创建流程，slug = `d57d8006`（建议加书签：feature='用户登录' ↔ slug='d57d8006'）

**v1.0/B 方案建议**：引入轻量拼音库（pypinyin）让中文 slug 可读，或在 `flow-state.json` 里维护一个 manifest 让 `--list` 可以查。

### 4.2 SKILL.md 缺一份"用户错误的 4 种 UX 模板"清单

B01 PASS 是因为 SKILL.md 给了完整错误模板。B02/B03 的弱点都源于"SKILL.md 没给模板"。

建议 v0.2 加一节 "## 用户错误的统一应对" 列出至少这 4 种：
- spec-kit 缺失（已有）
- `--review` 无效值
- `--resume` slug 不存在
- 当前不在 git repo 里（边界情况，目前没测）

模板格式统一：`❌ <一句话错误> + <为什么> + <怎么修>`。

---

## 5. v0.2 修复清单（按优先级）

| # | 优先级 | 改什么 | 改在哪 | 价值 |
|---|--------|--------|--------|------|
| 1 | **P0** | description 加一句区分"resume kdev-design-flow"和"executing-plans" | SKILL.md frontmatter description | 修 T07 漏触发，trigger 准确率 → 100% |
| 2 | **P0** | "恢复模式"段加 step 0 处理 FlowStateError | SKILL.md 恢复模式段 | 修 B02 真 bug，避免用户撞 traceback |
| 3 | **P1** | Step 0 解析加 `--review` 早校验 + 错误模板 | SKILL.md Step 0 | B03 从 SOFT PASS → PASS |
| 4 | **P1** | init 后 echo `feature_name → slug` 映射 | SKILL.md Step 2 | 缓解 4.1 slug 不可读问题 |
| 5 | **P2** | 加"用户错误的统一应对"小节 | SKILL.md 末尾 | 边界场景统一处理 |
| 6 | **P2** | 加 `/kdev-design-flow --list` 命令 | commands/ + SKILL.md | 配合 4.1，让 resume 可发现 |
| 7 | **P3** | 加 `pypinyin` 弱依赖让 slug 可读 | lib/slug.py | UX 提升，但增加依赖（v1.0 再考虑） |

---

## 6. 没修但记一笔

- **T15 信心 0.85（其他都 ≥ 0.92）**：subagent 对"用户明说不要 spec-kit"这个边界场景判断不太确定。这个 query 本身就模糊（用户的需求确实跟 design-flow 重叠），description 当前判 SKIP 是对的；如果将来用户反馈"想用 design-flow 但希望 fallback 不要 spec-kit"，再考虑。
- **运行成本**：16 trigger evals + 3 behavioral evals 总用 token ~270K。后续 iteration 可考虑降低 runs_per_query（现在是 1，skill-creator 推荐 3 取多数）以提高稳定性，但 v0.1 用 1 次 + 高 confidence (0.946 平均) 已经能给出可执行结论。

---

## 7. 结论

**v0.1 ship readiness**：

- ✅ Trigger description 大致到位（93.75%），1 个明确可修的漏判
- ✅ Boot sequence 主路径稳定（B01 完美 PASS）
- ❌ Resume 模式有真 bug（B02），用户首次试 `--resume` 错 slug 时会撞墙
- ⚠️ 边界 UX 不一致（B03 软通过，但跟 B01 待遇差太多）

**建议落地动作**：
1. **打 v0.1.1**（小补丁）：修 7 条清单里的 P0（#1 + #2）—— 这两条修了基本可以放心给外人用
2. **v0.2 计划**：把 P1（#3 + #4）也带上，整体打包成 0.2.0 升级
3. **v1.0/B 方案前**：把 P2 + P3 提上议程（slug 可读性 + 错误 UX 统一）

---

## 附录：原始数据

- 16 个 trigger eval queries：[evals/trigger-eval.json](../trigger-eval.json)
- 16 个 trigger eval 结果（含每条 confidence + duration + tokens）：[trigger-results.json](trigger-results.json)
- 3 个 behavioral eval 报告：
  - [B01-missing-spec-kit.md](behavioral/B01-missing-spec-kit.md)
  - [B02-resume-missing-slug.md](behavioral/B02-resume-missing-slug.md)
  - [B03-invalid-review-mode.md](behavioral/B03-invalid-review-mode.md)
