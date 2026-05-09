# 功能适配度对比

## 核心需求 → 项目功能映射

### 1. 需求追溯 (文档 → 代码映射)

| 项目 | 实现方式 | 适配度 | 评分 |
|------|----------|--------|------|
| **UA** | `/understand` + semantic_query + doc_code_trace | 文档节点(document:) → 代码节点(file:/function:)，带信心评分 0.5-1.0，明确追溯报告格式 | ⭐⭐⭐⭐⭐ 完美适配 |
| **graphify** | concepts节点 + semantically_similar_to边 | 文档提取为concept节点，通过语义边关联代码，但有置信度分级 (EXTRACTED/INFERRED/AMBIGUOUS) | ⭐⭐⭐⭐ 部分适配 |
| **CRG** | 无文档节点 | 只有代码节点，无文档→代码追溯能力 | ⭐ 不适配 |
| **ops-codegraph** | 无文档节点 | 只有代码节点，无文档→代码追溯能力 | ⭐ 不适配 |

**UA关键优势：**
- 有 `document:` 节点类型
- 有 `documents` 边类型 (doc → code)
- `/understand-onboard` 可生成实现状态报告
- Vision API 支持图片设计稿追溯

---

### 2. 爆炸半径分析 (变更影响范围)

| 项目 | 实现方式 | 适配度 | 评分 |
|------|----------|--------|------|
| **UA** | `/understand-diff` + get_impact_radius | L1直接/L2间接/L3语义三级分层，可视化依赖链，带confidence | ⭐⭐⭐⭐⭐ 完美适配 |
| **ops-codegraph** | `fn-impact` + `diff-impact` + co-change | 函数级追溯，git历史co-change耦合分析，BFS遍历调用链 | ⭐⭐⭐⭐⭐ 完美适配 |
| **CRG** | `get_impact_radius_tool` + `detect_changes_tool` | 核心功能，BFS从变更节点遍历，带风险评分 | ⭐⭐⭐⭐ 高适配 |
| **graphify** | calls边 + query命令 | 可以查询calls边，但无专门的爆炸半径分析命令 | ⭐⭐⭐ 部分适配 |

**对比：**
- UA/ops-codegraph 都有**三级分层** (直接/间接/语义 或 静态/历史/传递)
- ops-codegraph 独有 **co-change历史分析** (git history发现隐藏耦合)
- CRG 有**风险评分**功能
- graphify 只有基础calls边查询

---

### 3. 文档-代码同步检查

| 项目 | 实现方式 | 适配度 | 评分 |
|------|----------|--------|------|
| **UA** | `/understand` doc_code_sync Skill | ✅同步/⚠️需更新/❌缺实现/🔍缺文档 四级状态，时间戳对比+概念匹配，批量审计报告 | ⭐⭐⭐⭐⭐ 完美适配 |
| **graphify** | 无专门功能 | 无文档同步检查能力 | ⭐ 不适配 |
| **CRG** | 无专门功能 | 无文档节点，无法做同步检查 | ⭐ 不适配 |
| **ops-codegraph** | 无专门功能 | 无文档节点，无法做同步检查 | ⭐ 不适配 |

**UA独有优势：**
- 专门的 `doc-code-sync` Skill
- 输出同步报告：文档时间戳 vs 代码时间戳
- 概念匹配检查：文档描述的概念是否在代码中实现
- 优先级建议：立即处理/本周处理/后续处理

---

### 4. 知识蒸馏 Wiki

| 项目 | 实现方式 | 适配度 | 评分 |
|------|----------|--------|------|
| **UA** | `/understand-domain` + `/understand-onboard` + tour-builder | 提取 domains/flows/steps 业务知识，生成 onboarding guide，自动学习路径 | ⭐⭐⭐⭐⭐ 完美适配 |
| **graphify** | `--wiki` + Obsidian vault | Leiden社区聚类 → Wiki文章，wikilink格式，index.md入口 | ⭐⭐⭐⭐ 高适配 |
| **CRG** | `generate_wiki_tool` | 社区聚类 → Markdown Wiki，可查询wiki_page | ⭐⭐⭐⭐ 高适配 |
| **ops-codegraph** | `wiki生成` | 社区聚类 → Wiki，但无业务domain提取 | ⭐⭐⭐ 部分适配 |

**UA独有优势：**
- **Domain提取**: 提取业务领域知识 (domains/flows/steps)
- **Onboarding Guide**: 结构化新人入职指南
- **Tour生成**: 学习路径 + language lessons
- 这是四个需求中**UA最独特的强项**

**graphify优势：**
- Obsidian vault格式，可导入Obsidian知识库
- wikilink互联，社区聚类自动组织

---

## 综合评分

| 项目 | 需求追溯 | 爆炸半径 | 文档同步 | 知识蒸馏 | 总分 |
|------|:--------:|:--------:|:--------:|:--------:|:----:|
| **UA** | 5 | 5 | 5 | 5 | **20/20** ✅ |
| **ops-codegraph** | 1 | 5 | 1 | 3 | **10/20** |
| **graphify** | 4 | 3 | 1 | 4 | **12/20** |
| **CRG** | 1 | 4 | 1 | 4 | **10/20** |

---

## 结论

**UA (Understand-Anything) 完美适配四个核心需求：**

1. ✅ 需求追溯 — 有 `document:`节点 + `documents:`边 + 信心评分
2. ✅ 爆炸半径 — `/understand-diff` + L1/L2/L3分层
3. ✅ 文档同步 — 专门的 `doc-code-sync` Skill
4. ✅ 知识蒸馏 — `/understand-domain` + `/understand-onboard` + tour

**唯一短板：**
- 无 MCP Server (用 Skill 模式)
- TypeScript 架构

**但如果不考虑技术栈，UA 是最佳选择。**

---

## 补充：各项目功能亮点汇总

### UA 功能亮点
- 13种节点类型（含document/config/service/table等）
- 26种边类型（含documents/configures/deploys等）
- React Flow Dashboard（交互式可视化）
- 7阶段Agent Pipeline
- Vision API支持图片设计稿追溯
- Persona模式（junior/experienced不同UI）

### graphify 功能亮点
- 多模态最强：视频/音频/PDF/图片
- 置信度分级：EXTRACTED/INFERRED/AMBIGUOUS
- 71.5x Token压缩效率
- Obsidian vault导出
- MCP Server支持

### CRG 功能亮点
- 28 MCP Tools最丰富
- Daemon守护进程
- SQLite + FTS5全文搜索
- Token效率benchmark
- 多Repo后台自动更新

### ops-codegraph 功能亮点
- CFG + DataFlow深度分析
- 34语言支持最广
- co-change历史耦合分析
- CI Gates (check + manifesto)
- CODEOWNERS映射
- Role分类 (entry/core/utility/dead)