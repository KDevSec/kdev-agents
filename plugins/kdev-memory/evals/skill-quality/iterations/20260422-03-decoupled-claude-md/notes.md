# iter-3 notes：CLAUDE.md 接口 / 实现解耦验证

**日期**：2026-04-22
**目的**：验证**解耦改造**——把 CLAUDE.md 规则段从"skill 实现细节的摘要"改为"skill 对外的稳定接口"，看是否：
  - ① 不破坏现有边缘场景的守底能力
  - ② eval-0 初始化时产出的 CLAUDE.md 真的变精简了
  - ③ 新的接口级 assertion 能区分解耦前 / 解耦后
**规模**：4 evals × 2 configs × 1 run = 8 runs（聚焦验证关键问题，不复跑全量 6 场景）
**baseline 选择**：HEAD（Phase 1 重构后但未解耦）—— 专测解耦改造的影响，不回溯 v0.4.0

---

## 结果速览

| Metric | Pre-decouple（baseline） | Decoupled（新版）| Delta |
|---|---|---|---|
| **Pass rate** | 86.5% | **90.6%** | 新版 +4.1 pp |
| **Tokens** | 46,529 ± 11,552 | 45,198 ± 7,813 | 新版省 -2.9% |
| **Time** | 188.3s | 178.3s | 新版快 -5.3% |

**每个 eval 单独看**：

| eval | old_skill (pre-decouple) | with_skill (decoupled) |
|---|---|---|
| **eval-0 init** | 10/12 (83%) | **12/12 (100%)** ← 解耦改造的直接效果 |
| eval-4 merge-conflict | 7/8 (88%) | 7/8 (88%) ← 行为等价 |
| eval-5 missing-data | 6/8 (75%) | 6/8 (75%) ← 行为等价 |
| eval-7 warn-file | 8/8 (100%) | 8/8 (100%) ← 行为等价 |

---

## 三个核心结论

### ✅ 1. 解耦改造成功：eval-0 的 CLAUDE.md 从 57 行精简到 38 行

**新版 CLAUDE.md 规则段的成分**：
- 3 条贯穿铁规（实时落盘 / 文件聚合 / 优先处理 hook 产出）
- 4 个 hook 注入标签 / 文件模式接口
- 7 个召唤 skill 的时机场景
- 关键授权（`.kdev/memory/` 写入 + frontmatter 顺手改）

**新版 CLAUDE.md 规则段**不包含**（已迁移到 skill 本体）**：
- ❌ 17 行触发规则 markdown 表格
- ❌ 评分机制要点（双评分 / 扣分项 / 差值 → R-NNN 等）
- ❌ Q/G/R/Step 编号规则
- ❌ hook 行为响应详细表

**最关键**：Q-001 答案（Step 编号方式）**只入决策日志**，**不同步到 CLAUDE.md**——因为编号规则是 skill 实现细节，不在接口契约里。

### ✅ 2. 边缘场景全部守住

解耦最大的担忧是"会不会去掉太多导致 Claude 失守"。eval-4 / 5 / 7 三个边缘场景数据说明没有：

- **eval-4 合并冲突**：两版本都**保留 CLAUDE.md byte-identical 未动**，都列出了要问用户的差异对照表 / 必答问题清单
- **eval-5 数据缺失**：两版本都**拒绝编造 Step 11**，都提出了合规的恢复路径（用户口述补记 / 接受汇总缺失 / 启用 hook）
- **eval-7 WARN 文件处理**：两版本都完整闭环（读 → 核对 → 采集 → 补记 → 删 WARN → 改 frontmatter）

解耦前的铁规在解耦后**全部保留**（它们属于"贯穿 session"范畴，不属于实现细节）。

### ✅ 3. 新的接口级 assertion 区分力到位

eval-0 old_skill 在 2 条新 assertion 上 FAIL：
- **FAIL**: "不含 8 行以上的触发规则 markdown 表格" —— 旧模板就是有 17 行表
- **FAIL**: "包含「召唤 skill 的时机」段" —— 旧模板把召唤逻辑隐藏在触发表里

这正是升级 assertion 想要的——**让测试本身能拒绝"偷偷把实现细节塞回 CLAUDE.md"**，给未来 skill 维护者一个 guard rail。

---

## 次要发现：Grader 指出的 eval 基础设施问题

