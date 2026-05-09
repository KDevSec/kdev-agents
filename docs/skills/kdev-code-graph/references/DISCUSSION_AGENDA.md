# kdev-code-graph 调研进展与待讨论问题

> 更新日期: 2026-05-09
> 状态: 调研阶段已完成，进入讨论阶段

---

## 一、调研结论摘要

### 已完成调研

四个开源项目对比分析已完成，详见：
- `COMPARATIVE_ANALYSIS.md` — 综合对比
- `FEATURE_FIT_ANALYSIS.md` — 功能适配度评分

### 功能适配度排名

| 项目 | 需求追溯 | 爆炸半径 | 文档同步 | 知识蒸馏 | 总分 |
|------|:--------:|:--------:|:--------:|:--------:|:----:|
| **Understand-Anything** | 5 | 5 | 5 | 5 | **20/20** |
| graphify | 4 | 3 | 1 | 4 | 12/20 |
| ops-codegraph-tool | 1 | 5 | 1 | 3 | 10/20 |
| code-review-graph | 1 | 4 | 1 | 4 | 10/20 |

**结论:** UA (Understand-Anything) 完美适配四个核心需求。

---

## 二、四个核心需求定义

| 需求 | 定义 | UA实现方式 |
|------|------|------------|
| **需求追溯** | 设计文档(.md/图片) → 代码实现映射，带信心评分 | `document:`节点 + `documents:`边 + `/understand` Skill |
| **爆炸半径分析** | 修改代码时分析影响范围，L1/L2/L3分层 | `/understand-diff` + `get_impact_radius` |
| **文档-代码同步** | 文档与代码一致性检查，发现脱节 | `doc-code-sync` Skill，四级状态报告 |
| **知识蒸馏 Wiki** | 提取代码中的设计模式/规范/经验，形成Wiki | `/understand-domain` + domains/flows/steps |

---

## 三、待讨论问题

### 问题1: 技术栈融合方案

**背景:**
- UA 是 TypeScript 架构
- kdev-* 系列插件是 Python 架构
- 用户要求"本地可用 + 轻量"

**待讨论:**
- 如何让 UA 的 TypeScript 与 Python kdev-* 插件协同？
- 是否需要创建 Python 版本的 UA Schema？
- 还是直接使用 UA，kdev-code-graph 作为其领域特化配置？

**相关项目信息:**
- UA: TypeScript Monorepo (`packages/core` + `skill` + `dashboard`)
- CRG: Python + fastmcp + tree-sitter-language-pack (轻量)
- ops-codegraph: TypeScript + 34个tree-sitter包 (重)

---

### 问题2: UA 精简方案

**背景:**
- UA 功能很全（Dashboard、Vision API、Tour、Domain、Onboarding等）
- 用户要求"轻量"

**待讨论:**
- 哪些是核心必需功能？
- 哪些可以裁剪/不做？
- Dashboard 是否必需？还是只需要 MCP Server？
- 多模态（图片/Vision API）是否必需？

**UA 功能模块:**
| 模块 | 功能 | 是否核心？ |
|------|------|-----------|
| Schema | 13节点+26边定义 | ✅ 核心 |
| tree-sitter解析 | 10语言AST提取 | ✅ 核心 |
| `/understand` Pipeline | 7阶段Agent分析 | ✅ 核心 |
| `/understand-diff` | 爆炸半径分析 | ✅ 核心 |
| `doc-code-sync` | 文档同步检查 | ✅ 核心 |
| `/understand-domain` | Domain知识提取 | ✅ 核心 |
| `/understand-onboard` | Onboarding指南 | ⚠️ 可选 |
| Dashboard | React Flow可视化 | ⚠️ 可选 |
| Vision API | 图片设计稿追溯 | ⚠️ 可选 |
| Tour生成 | 学习路径 | ⚠️ 可选 |
| Persona模式 | UI适配 | ❌ 可裁剪 |

---

### 问题3: 安全特化扩展

**背景:**
- kdev-code-graph 定位为安全编码领域特化
- 需要在 UA 基础上新增安全相关能力

**待讨论:**
- 新增哪些安全节点类型？
- 新增哪些安全边类型？
- 是否需要专门的 `/understand-security` Skill？
- 如何与 kdev-secure-coding 插件联动？

**建议扩展方案:**

