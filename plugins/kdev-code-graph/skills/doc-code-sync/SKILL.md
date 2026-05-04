---
name: doc-code-sync
description: |
  Use this skill to check synchronization status between documentation and code implementation.
  Make sure to use this skill whenever the user mentions: "doc-code sync", "文档代码同步", "check if docs are up to date", "文档是否需要更新", "docs outdated", "document consistency audit", "文档和代码对不上", or when auditing documentation health across the project. Even if the user doesn't explicitly ask for "sync", trigger this skill when they mention outdated docs or doc-code mismatch concerns.
version: 1.0.0
allowed-tools:
  - mcp__semantic-graph__semantic_query
  - mcp__semantic-graph__doc_code_trace
  - mcp__semantic-graph__build_graph
---

# Document-Code Sync Check Skill

Check synchronization status between documentation and code implementation.

## When to Use

Trigger this skill when:
- User asks "文档代码同步检查"
- User wants to audit documentation consistency
- User asks "文档是否需要更新"
- User mentions "docs outdated" or "sync check"

## Why This Skill Matters

文档代码同步是维护项目信息一致性的基础：

- **减少信息不一致**：文档描述的功能与代码实现脱节会导致误导性信息
- **降低新人理解成本**：同步的文档帮助新人快速定位正确代码
- **预防维护隐患**：过时文档可能包含已废弃的接口，误导后续开发
- **自动化审计**：无需人工逐一对照，批量识别需更新的文档并优先级排序

## Workflow

### Step 1: Build/Update Graph

```
Call mcp__semantic-graph__build_graph
Input: { project_root: current working directory }
Output: Graph with doc_nodes and code_nodes
```

### Step 2: Scan Documents

For each document in the project:

```
Call mcp__semantic-graph__doc_code_trace
Input: { doc_name: document_name }
Output: { code_nodes, implementation_status }
```

### Step 3: Analyze Sync Status

Compare:
- Document timestamps vs code timestamps
- Document concepts vs implemented concepts
- Unimplemented concepts (doc exists, code missing)
- Orphan code (code exists, doc missing)

### Step 4: Generate Sync Report

Provide detailed synchronization report.

## Output Format

```
## 文档-代码同步报告

### 同步状态总览

| 状态 | 数量 | 说明 |
|------|------|------|
| ✅ 同步 | 12 | 文档与代码一致 |
| ⚠️ 需更新 | 3 | 代码已更新，文档滞后 |
| ❌ 缺实现 | 2 | 文档描述功能未实现 |
| 🔍 缺文档 | 1 | 代码存在但无文档 |

### 详细分析

#### ⚠️ 需更新的文档

| 文档 | 相关代码 | 变更时间 | 建议 |
|------|----------|----------|------|
| auth_design.md | src/auth/service.py | 代码更新于 2026-04-25 | 更新认证流程描述 |
| api_spec.md | src/api/routes.py | 新增 2 个 API | 补充接口文档 |

#### ❌ 缺实现的功能

| 文档 | 概念 | 描述位置 | 建议 |
|------|------|----------|------|
| security_rules.md | SessionStore | 第 3.2 节 | 需实现 session 存储 |
| perf_spec.md | CacheLayer | 第 2.1 节 | 需实现缓存层 |

#### 🔍 缺文档的代码

| 代码 | 类型 | 建议 |
|------|------|------|
| src/utils/crypto.py:CryptoHelper | 类 | 补充安全模块文档 |

### 优先级建议

1. 🔴 立即处理: auth_design.md - 认证流程已变更
2. 🟠 本周处理: SessionStore 实现
3. 🟢 后续处理: CryptoHelper 文档补充
```

## Sync Status Definitions

|  Icon | Status | Condition |
|------|--------|-----------|
| ✅ | 同步 | doc timestamp ≈ code timestamp, concepts matched |
| ⚠️ | 需更新 | code newer than doc, or concepts diverged |
| ❌ | 缺实现 | doc concept not found in code |
| 🔍 | 缺文档 | code exists without corresponding doc |

## Notes

- Use file modification timestamps for sync detection
- Confidence threshold: 0.7 for concept matching
- Include actionable recommendations prioritized by impact

## Edge Cases / Error Handling

| 场景 | 处理方式 |
|------|----------|
| 图谱缺失 | 自动调用 build_graph，提示首次构建需要等待 |
| 新文档首次检查 | 标注为"新文档"，需要建立 doc-code 关联后才能评估同步状态 |
| 无 timestamp 信息 | 依赖语义匹配而非时间戳，标注为"语义检查" |
| 全新项目 | 提示"项目无历史文档"，建议先运行 semantic-trace 建立基础关联 |
| 大量脱节文档 | 建议用户分批处理，按优先级从高到低逐步修复 |

## Related Skills

| Skill | 适用场景 | 选择依据 |
|------|----------|----------|
| **doc-code-sync** (本 skill) | **批量审计**全项目文档同步状态，生成优先级建议 | 用户问"文档是否需要更新"、"批量检查同步"、"文档健康度" |
| **semantic-trace** | 追溯**单个文档**到代码，查看实现状态 | 用户问"这个需求实现了吗"、"找这个文档的对应代码" |
| **code-review-enhanced** | 代码变更影响分析，爆炸半径评估 | 用户问"这个改动会影响什么" |

**关键区别**：
- 本 skill 是**批量扫描**，适合全项目文档健康度体检
- semantic-trace 是**单点追溯**，适合快速定位特定需求的实现状态

如果用户只是想知道某个文档对应的代码在哪，用 semantic-trace 更高效。如果要做全面审计，用本 skill。