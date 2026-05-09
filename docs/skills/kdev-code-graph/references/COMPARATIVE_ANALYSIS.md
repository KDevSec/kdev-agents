# 代码知识图谱项目对比分析报告

> 生成日期: 2026-05-09
> 对比项目: Understand-Anything, graphify, code-review-graph, ops-codegraph-tool

---

## 一、项目概览

| 项目 | Stars | 语言 | 核心定位 | MCP支持 |
|------|-------|------|----------|---------|
| **graphify** | 45k | Python | 多模态知识图谱 (代码+文档+图片+视频) | ✅ |
| **Understand-Anything** | 13k | TypeScript | 交互式Dashboard + 多Agent分析Pipeline | ❌ (Skill模式) |
| **code-review-graph** | - | Python | Token优化 + 爆炸半径分析 + Code Review | ✅ 28 tools |
| **ops-codegraph-tool** | 47 | TypeScript | 深度AST分析 + CFG + DataFlow + CI Gates | ✅ 30+ tools |

---

## 二、能力矩阵对比

### 2.1 核心解析能力

| 能力 | graphify | UA | CRG | ops-codegraph |
|------|----------|-----|-----|----------------|
| **tree-sitter解析** | ✅ 25语言 (WASM) | ✅ 10语言 (WASM) | ✅ 23语言 | ✅ 34语言 (Native+WASM) |
| **多模态支持** | ✅ 视频/音频/PDF/图片 | ✅ 图片/Vision API | ❌ | ❌ |
| **非代码文件** | ✅ Markdown/SQL/Docker等 | ✅ 30+解析器 | ✅ | ✅ |
| **CFG/控制流图** | ❌ | ❌ | ❌ | ✅ |
| **DataFlow分析** | ❌ | ❌ | ❌ | ✅ |
| **复杂度指标** | ❌ | ❌ | ✅ | ✅ Halstead/Cognitive |

### 2.2 图谱能力

| 能力 | graphify | UA | CRG | ops-codegraph |
|------|----------|-----|-----|----------------|
| **节点类型数** | ~5种 | 13种 | 7种 | 10+种 |
| **边类型数** | ~10种 | 26种 | 15种 | 20+种 |
| **增量更新** | ✅ SHA256 cache | ✅ fingerprint | ✅ <2秒 | ✅ 三层检测 |
| **社区检测** | ✅ Leiden | ✅ | ✅ | ✅ |
| **语义搜索** | ❌ 无embedding | ✅ embedding | ✅ 多provider | ✅ hybrid BM25+embedding |
| **角色分类** | ❌ | ❌ | ❌ | ✅ entry/core/utility/dead |

### 2.3 变更影响分析

| 能力 | graphify | UA | CRG | ops-codegraph |
|------|----------|-----|-----|----------------|
| **爆炸半径分析** | ❌ | ✅ /understand-diff | ✅ core功能 | ✅ fn-impact |
| **函数级追溯** | ❌ | ✅ | ✅ | ✅ |
| **调用链追踪** | ✅ calls edges | ✅ | ✅ | ✅ |
| **历史co-change** | ❌ | ❌ | ❌ | ✅ git history分析 |
| **Diff Impact** | ❌ | ✅ | ✅ detect_changes | ✅ |

### 2.4 知识蒸馏能力

| 能力 | graphify | UA | CRG | ops-codegraph |
|------|----------|-----|-----|----------------|
| **Tour生成** | ❌ | ✅ tour-builder Agent | ✅ | ✅ |
| **Onboarding Guide** | ❌ | ✅ /understand-onboard | ❌ | ❌ |
| **Domain提取** | ❌ | ✅ /understand-domain | ❌ | ❌ |
| **Wiki生成** | ✅ Obsidian vault | ❌ | ✅ | ✅ |
| **文档注释提取** | ✅ rationale_for | ✅ languageNotes | ❌ | ❌ |

### 2.5 架构与集成

| 能力 | graphify | UA | CRG | ops-codegraph |
|------|----------|-----|-----|----------------|
| **MCP Server** | ✅ stdio | ❌ | ✅ 28 tools | ✅ 30+ tools |
| **多平台支持** | ✅ 15+平台 | ✅ 10+平台 | ✅ | ❌ CLI only |
| **Dashboard可视化** | ✅ vis.js HTML | ✅ React Flow | ✅ D3.js | ✅ HTML plot |
| **CI Gates** | ❌ | ❌ | ❌ | ✅ check命令 |
| **CODEOWNERS集成** | ❌ | ❌ | ❌ | ✅ |
| **多Repo支持** | ✅ merge-graphs | ❌ | ✅ daemon | ✅ registry |

