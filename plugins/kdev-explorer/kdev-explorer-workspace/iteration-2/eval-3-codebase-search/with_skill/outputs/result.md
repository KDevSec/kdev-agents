# MCP Server / fastmcp 使用情况

## 文件列表

**核心配置文件：**
- `plugins/kdev-code-graph/.mcp.json` - MCP server 配置（semantic-graph）
- `plugins/kdev-code-graph/.claude-plugin/plugin.json` - 插件定义，引用 mcpServers
- `plugins/kdev-code-graph/hooks/hooks.json` - PostToolUse/SessionStart hooks 调用 server.py
- `plugins/kdev-code-graph/README.md` - 技术架构说明 MCP Server 层

**提及 MCP server 但非实现文件（eval/输出）：**
- `plugins/kdev-explorer/kdev-explorer-workspace/iteration-1/eval-3-codebase-search/*.json/md` - eval 测试产物
- `plugins/kdev-explorer/skills/kdev-explorer/SKILL.md` - Skill 文档提及未来 MCP 联动

## 关键发现

1. **唯一 MCP server 定义**：仅 `kdev-code-graph` 插件定义 MCP server，其他 6 个插件均无。

2. **Server 配置详情**：
   - 名称：`semantic-graph`
   - 命令：`python ${CLAUDE_PLUGIN_ROOT}/mcp-server/server.py serve`
   - 预置工具：semantic_query / detect_changes / doc_code_trace / get_impact_radius

3. **实现状态**：**未实施**。.mcp.json 和 hooks.json 均引用 `mcp-server/server.py`，但该文件不存在。README 标注 Phase 2 MCP Server 核心 "设计完成"。

4. **fastmcp**：无实际代码使用。仅在 eval 测试产物中作为历史搜索关键词出现。

5. **Hooks 设计**：PostToolUse 触发 `server.py update`，SessionStart 触发 `server.py status` - 均待实现。