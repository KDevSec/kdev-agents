# MCP Server 和 fastmcp 使用情况搜索报告

## 搜索范围
`D:\Works\SecDev\kdev-agents\plugins`

## 搜索关键词
- `mcp server`
- `fastmcp`
- `MCP`
- `@mcp`
- `mcp_server`

---

## 搜索结果

### 相关文件列表

| 文件 | 路径 | MCP 使用方式 |
|------|------|--------------|
| `.mcp.json` | `plugins/kdev-code-graph/.mcp.json` | MCP server 配置文件，定义 `semantic-graph` server |
| `plugin.json` | `plugins/kdev-code-graph/.claude-plugin/plugin.json` | 插件元数据，声明 MCP servers |
| `hooks.json` | `plugins/kdev-code-graph/hooks/hooks.json` | Hooks 配置，调用 MCP server 命令 |
| `README.md` | `plugins/kdev-code-graph/README.md` | 架构图展示 MCP Server 层及 4 个工具 |
| `SKILL.md` | `plugins/kdev-code-graph/skills/*/SKILL.md` | Skills 引用 MCP tools (`mcp__semantic-graph__*`) |

### MCP Server 实现状态

**kdev-code-graph 插件:**
- **配置已存在**: `.mcp.json` 定义了 `semantic-graph` MCP server (stdio 类型, Python 命令)
- **服务端代码未实现**: `mcp-server/server.py` 在配置中引用但 **不存在** - `mcp-server/` 目录仅包含空的子目录 (graph/, parser/, semantic/, tools/)
- **声明的 MCP 工具** (在 README & skills 中):
  - `semantic_query` - 语义概念查询
  - `detect_changes` - 代码变更检测
  - `doc_code_trace` - 文档到代码追踪
  - `get_impact_radius` - 影响半径分析

### fastmcp 使用情况

**未发现 fastmcp 使用**。kdev-explorer 中的 eval 元数据文件 (`evals.json`, `eval_metadata.json`) 仅包含提示测试数据，不是实际实现。

---

## 结论

整个 `plugins` 目录中仅发现一个 MCP server 声明：**semantic-graph**，位于 **kdev-code-graph** 插件中。

实现状态：**设计/规划阶段** - 配置文件和 skill 定义已存在，但实际的 Python server 代码 (`server.py`) 和模块实现尚未编写。

README 状态标记："Phase 2 MCP Server 核心 - 📝 设计完成"（设计完成，未实现）。

---

*搜索完成时间: 2026-05-09*