---

## 三、架构设计对比

### 3.1 graphify — Pipeline架构

```
detect() → extract() → build_graph() → cluster() → analyze() → report() → export()
```

**特点:**
- 纯函数式Pipeline，无共享状态
- NetworkX + Leiden聚类
- 多模态支持最强 (视频/音频转录 + Vision API)
- 边置信度分级: EXTRACTED/INFERRED/AMBIGUOUS

### 3.2 Understand-Anything — 多Agent架构

```
Phase 0: Pre-flight (增量检测)
Phase 1: SCAN (project-scanner)
Phase 2: ANALYZE (file-analyzer × 5并行)
Phase 3: ASSEMBLE REVIEW
Phase 4: ARCHITECTURE (layer-detector)
Phase 5: TOUR (tour-builder)
Phase 6: REVIEW (graph-reviewer)
Phase 7: SAVE
```

**特点:**
- 7阶段Agent Pipeline
- TypeScript Monorepo (packages/core + skill + dashboard)
- React Flow Dashboard 最完整
- Domain/Flow/Step业务知识提取

### 3.3 code-review-graph — MCP优先架构

```
Tree-sitter → SQLite → MCP Server (28 tools)
                   ↓
           Incremental Engine (git diff)
```

**特点:**
- 28 MCP Tools + 5 MCP Prompts
- SQLite存储，FTS5全文搜索
- Token效率benchmark (8.2x平均减少)
- 多Repo Daemon后台守护进程

### 3.4 ops-codegraph-tool — 深度分析架构

```
tree-sitter (Native+WASM) → SQLite → CFG Builder → DataFlow Analyzer
                                      ↓
                            Role Classifier → CI Gate
```

**特点:**
- 34语言支持最广
- CFG + DataFlow深度分析
- 三层增量检测: journal → mtime+size → hash
- CI集成 (check命令 + manifesto规则)
- CODEOWNERS映射

---

## 四、Schema对比

### 4.1 节点类型对比

| 项目 | 节点类型 |
|------|----------|
| graphify | concept, file, function, class, rationale_for |
| UA | file, function, class, module, concept, config, document, service, table, endpoint, pipeline, schema, resource |
| CRG | file, function, class, method, import, test |
| ops-codegraph | file, function, method, class, interface, type, struct, enum, trait, record, module, parameter, property, constant |

### 4.2 边类型对比

| 项目 | 边类型 |
|------|----------|
| graphify | calls, imports, uses, semantically_similar_to, rationale_for, defines |
| UA | imports, exports, contains, calls, inherits, implements, configures, documents, deploys, triggers, defines_schema, routes, provisions, serves, migrates, reads_from, writes_to, transforms, validates, depends_on, tested_by, related, similar_to, subscribes, publishes, middleware |
| CRG | calls, imports, inherits, implements, contains, tested_by, depends_on |
| ops-codegraph | calls, imports, inherits, implements, contains, flows_to, returns, mutates, parent_of, receiver, parameter_of |

---

## 五、关键差异点

### 5.1 graphify 独特能力

| 能力 | 说明 |
|------|------|
| **多模态最强** | 视频/音频本地转录 (Whisper)，PDF解析，图片Vision API |
| **置信度分级** | EXTRACTED/INFERRED/AMBIGUOUS 三级标签 |
| **Obsidian导出** | 生成Obsidian vault，wikilink格式 |
| **71.5x Token压缩** | benchmark验证的token效率 |

### 5.2 UA 独特能力

| 能力 | 说明 |
|------|------|
| **交互式Dashboard** | React Flow + Monaco Editor + Chat Panel，最完整的可视化 |
| **业务Domain提取** | /understand-domain 提取 domains/flows/steps |
| **Tour生成** | guided learning tour + language lessons |
| **Persona模式** | non-technical/junior/experienced 不同UI |

### 5.3 CRG 独特能力

| 能力 | 说明 |
|------|------|
| **28 MCP Tools** | 最丰富的MCP工具集 |
| **Daemon守护进程** | 多Repo后台自动更新 |
| **Wiki生成** | 自动生成markdown wiki |
| **Benchmarks验证** | 6个真实repo的benchmark数据 |

### 5.4 ops-codegraph 独特能力

| 能力 | 说明 |
|------|------|
| **CFG + DataFlow** | 控制流图 + 数据流分析，34语言全覆盖 |
| **角色分类** | entry/core/utility/adapter/dead/leaf |
| **CI Gates** | check命令 + manifesto规则，exit code集成 |
| **CODEOWNERS** | 符号→Owner映射 |
| **Co-change分析** | git历史耦合分析 |

