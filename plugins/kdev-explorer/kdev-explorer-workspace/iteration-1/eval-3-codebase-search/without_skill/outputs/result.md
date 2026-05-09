# MCP Server / FastMCP 使用情况搜索结果

## 概述

在 `D:\Works\SecDev\kdev-agents\plugins` 目录下，MCP server 的使用主要集中在 **kdev-code-graph** 插件中。

## 相关文件列表

### 1. MCP Server 配置文件

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-code-graph\.mcp.json` | MCP Server 配置文件，定义 `semantic-graph` server |

**配置内容摘要：**
- Server 名称: `semantic-graph`
- 类型: `stdio`
- 命令: `python ${CLAUDE_PLUGIN_ROOT}/mcp-server/server.py serve`
- 环境变量: `PYTHONUTF8=1`, `ANTHROPIC_API_KEY`

### 2. Hooks 配置文件

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-code-graph\hooks\hooks.json` | 定义 PostToolUse 和 SessionStart hooks，调用 MCP server |

**Hook 配置内容：**
- `PostToolUse`: 在 Edit/Write/Bash 操作后调用 `python server.py update`
- `SessionStart`: 会话启动时调用 `python server.py status`

### 3. 插件元数据文件

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-code-graph\.claude-plugin\plugin.json` | 插件配置，声明 MCP server 路径引用 `.mcp.json` |

### 4. Skills 文件（声明 MCP tools 使用）

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-code-graph\skills\semantic-trace\SKILL.md` | 声明使用 MCP tools: `semantic_query`, `doc_code_trace`, `get_impact_radius`, `build_graph` |
| `plugins\kdev-code-graph\skills\code-review-enhanced\SKILL.md` | 声明使用 MCP tools: `detect_changes`, `get_impact_radius`, `semantic_query`, `build_graph` |
| `plugins\kdev-code-graph\skills\doc-code-sync\SKILL.md` | 声明使用 MCP tools: `semantic_query`, `doc_code_trace`, `build_graph` |

### 5. 文档文件

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-code-graph\README.md` | 描述 MCP Server 层架构和功能 |

## MCP Tools 命名规范

Skills 文件中声明使用的 MCP tools 均以 `mcp__semantic-graph__` 为前缀：
- `mcp__semantic-graph__semantic_query` - 语义查询
- `mcp__semantic-graph__doc_code_trace` - 文档到代码追溯
- `mcp__semantic-graph__get_impact_radius` - 爆炸半径分析
- `mcp__semantic-graph__build_graph` - 构建语义图谱
- `mcp__semantic-graph__detect_changes` - 变更检测

## 实现状态

**注意：** MCP Server 的 Python 实现文件 (`mcp-server/server.py`) **尚未存在**。
- `.mcp.json` 和 `hooks.json` 已配置，指向 `${CLAUDE_PLUGIN_ROOT}/mcp-server/server.py`
- 但该目录和文件尚未创建（设计完成，待实施）

## FastMCP 使用情况

**未找到任何 FastMCP 使用。** 在整个 plugins 目录中搜索 `fastmcp` 和 `FastMCP` 模式，均无匹配结果。

## 其他 MCP 引用

| 文件路径 | 说明 |
|----------|------|
| `plugins\kdev-explorer\skills\kdev-explorer\SKILL.md` | 描述中使用 "MCP fetch" 作为探索任务的示例（非实际 MCP server 实现） |

---

**搜索日期:** 2026-05-09
**搜索范围:** `D:\Works\SecDev\kdev-agents\plugins`