| 类别 | 新增类型 | 说明 |
|------|----------|------|
| **节点类型** | `security_rule:` | 安全编码规范条目 |
| | `vulnerability:` | 已识别的安全漏洞 |
| | `compliance:` | 合规要求项 |
| | `security_test:` | 安全测试用例 |
| **边类型** | `secure_implements:` | 代码实现了安全规范 |
| | `security_tested_by:` | 安全测试覆盖 |
| | `vulnerability_related:` | 与已知漏洞关联 |
| | `compliance_requires:` | 合规要求映射 |
| **Skill** | `/trace-security` | 安全需求→代码追溯 |
| | `/security-impact` | 安全代码爆炸半径 |

---

### 问题4: MCP Server 设计

**背景:**
- UA 没有 MCP Server（使用 Skill 模式）
- ops-codegraph 有 30+ MCP tools
- CRG 有 28 MCP tools

**待讨论:**
- kdev-code-graph 需要多少个 MCP tools？
- 命名规范如何定义？
- 是否需要参考 CRG/ops-codegraph 的工具设计？

**参考 MCP tools设计:**

| 类别 | CRG tools | ops-codegraph tools |
|------|-----------|---------------------|
| 构建 | build_or_update_graph_tool | build |
| 查询 | query_graph_tool | query, where, context |
| 搜索 | semantic_search_nodes_tool | search (hybrid) |
| 影响 | get_impact_radius_tool | impact, fn-impact, diff-impact |
| 结构 | list_communities_tool | communities, structure |
| Wiki | generate_wiki_tool | wiki生成 |
| Flow | list_flows_tool | flow, dataflow, cfg |

---

### 问题5: Schema 设计决策

**背景:**
- UA 有 13节点 + 26边
- ops-codegraph 有 10+节点 + 20+边

**待讨论:**
- 直接采用 UA Schema？
- 还是精简后采用？
- 安全扩展部分如何融入？

**UA Schema 核心类型:**

节点类型 (13种):
```
file, function, class, module, concept,
config, document, service, table, endpoint,
pipeline, schema, resource
```

边类型 (26种):
```
imports, exports, contains, calls, inherits, implements,
configures, documents, deploys, triggers, defines_schema,
routes, provisions, serves, migrates, reads_from, writes_to,
transforms, validates, depends_on, tested_by, related,
similar_to, subscribes, publishes, middleware
```

---

## 四、讨论优先级建议

建议按以下顺序讨论：

1. **问题2 (UA精简)** → 先确定核心功能范围
2. **问题1 (技术栈)** → 根据功能范围决定架构方案
3. **问题5 (Schema)** → 确定核心Schema
4. **问题3 (安全扩展)** → 在核心Schema上扩展
5. **问题4 (MCP设计)** → 最后设计工具接口

---

## 五、参考资料索引

| 文档 | 路径 | 内容 |
|------|------|------|
| 项目指引 | `references/README.md` | 下载命令 + 文件索引 |
| 综合对比 | `references/COMPARATIVE_ANALYSIS.md` | 四项目完整对比 |
| 功能适配 | `references/FEATURE_FIT_ANALYSIS.md` | 四需求适配度评分 |
| UA Schema | `references/Understand-Anything/understand-anything-plugin/packages/core/src/types.js` | 节点边定义 |
| UA Pipeline | `references/Understand-Anything/understand-anything-plugin/skills/understand/SKILL.md` | 7阶段流程 |
| UA doc-sync | `references/Understand-Anything/understand-anything-plugin/skills/doc-code-sync/SKILL.md` | 文档同步 |
| CRG MCP | `references/code-review-graph/README.md` | 28 MCP tools列表 |
| ops-codegraph MCP | `references/ops-codegraph-tool/README.md` | 30+ MCP tools列表 |

---

## 六、给后续模型的提示

如果你是接续此调研的模型，请：

1. **先读取分析报告** — `COMPARATIVE_ANALYSIS.md` + `FEATURE_FIT_ANALYSIS.md`
2. **理解四个核心需求** — 需求追溯、爆炸半径、文档同步、知识蒸馏
3. **按优先级讨论问题** — 从问题2开始，依次讨论
4. **参考 UA 源码** — 了解 Schema 和 Skill 实现细节
5. **输出讨论结论** — 每个问题给出明确建议