---

## 六、对 kdev-code-graph 的借鉴建议

### 6.1 可直接采用的设计

| 来源 | 设计点 | 建议 |
|------|--------|------|
| **UA** | KnowledgeGraph Schema | 直接采用13节点类型 + 26边类型定义 |
| **UA** | Agent Pipeline结构 | 参考7阶段流程设计多Agent分析 |
| **graphify** | 置信度分级 | 采用 EXTRACTED/INFERRED/AMBIGUOUS |
| **CRG** | MCP Tools设计 | 参考28 tools的tool命名和参数设计 |
| **ops-codegraph** | 三层增量检测 | 采用 journal → mtime → hash 策略 |

### 6.2 可参考的架构

| 来源 | 架构 | 建议 |
|------|------|------|
| **UA** | TypeScript Monorepo | 如果用TypeScript，采用packages/core结构 |
| **CRG** | SQLite + FTS5 | 采用SQLite存储 + FTS5全文搜索 |
| **ops-codegraph** | Native+WASM | tree-sitter Native优先，WASM fallback |

### 6.3 领域特化建议

kdev-code-graph 定位为**安全编码领域特化**，应补充：

| 能力 | 建议来源 |
|------|----------|
| **安全边类型** | 新增: `secure_implements`, `security_tested_by`, `vulnerability_related` |
| **安全节点类型** | 新增: `vulnerability`, `security_rule`, `compliance_requirement` |
| **安全规范追溯** | 参考UA的domain-analyzer，设计 `security-rule-analyzer` |
| **安全爆炸半径** | 参考ops-codegraph的fn-impact，设计 `security-impact` |

### 6.4 集成路径建议

**Option A: 基于现有项目扩展**
- 使用 ops-codegraph-tool 作为底层引擎 (MCP Server + CFG/DataFlow)
- 补充安全领域的节点/边类型
- 开发安全特化的Skills

**Option B: 独立实现 + 参考设计**
- 参考 UA 的 Schema 和 Agent Pipeline
- 参考 ops-codegraph 的 MCP Tools 结构
- 参考 graphify 的置信度分级
- 参考 CRG 的 SQLite + FTS5

---

## 七、附录: MCP Tools对比

| Tool类别 | CRG | ops-codegraph |
|----------|-----|---------------|
| **构建** | build_or_update_graph_tool | build |
| **查询** | query_graph_tool, traverse_graph_tool | query, where, context |
| **搜索** | semantic_search_nodes_tool, embed_graph_tool | search (hybrid) |
| **影响** | get_impact_radius_tool, detect_changes_tool | impact, fn-impact, diff-impact |
| **结构** | list_communities_tool, get_architecture_overview_tool | communities, structure |
| **分析** | get_hub_nodes_tool, get_bridge_nodes_tool, get_surprising_connections_tool | triage, audit |
| **重构** | refactor_tool, apply_refactor_tool | — |
| **Wiki** | generate_wiki_tool, get_wiki_page_tool | wiki生成 |
| **CI** | — | check, manifesto |
| **Flow** | list_flows_tool, get_flow_tool, get_affected_flows_tool | flow, dataflow, cfg |
| **代码** | find_large_functions_tool, get_docs_section_tool | complexity, exports, children |
| **多Repo** | list_repos_tool, cross_repo_search_tool | registry |

---

## 八、结论

| 项目 | 推荐借鉴程度 | 主要价值 |
|------|--------------|----------|
| **Understand-Anything** | ⭐⭐⭐⭐⭐ | Schema设计 + Agent Pipeline + Dashboard + 知识蒸馏 |
| **ops-codegraph-tool** | ⭐⭐⭐⭐⭐ | MCP架构 + CFG/DataFlow + CI集成 + 深度分析 |
| **graphify** | ⭐⭐⭐⭐ | 多模态 + 置信度分级 + Token优化 |
| **code-review-graph** | ⭐⭐⭐ | MCP工具设计 + Daemon + Wiki |

**综合建议:**

kdev-code-graph 应采用**混合借鉴策略**:
- Schema + Agent Pipeline → UA
- MCP架构 + CFG/DataFlow → ops-codegraph
- 置信度分级 → graphify
- SQLite存储 + FTS5 → CRG

然后在安全编码领域做**特化扩展**:
- 新增安全相关节点/边类型
- 开发安全规范追溯Agent
- 设计安全爆炸半径分析
- 集成安全编码规范 (参考kdev-secure-coding)