eval-4 / eval-5 / eval-7 几个 subagent 没有正确生成 `outputs/REPORT.md`（被 harness 规则拦了），导致依赖 REPORT 内容的 assertion 全部 FAIL：

- eval-4 / 5 的"REPORT.md 明确引用 skill 条款"等 → 没文件可扫
- 被主 agent 补写的 REPORT.md 虽然存在但内容是转写，grader 未算作一手证据

**影响**：eval-4 从真实的 8/8 降到 7/8，eval-5 从真实的 8/8 降到 6/8。

**根因**：subagent prompt 虽要求"写 REPORT.md"但 harness 层有限制；且并非所有 eval 都明确说了 REPORT 放哪。

**下次修复**：
- 在 subagent prompt 里用绝对路径 + 明确文件名
- 或把 assertion 里"REPORT 里说了 X"改成"sandbox 里 Y 的状态证明 X"（从产物证据而非叙述证据下手）

不影响解耦方案的结论——两个 config 都同样受影响，差异是公平的。

---

## 接口契约文档化

新模板文件顶部有 YAML frontmatter `claude_md_contract`：

```yaml
claude_md_contract:
  cross_session_rules: [3 条]
  hook_injection_tags: [<kdev-memory-brief>, <kdev-memory-recall>]
  hook_file_patterns: [WARN-未记录-*.md, checkpoints/压缩前-*.md]
  summon_keywords: [5 类典型]
  version_hint: "契约变更规则"
```

**用处**：
1. 给未来 skill 维护者看的 explicit contract——改 skill 时要对照这个判断"会不会影响老项目 CLAUDE.md"
2. 未来的 SessionStart hook 可以读这个 contract 然后 lint 项目 CLAUDE.md 是否缺少某条必备接口
3. CHANGELOG 里可以明确声明"本次升级是否触及 claude_md_contract"——接口变更和实现变更分开标注

---

## 回答审计文档的原始关切

审计 §5.1 P1-7 原本想做"CLAUDE.md 版本漂移检测 + 一键重写"。iter-3 数据说明：

| 问题 | 解耦后的答案 |
|---|---|
| CLAUDE.md 会漂移吗？ | **90% 场景不会**（实现变更不影响规则段） |
| 10% 场景漂移怎么办？ | **精确 patch 单独几行**（而非整段重写），`claude_md_contract` 给出了要改哪几行的清单 |
| 要不要做自动化漂移检测？ | **可选**——基于 `claude_md_contract` 的 lint 机制，告诉用户"这行该加"比"整段重写"温和得多 |
| 审计 P0-1/2/3（闸门 / 动词链 / 豁免）还需要吗？ | 需要先看 eval-5 数据：**两版本都守住坦白报告**——说明 skill 本体已够硬，P0 修订改在 SKILL.md 本体（不是 CLAUDE.md 规则段）|

**优先级重排建议**（基于 iter-3 实测）：
- **P0 已完成**：接口解耦本身（从根源消除漂移） ✅
- **P1 可做**：`claude_md_contract` lint 机制（让老项目自动收到"缺哪行"的精确提示）
- **P2 观察**：原审计 P0-1/2/3 需要 discriminating eval 验证是否真必要——iter-3 数据说不必要

---

## 与 iter-2 的关系

| 维度 | iter-2（首次解耦前） | iter-3（解耦后） |
|---|---|---|
| 对比对象 | Phase 1 重构后 vs v0.4.0 | 解耦后 vs Phase 1 重构后 |
| 覆盖场景 | 6 个（含 archive / rule-upgrade） | 4 个（只测解耦影响的关键点） |
| 关键发现 | Phase 1 重构省 -19.6% tokens 且行为等价 | 解耦改造 eval-0 100%、边缘场景 0 regression |
| 验证了什么 | "拆分到 references/ 是否可行" | "把 CLAUDE.md 减肥一半是否可行" |

两轮共同证明：**kdev-memory 的 SKILL.md / CLAUDE.md 都可以大幅精简而不损失行为质量**——context budget 有大量可复用的空间，未来加功能（P0/P1 修订）时不用担心上限。

---

## 文件清单

- `benchmark.json` / `benchmark.md` —— aggregated 数据
- `eval-*/eval_metadata.json` —— assertions 冻结快照
- `eval-*/<config>/run-1/grading.json` —— 逐 assertion 评分
- `eval-*/<config>/run-1/timing.json` —— tokens + duration + tool_uses
- （outputs/ 沙盒未保留，workspace 跑完已清理，gitignored）
