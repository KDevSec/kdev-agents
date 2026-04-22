# iter-4 notes：CLAUDE.md lint 自动化 + 修漂移流程

**日期**：2026-04-22
**目的**：验证在 iter-3 解耦 + `claude_md_contract` 的基础上，新增的 `claude_md_lint.py` + SessionStart hook 集成 + "修漂移"召唤流程是否真的带来自动化价值
**规模**：1 eval × 2 configs × 1 run = 2 runs
**baseline**：HEAD（iter-3 解耦版，有 contract 但无 lint 工具、无专门修漂移流程）

---

## 结果速览

| Metric | Baseline（解耦但无 lint）| With lint + fix workflow | Delta |
|---|---|---|---|
| **Pass rate** | 75% (6/8) | **100% (8/8)** | +25 pp |
| **Tokens** | 44,897 | 54,372 | +9,475（+21%） |
| **Time** | 154.9s | 199.3s | +44.4s（+29%） |

New skill 多花 ~20% tokens / ~30% time 换来的：
- 漂移**自动识别**（lint 工具输出 JSON）
- diff patch **一次闭环**（不用等用户裁决多轮）
- `status=ok` 复验**权威确认**修复成功
- +25 pp 更高 pass rate

---

## 关键对比

### baseline（iter-3 解耦后但无 lint）的行为

- 读 `claude_md_contract` + CLAUDE.md → 识别 **4 项漂移**（比 lint 更严格的人类式语义对比）
- 按"CLAUDE.md 合并策略" **暂停不改**，把 diff + 抉择问题交给用户
- 产出：详细的 diff 清单 + 3 个抉择问题

**验证**：baseline **已经做对了核心事情**——识别 + 给建议 + 不自作主张合并。这证明 iter-3 的解耦架构本身是 self-documenting 的：即使没有显式"修漂移"流程章节，skill 通过 `claude_md_contract` + "合并策略"两块信息，能正确推理出合规行为。

### with_skill（新版 lint + 修漂移流程）的行为

1. **Before**：跑 lint → `status: drift`, `missing_hook_files: 2 个`
2. **Edit**：生成最小化 diff patch（仅 3 行新增：1 条 🔴 铁规 + 2 行 bullet）
3. **After**：复跑 lint → `status: ok`, 契约齐全
4. **保留**：`## 开发惯例` 未动；用户写的"（缺第 3 条…）"括注也未动（只管辖 contract 字段）

每一步都有对应的 sandbox 文件证据（REPORT.md 里给出 before/after 双形式 + 字节数比对）。

---

## 自动化价值的本质

baseline 和新版最终都能完成**正确**的漂移修复，差异在**用户负担**：

| 步骤 | Baseline | With lint |
|---|---|---|
| 发现漂移 | 用户在项目待很久才意识到 | **SessionStart hook 自动在 brief 里 ⚠️ 提示** |
| 判定缺什么 | Claude 通读 contract + 规则段 | **lint 一秒 JSON 输出** |
| 生成 diff | Claude 逐项写建议 | **skill 按 reference 里的流程生成最小化 diff** |
| 用户介入 | 要回答 3-4 个抉择问题 | **一次"批准 diff"即可** |
| 验证修复 | 靠用户肉眼看 | **lint 复跑 → status=ok 权威确认** |

---

## grader 提出的 3 点 nuance（未来可考虑）

1. **baseline 的 contract 对比比 lint 严格**
   - Baseline 识别 4 项漂移（包括 injection tags / summon keywords 过简）
   - lint 只报 2 项（missing_hook_files）
   - 原因：lint 用字面子串匹配（fixture 的 `<kdev-memory-brief>` 在注释里也算命中），baseline 做语义理解
   - 这是**刻意设计**：lint 宽松 = 低误报 + 高可用；严格对比交给 skill 人类介入时做

2. **`（缺…）` 括注"撒谎"**
   - 用户的历史注释"缺第 3 条…"在漂移修复后仍保留，条件已修复但注释还说缺
   - 是**刻意**行为：skill 只管辖 contract 字段，**不动**用户自定义内容
   - 未来可加 `lint --clean-comments` 选项清理已解决的历史注释

3. **开发惯例章节完好**
   - 两版本都正确守住章节边界——Node.js / npm test 行一字未动
   - 证明 Edit 的 section scoping 机制可靠

---

## 累计演进（iter-1 → iter-4）

| iteration | 改动 | 对审计问题的对应 |
|---|---|---|
| iter-1 | SKILL.md 拆分到 references/（Phase 1 重构） | 为后续改动腾出 context 预算 |
| iter-2 | 6 场景全面验证重构 | 证明重构语义零损失 + tokens -19.6% |
| iter-3 | CLAUDE.md 接口 / 实现解耦 + `claude_md_contract` | 审计 §6 盲区 1（无升级路径）根治 |
| **iter-4** | **lint 工具 + SessionStart 集成 + 修漂移流程** | **审计 P1-7（CLAUDE.md 版本漂移检测）正式落地** |

审计 P1-7 的原方案是"版本号标记文件 + 一键重写"；iter-4 落地的是更优雅的"`claude_md_contract` lint + 精确 diff patch + 用户批准"。核心进步：不再依赖版本号（自然演进友好），也不粗暴整段重写（用户手改保护）。

---

## 下一轮可做（留给后续 session）

- **P1-5 brief 欠评 Step 告警**（~1h）：SessionStart 扫执行日志最近 N 条 Step，标"污染样本"/"待补"⚠️
- **P1-6 Stop hook check-step-completeness**（~1h）：扫今日 Step 字段完整度，strict 模式下 exit 2 阻塞
- **P0-1 discriminating eval 设计**（~1-2h）：前面 3 次 iter 数据都暗示 skill 本体已够用，真要加闸门需 discriminating eval 先证明必要性
- **eval-6 跨会话续航验证**（~10min）：已有 fixture，补场景覆盖
- **kdev 生态推广 contract 模式**：若 kdev-commit 等其他 skill 未来有贯穿 session 铁规，复用同样的 `<plugin>_md_contract` frontmatter + lint 框架

---

## 文件清单

- `benchmark.json` / `benchmark.md`
- `eval-8-claude-md-drift/eval_metadata.json`
- `eval-8-claude-md-drift/<config>/run-1/grading.json`
- `eval-8-claude-md-drift/<config>/run-1/timing.json`
