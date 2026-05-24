# kdev-code-graph CHANGELOG

## [0.3.0] — 2026-05-24

**关联器家族双成员上线 + UX 知情同意 + doc-sync 取代：从"只能建图"升级到"安全规则 ↔ 代码 + spec ↔ 代码"全链路语义关联。**

PatternLinker（成员 1）+ SemanticLinker（成员 2）相继落地，trace / impact / spec-link 三条审计路径同时拿到真实可查的图谱边。本次 22 个 commit，单测 92/92 PASS（从 0.2.0 时的 ~30 增长到 92），真实数据烟测在本仓库 PRD 上抽出 63 条 intent（30 section + 33 fr_row 精确对应 F1.1–F8.3）。

设计与计划文档全部归档在 `docs/skills/kdev-code-graph/` 下：
- 决策记录：`2026-05-22-CRG融合评估与目标定位结论.md`
- PatternLinker：`2026-05-22-安全模式linker设计.md` + 实施计划
- SemanticLinker：`2026-05-22-spec-link设计.md` + 实施计划

---

### ✨ 新增功能

#### 关联器家族（`kdev_ingestor/linkers/`）

新建 `linkers/` 子包，定义统一抽象与两个成员：

**成员 1：PatternLinker（零 LLM，确定性）**
- 从安全规则的 `### 适用场景` 段抽 backtick API token 作为模式
- 词边界匹配扫源码，命中行用 `lineRange` 映射到 function 节点（落不进则退到 file 节点）
- 产 `related` 边（direction=forward, weight=0.6），source 端的 `kdev:security_rule` tag 编码 kdev 语义
- 折进 `/kdev-codegraph-build`：`/understand → inject → link` 三步连跑
- 真实数据验证：在 UA 自己的图谱（57 function 节点）上跑通函数级精度 + 文件级兜底两条路径

**成员 2：SemanticLinker（LLM 判定，按需触发）**
- 全新 skill `/kdev-codegraph-spec-link`：扫 markdown spec → B+ 粒度抽 intent（FR 表格行 + section）→ KeywordRetriever 做候选检索 → 每条 intent 派一个 sonnet subagent 判定 → 写 `documents` 边（direction=backward, weight=confidence）
- 三阶段架构：`spec-link-prepare`（本地 stdlib）→ skill 派 subagent（LLM）→ `spec-link-finalize`（本地 stdlib）
- 输出**统一两维报告**：实现状态（✅有实现 / ⚠️部分 / ❌未发现 / 🔥LLM 错误）+ 同步状态（漂移 / 缺文档 / LLM 幻觉跳过）
- 漂移阈值：默认 30 天，涉及 `kdev:security_rule` 的 doc 收紧到 14 天
- 幂等：`graph.extras.kdev_spec_link.owned_edge_triples` 标记自己产的边，重跑时先清旧再写新，不污染 UA 原生的 documents 边
- `CandidateRetriever` Protocol 为未来 `EmbeddingRetriever`（C 策略，跨语言召回）留接口

#### 人友好"前置面板"（UX 一致性）

- 所有重操作 skill（`/kdev-codegraph-build` + `/kdev-codegraph-spec-link`）开场打印结构化面板：
  - 这次会做什么（分步）/ 成本提示（subagent 数 + token 估算）/ 这次会产生什么 / 跑完后能做什么 / `[y/n]` 确认
- 显眼标注 🔴 **不建议在按"请求次数"计费的 coding plan 上跑**，引导用户切到 API 计费
- spec-link 采两段式：开场粗略告知 + prepare 完成后用 intents.json 精确 N 数二次确认
- 支持 `--yes` 跳过确认（自动化场景）

#### 新 CLI 子命令（`kdev-ingest`）

- `kdev-ingest link --rules-dir --graph --source-root`：PatternLinker 编排
- `kdev-ingest spec-link-prepare --graph --source-root --out [--top-k]`：抽 intent + 候选 → intents.json
- `kdev-ingest spec-link-finalize --graph --verdicts --source-root --report-dir`：写边 + extras + 报告

#### trace skill 更新

- 模式 1（规范→代码）报告新增"⚠️ 疑似涉及（related 边，weight=0.6，需人工核对）"段落
- 模式 2（代码→规范）的邻居扫描扩展为同时认 `documents` 和 `related` 边
- 措辞统一为"模式命中 ≠ 一定违规，请对照规则正例/反例人工核"

---

### 💥 破坏性变更

- **删除 `kdev-codegraph-doc-sync` skill**：能力被 `/kdev-codegraph-spec-link` 完整取代且加强（LLM 判定 + 真实证据支持的"未发现实现"判定，不再仅依赖 UA 浅启发式）
- `plugin.json` 的 `skills` 数组：`-./skills/kdev-codegraph-doc-sync` `+./skills/kdev-codegraph-spec-link`
- 已升级用户：跑 `/kdev-codegraph-spec-link` 替代 doc-sync，第一次跑会过两次知情同意面板

---

### 🔧 内部改进

- `intents.py`（B+ 粒度 markdown 解析）：FR 表格首列 ID 模式识别 / section 默认 / 无标题文档兜底
- `candidates.py`（`KeywordRetriever`）：token 重叠评分 + 全零兜底 + 小图全表，仅考虑 function/class 节点
- `semantic_linker_finalize.py`：`_remove_owned_edges` 重建 `_edge_triple_to_index`，保证幂等
- `references/conventions.md`：清理 doc-sync 残留，`documents` 边语义改写为 spec-link 视角
- `linkers/base.py` Protocol docstring 收紧：明示 SemanticLinker 是不同形态，不实现该 Protocol
- 重复 `intent_id` 在 prepare 阶段被检测：后者覆盖 + stderr 警告

---

### 🧪 测试

- 92 测试 PASS（0.2.0 时 ~30 → 0.3.0 92），增量 +60+
- 新增覆盖：intent 抽取（5）/ KeywordRetriever（6）/ semantic prepare（5，含重复 intent_id 警告）/ semantic finalize（10，含幂等 / extras / 报告 / security 14d 阈值 / LLM 幻觉跳过暴露）/ PatternLinker（9）/ CLI（3 个 link 端到端 + 7 个 spec-link 相关）
- contract test 不回归（`related` / `documents` 都在 UA 白名单内）

---

### 📦 兼容性

- UA 上游：测试通过 v2.6.3，预期对后续小版本兼容（contract test 守护）
- Python：3.11+（stdlib only，零依赖）
- Claude Code：与 0.2.0 一致

---

### 已知限制（v1 接受，留作 future）

- KeywordRetriever 跨语言（中文 spec ↔ 英文代码摘要）召回不全 —— EmbeddingRetriever（C 策略）通过 Protocol 接口预留，未来实现
- PatternLinker 文本扫描不解析 AST，可能命中注释/字符串中的字面量（已通过 weight=0.6 + "疑似涉及"措辞表达不确定性）
- SemanticLinker 全量重跑（无增量），追踪 doc/code 改动差量留作 future


## [0.2.0] — 之前

- 初版：UA 适配 + ingestor inject（仅灌孤立规则节点，无边）+ trace / impact / doc-sync / build 4 skill 骨架
- 已知问题：trace / impact 跑出来恒为空（规则节点是孤岛，缺 linker）—— 0.3.0 由 PatternLinker + SemanticLinker 修复
