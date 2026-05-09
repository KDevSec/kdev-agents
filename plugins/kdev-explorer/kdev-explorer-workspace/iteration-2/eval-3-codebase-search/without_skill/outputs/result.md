# MCP Server / FastMCP 使用情况搜索结果

## 搜索范围
`D:\Works\SecDev\kdev-agents\plugins` 目录

## 搜索结果汇总

### 1. kdev-code-graph 插件 - MCP Server 配置与设计

| 文件路径 | 说明 |
|---------|------|
| `plugins\kdev-code-graph\.mcp.json` | **核心 MCP Server 配置文件** - 定义了 `semantic-graph` MCP server，使用 Python stdio 方式启动 `server.py serve` |
| `plugins\kdev-code-graph\.claude-plugin\plugin.json` | **插件配置** - 引用了 `.mcp.json` 作为 MCP Servers 配置 |
| `plugins\kdev-code-graph\hooks\hooks.json` | **Hooks 配置** - PostToolUse/SessionStart hooks 调用 MCP server 的 `update` 和 `status` 命令 |
| `plugins\kdev-code-graph\README.md` | **插件文档** - 描述了 MCP Server 层提供 `semantic_query`, `detect_changes`, `doc_code_trace`, `get_impact_radius` 等工具 |
| `plugins\kdev-code-graph\skills\semantic-trace\SKILL.md` | **Skill 定义** - 使用 MCP tools 如 `mcp__semantic-graph__semantic_query`, `mcp__semantic-graph__doc_code_trace` 等 |
| `plugins\kdev-code-graph\skills\code-review-enhanced\SKILL.md` | **Skill 定义** - 使用 MCP tools 进行变更影响分析 |
| `plugins\kdev-code-graph\skills\doc-code-sync\SKILL.md` | **Skill 定义** - 使用 MCP tools 进行文档-代码同步检查 |

**注意**: MCP server 的 Python 实现文件 (`server.py`) 尚未创建，目录结构已准备但代码未实现。

### 2. kdev-explorer 插件 - MCP 使用提及

| 文件路径 | 说明 |
|---------|------|
| `plugins\kdev-explorer\skills\kdev-explorer\SKILL.md` | **Skill 文档** - 提及 MCP fetch 工具作为探索任务示例，描述了与 kdev-code-graph MCP server 的未来联动计划 |

### 3. 设计文档中的 FastMCP 参考

| 文件路径 | 说明 |
|---------|------|
| `docs\skills\kdev-code-graph\2026-04-28-调研报告.md` | **调研报告** - 详细介绍了 code-review-graph 使用 fastmcp 的设计模式，推荐依赖 `fastmcp>=3.2.4` |
| `docs\skills\kdev-code-graph\2026-04-28-实施计划.md` | **实施计划** - 包含 FastMCP 相关实施策略 |
| `docs\skills\kdev-code-graph\references\DISCUSSION_AGENDA.md` | **讨论议程** - MCP server 设计相关讨论 |

## 技术架构分析

### kdev-code-graph MCP Server 设计

```json
// .mcp.json 配置
{
  "mcpServers": {
    "semantic-graph": {
      "type": "stdio",
      "command": "python",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-server/server.py", "serve"],
      "env": {
        "PYTHONUTF8": "1",
        "ANTHROPIC_API_KEY": "${ANTHROPIC_API_KEY}"
      }
    }
  }
}
```

### 计划提供的 MCP Tools

| Tool 名称 | 功能 |
|-----------|------|
| `semantic_query` | 语义级别代码查询 |
| `detect_changes` | 变更检测 |
| `doc_code_trace` | 文档到代码追溯 |
| `get_impact_radius` | 爆炸半径分析 |
| `build_graph` | 构建语义图谱 |

### 推荐的技术栈（来自调研报告）

```toml
[project]
dependencies = [
    "code-review-graph>=2.3.2",  # 复用 GraphStore + Parser + Tools
    "anthropic>=0.40",           # Vision API + 语义关联
    "mcp>=1.0.0",
    "fastmcp>=3.2.4",
]
```

## 实现状态总结

| 状态 | 说明 |
|------|------|
| **配置文件** | 已完成 - `.mcp.json`, `plugin.json`, `hooks.json` 已配置 |
| **Skill 定义** | 已完成 - 三个 skills 的 SKILL.md 已定义 MCP tool 使用 |
| **MCP Server 代码** | 未实现 - `mcp-server/` 目录结构存在但无 Python 文件 |
| **FastMCP 依赖** | 设计中 - 调研报告推荐使用，尚未实际集成 |

---

**搜索完成时间**: 2026-05-09