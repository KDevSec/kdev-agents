# iter-2-a-plus notes

**日期**：2026-04-22
**目的**：用升级版 assertions + 3 个新场景（archive / merge-conflict / missing-data）再次验证重构版本 vs v0.4.0 单文件版本。
**规模**：6 evals × 2 configs × 1 run = 12 runs

## 结果速览

| 指标 | Old Skill（v0.4.0，734 行单文件） | New Skill（重构版，254 行 + 6 references） | Delta |
|---|---|---|---|
| **Pass rate** | 100% (56/56) | 100% (56/56) | 0（齐平）|
| **Time** | 259.7s ± 30.7s | 236.3s ± 66.1s | 新版快 -23.4s (-9%) |
| **Tokens** | 59,599 ± 2,820 | 47,892 ± 6,457 | **新版省 -11,707 tokens (-19.6%)** |

---

## 关键发现 1：token 省 19.6% 比 iter-1 更稳

iter-1 是 3 runs × 2 configs，token delta 是 -13%；iter-2 做到 6 runs × 2 configs，delta 是 -19.6%——样本越多差异越显著。意味着新版的 context 优势不是偶然。

平均单 run：新版 47.9k tokens，老版 59.6k tokens——**每次触发 skill 少扛 ~12k token 的"用不上的细节"**，按一天几十次使用频次算，每天至少省几十万 token。

## 关键发现 2：渐进式披露完美落地

通过 `grep` subagent transcripts 的 references/ 路径提及次数，统计每个 with_skill run 实际读了哪些 reference：

| eval | 最高频读取的 reference | 次高 | 解读 |
|---|---|---|---|
| eval-0 init | 初始化模板 (5) + 六类记录 schema (5) | triggers-写法 / hooks (3) | 初始化场景按需拉 schema + 模板 |
| eval-1 daily-summary | 六类记录 schema (4) | triggers / 规则升级 / hooks (2) | 汇总对齐 schema |
| eval-2 rule-upgrade | 初始化模板 (5) + 规则升级 (4) | triggers (3) + schema (2) | 合并策略 + 升级流程双路径 |
| eval-3 archive | **切档与归档 (5)** | hooks (2) | **场景专属精准召回** |
| eval-4 merge-conflict | **初始化模板 (6)** | schema / triggers / hooks (2) | 合并策略条款精准命中 |
| eval-5 missing-data | 平均每个 reference 1 次 | — | SKILL.md 本体够用，reference 不必深读 |

Old_skill 全部读取次数 = 0（单文件 skill 没 references/）。

**结论**：新 skill 不只是"把文件拆小"，而是让 Claude **按场景动态拉取最相关的细节**。eval-3 的切档场景优先读 `切档与归档.md`，eval-4 的合并冲突优先读 `初始化-claude-md-模板.md`——skill-creator 设计的 Progressive Disclosure 精确落地。

## 关键发现 3：边缘场景（eval-4 / eval-5）双版本都正确守住底线

这是最令人意外的结果：

- **eval-4 merge-conflict**：两个版本都**没有自作主张合并**，都把 CLAUDE.md byte-identical 保留，都记录了要问用户的三个问题。
- **eval-5 missing-data**：两个版本都**没有从 src/ 工作区变更反推编造 Step 11**，都正确坦白报告"skill 失效信号"。

**暗示**：审计文档里担心的"skill 默认行为不够硬"可能是**项目现场 CLAUDE.md 漂移** / **触发规则段过时**导致的，不是 skill 本体的规则缺陷。v0.5.0 规则层改进（Step 完成闸门、豁免动作化）可能不是必需的，但**CLAUDE.md 版本漂移检测 + 升级机制**可能是更关键的缺失点。

## assertions 仍然不够 discriminating

升级后 56/56 assertion 全过，没有任何一条能区分 with_skill vs old_skill。grader 建议下次再升级：

- eval-1：加"汇总文件长度 ≤ 50 行（不复述执行日志）"
- eval-2：加"triggers 数量 ≤ 5（符合上限建议）"——能捕捉 old_skill 本次用了 7 个的溢出
- eval-3：加"归档文件里 triggers 字段未被去掉"（归档后召回能力）
- eval-4：加"REPORT 不能自作主张'建议方案 A'（提问即止）"
- eval-5：加"没有生成 WARN 文件"（那是 SessionEnd hook 职责，不是 skill 当下该做的）

这些 assertion 需要**读实际文件内容**（不只是存在性），属于下一轮的优化方向。

## 各 run 原始数据

tokens / duration_seconds / tool_uses：

| run_id | tokens | time (s) | tool_uses |
|---|---|---|---|
| eval-0-with_skill | 57,376 | 263.1 | 19 |
| eval-0-old_skill | 62,358 | 255.8 | 17 |
| eval-1-with_skill | 48,846 | 139.4 | 17 |
| eval-1-old_skill | 56,143 | 203.7 | 15 |
| eval-2-with_skill | 48,197 | 289.6 | 18 |
| eval-2-old_skill | 60,242 | 265.6 | 14 |
| eval-3-with_skill | 51,515 | 318.3 | 19 |
| eval-3-old_skill | 63,249 | 292.3 | 17 |
| eval-4-with_skill | 41,478 | 199.3 | 9 |
| eval-4-old_skill | 57,740 | 280.9 | 9 |
| eval-5-with_skill | 39,940 | 208.1 | 11 |
| eval-5-old_skill | 57,864 | 259.8 | 14 |

With_skill 在所有 6 个 eval 上都比 old_skill 省 token。差距最大是 eval-4 merge-conflict（-28%）和 eval-5 missing-data（-31%）——边缘场景下新版优势更明显，因为：
- 这些场景 Claude **不需要深读很多 reference**（SKILL.md 本体就有足够指引）
- 老版本加载 734 行 SKILL.md 本身就是 context 负担，一旦场景简单就浪费更多

核心场景（eval-0 init）token delta 较小（-8%），因为两个版本都要读完整的 CLAUDE.md 模板 + schema——新版虽然文件更小，但多读了 references/ 对冲掉一部分节省。

## 结论

1. **重构成功，无 regression**：pass rate 100% 双持平，所有行为层面都正确
2. **Token 节省 -19.6% 稳定可信**：6 runs 的方差已经能说明不是偶然
3. **渐进式披露按设计运作**：references/ 文件被精准按场景召回
4. **边缘场景（审计文档失守案例）都正确处理**：暗示 v0.5.0 重点可能不是闸门规则，而是**CLAUDE.md 版本漂移检测**

## 关联资源

- 详细对比数据：`benchmark.json` / `benchmark.md`
- 每个 run 的评分：`eval-*/<config>/run-1/grading.json`
- assertion 定义：`eval-*/eval_metadata.json`
- 完整 sandbox outputs：已删除（gitignored，跑完归档时不保留）
- baseline iter（iter-1）：`../baseline-v0.4.0-vs-refactor/`
