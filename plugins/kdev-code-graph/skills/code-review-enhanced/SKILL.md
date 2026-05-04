---
name: code-review-enhanced
description: |
  Use this skill to perform code review with semantic impact analysis and blast radius calculation.
  Make sure to use this skill whenever the user mentions: "enhanced code review", "impact analysis", "检查变更影响", "这个改动会影响什么", "review with impact", "blast radius", or when reviewing code changes/PRs that need impact assessment. Even if the user doesn't explicitly ask for "impact", trigger this skill when they mention reviewing changes or making modifications to existing code.
version: 1.0.0
allowed-tools:
  - mcp__semantic-graph__detect_changes
  - mcp__semantic-graph__get_impact_radius
  - mcp__semantic-graph__semantic_query
  - mcp__semantic-graph__build_graph
---

# Enhanced Code Review Skill

Perform code review with semantic impact analysis and blast radius calculation.

## When to Use

Trigger this skill when:
- User asks for "增强代码审查" or "enhanced code review"
- User wants to check impact before making changes
- User is reviewing PR/changes and needs dependency analysis
- User asks "这个改动会影响什么"

## Why This Skill Matters

爆炸半径分析是预防级联故障的关键：

- **预防隐蔽缺陷**：修改一个函数可能引发调用链的连锁问题，爆炸半径能提前预警
- **提高 Review 质量**：知道影响范围后，reviewer 能有针对性地检查关键调用者
- **测试覆盖保障**：自动识别需运行的测试，避免遗漏关键测试场景
- **风险评估量化**：confidence 分级帮助判断哪些影响是确定的，哪些是推测的

## Workflow

### Step 1: Ensure Graph Exists

```
Call mcp__semantic-graph__build_graph (if needed)
Input: { project_root: current working directory }
```

### Step 2: Detect Changes

Identify what has changed:

```
Call mcp__semantic-graph__detect_changes
Input: { file_paths: ["src/auth/service.py"] }
Output: { changed_nodes, new_edges, deleted_nodes }
```

### Step 3: Calculate Impact Radius

For each significant change:

```
Call mcp__semantic-graph__get_impact_radius
Input: { node_id: changed_node.id, depth: 3 }
Output: { impact_set: { level_1, level_2, level_3 }, visualization }
```

### Step 4: Review Recommendations

Based on impact analysis, provide:

1. **Direct Impact**: Code that directly calls/depends on changed code
2. **Indirect Impact**: Code that might be affected through chains
3. **Semantic Impact**: Related code based on semantic similarity
4. **Test Coverage**: Which tests should be run
5. **Review Priority**: Rank files by impact severity

## Output Format

```
## 代码审查影响分析

### 变更文件: src/auth/service.py

**变更节点:**
- AuthService.login() - 修改了返回类型
- AuthService.validate_token() - 新增方法

### 爆炸半径分析

| 层级 | 影响节点 | 信心评分 | 建议操作 |
|------|----------|----------|----------|
| L1 直接 | src/api/routes.py:login_route | 1.0 | 必须审查 |
| L1 直接 | src/middleware/auth.py:check_auth | 1.0 | 必须审查 |
| L2 间接 | src/utils/session.py:get_user | 0.85 | 建议审查 |
| L2 间接 | tests/auth_test.py:test_login | 0.90 | 必须运行测试 |
| L3 语义 | docs/api_spec.md:登录接口 | 0.72 | 建议更新文档 |

### 审查建议

1. 🔴 高优先级: src/api/routes.py - 直接调用 login()
2. 🔴 高优先级: tests/auth_test.py - 测试需更新
3. 🟡 中优先级: src/middleware/auth.py - 依赖验证逻辑
4. 🟢 低优先级: docs/api_spec.md - 文档同步

### 测试覆盖建议

必须运行的测试:
- tests/auth_test.py::test_login
- tests/auth_test.py::test_validate_token
- tests/integration/login_flow_test.py
```

## Notes

- Level 1 = direct calls/dependencies (confidence 1.0)
- Level 2 = indirect chains (confidence 0.7-0.9)
- Level 3 = semantic relations (confidence 0.5-0.7)
- Always include test file recommendations

## Edge Cases / Error Handling

| 场景 | 处理方式 |
|------|----------|
| 空变更列表 | 提示用户指定变更文件，或从 git diff 自动获取 |
| 循环依赖 | 标注循环依赖路径，建议用户优先解耦 |
| 大规模变更 (>50 文件) | 建议用户分批分析，或仅分析核心模块变更 |
| 超时处理 | 图谱查询超时时，建议用户检查图谱大小或重建索引 |
| 无测试覆盖 | 明确标注"无测试"，建议补充测试作为高优先级 |
| 新增代码 | 新节点无调用者，爆炸半径为空，标注为"新增需建立调用关系" |

## Related Skills

| Skill | 适用场景 | 选择依据 |
|------|----------|----------|
| **code-review-enhanced** (本 skill) | 代码变更影响分析，爆炸半径评估 | 用户问"这个改动会影响什么"、"review 前检查风险" |
| **semantic-trace** | 追溯需求文档到代码实现 | 用户问"这个需求实现了吗"、"找对应代码" |
| **doc-code-sync** | 文档同步状态批量审计 | 用户问"文档是否需要更新" |

如果用户在修改代码前想了解影响，用本 skill。如果是检查需求是否实现，用 semantic-trace。