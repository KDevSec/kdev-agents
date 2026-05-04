---
name: semantic-trace
description: |
  Use this skill to trace requirements or design documents to their code implementations.
  Make sure to use this skill whenever the user mentions: "trace requirement", "需求追溯", "check if spec is implemented", "find code for design doc", "这个需求实现了吗", "check implementation status", or mentions .md design documents, PRD, spec files, or images that need code mapping. Even if the user doesn't explicitly ask for "trace", trigger this skill when they reference design docs and want to know the implementation state.
version: 1.0.0
allowed-tools:
  - mcp__semantic-graph__semantic_query
  - mcp__semantic-graph__doc_code_trace
  - mcp__semantic-graph__get_impact_radius
  - mcp__semantic-graph__build_graph
---

# Semantic Trace Skill

Trace requirements/design documents to code implementation with confidence scores.

## When to Use

Trigger this skill when:
- User asks "需求追溯" or "trace requirement"
- User wants to check if a spec/PRD is implemented
- User mentions design documents (.md or images)
- User asks "find code for this design"

## Why This Skill Matters

需求追溯是确保设计意图完整落地到代码的关键环节：

- **避免遗漏实现**：设计文档中的需求可能被遗忘或只部分实现，追溯可识别缺口
- **减少沟通成本**：无需人工对照文档逐项检查，自动映射概念到代码
- **变更风险评估**：知道需求对应哪些代码，修改时才能评估爆炸半径
- **新人快速上手**：通过追溯报告理解设计→实现的对应关系

## Workflow

### Step 1: Build/Update Graph

If semantic graph does not exist or is outdated:

```
Call mcp__semantic-graph__build_graph
Input: { project_root: current working directory }
Output: { nodes_count, edges_count, status }
```

### Step 2: Query Semantic Relations

Query by concept from the requirement/design:

```
Call mcp__semantic-graph__semantic_query
Input: { concept: "认证流程", limit: 10 }
Output: { nodes, edges, confidence_scores }
```

### Step 3: Trace Document to Code

If user specifies a specific document:

```
Call mcp__semantic-graph__doc_code_trace
Input: { doc_name: "auth_design.md" }
Output: { code_nodes, implementation_status }
```

### Step 4: Check Impact Radius (Optional)

If changes are being considered:

```
Call mcp__semantic-graph__get_impact_radius
Input: { node_id: "auth_service.py:AuthService", depth: 3 }
Output: { impact_set, visualization }
```

## Output Format

Provide a structured trace report:

```
## 需求追溯报告

### 文档: auth_design.md

| 概念 | 关联代码 | 信心评分 | 实现状态 |
|------|----------|----------|----------|
| AuthService | src/auth/service.py:AuthService | 0.95 | ✅ 已实现 |
| TokenValidation | src/auth/token.py:validate_token | 0.88 | ✅ 已实现 |
| SessionStore | - | - | ❌ 未实现 |

### 爆炸半径分析 (如需要)

Level 1 直接影响:
- src/api/routes.py:login_route (confidence: 1.0)

Level 2 间接影响:
- src/utils/session.py:get_session (confidence: 0.85)

### 建议

1. SessionStore 需要实现，参考 auth_design.md 第 3.2 节
2. AuthService 修改将影响 5 个直接调用者
```

## Notes

- Confidence scores: 1.0 (exact) / 0.7-0.9 (semantic) / 0.5-0.7 (context)
- Implementation status: ✅ implemented / ⚠️ partial / ❌ not found
- Always check graph freshness before querying

## Edge Cases / Error Handling

| 场景 | 处理方式 |
|------|----------|
| 文档不存在 | 提示用户提供正确的文档路径，或列出项目中可追溯的文档 |
| 概念未匹配 | 返回低信心结果，建议用户检查概念命名或手动补充关联 |
| 图谱不存在 | 自动调用 build_graph，提示用户首次构建可能需要等待 |
| 大项目分批 | 建议用户指定关键文档，避免一次性构建全项目图谱（超时） |
| 图片文档追溯 | 支持 Vision API 解析图片中的设计组件，信心评分可能较低 (0.5-0.8) |

## Related Skills

| Skill | 适用场景 | 选择依据 |
|------|----------|----------|
| **semantic-trace** (本 skill) | 追溯**单个文档**到代码，查看实现状态 | 用户问"这个需求实现了吗"、"找对应代码" |
| **doc-code-sync** | **批量审计**全项目文档同步状态，生成优先级建议 | 用户问"文档是否需要更新"、"批量检查同步" |
| **code-review-enhanced** | 代码变更影响分析，爆炸半径评估 | 用户问"这个改动会影响什么"、"review 前检查风险" |

如果用户只是想快速检查单个需求是否实现，用本 skill。如果需要全项目文档健康度审计，用 doc-code-sync。