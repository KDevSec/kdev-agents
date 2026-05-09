# Claude Code Main Features

## Overview

Claude Code is Anthropic's official CLI tool that operates in your terminal, helping developers build features, debug issues, navigate codebases, and automate tasks.

---

## Core Capabilities

### 1. File Operations
- **Read** - Read files from the local filesystem
- **Write** - Write or overwrite files
- **Edit** - Perform precise string replacements in files
- **NotebookEdit** - Edit Jupyter notebook cells

### 2. Search Tools
- **Glob** - Fast file pattern matching (e.g., `**/*.js`)
- **Grep** - Search file contents using regex patterns
- Supports filtering by file type, glob patterns, and context lines

### 3. Execution Tools
- **Bash** - Execute shell commands with configurable timeout
- Supports background execution for long-running tasks
- Git workflow integration (status, diff, commit, push, PR creation)

### 4. Web Tools
- **WebFetch** - Fetch and process web content
- **WebSearch** - Search the web for current information
- **MCP Fetch** - Enhanced fetch capabilities via MCP servers

### 5. Code Intelligence
- Understanding code structure and errors
- Code analysis and explanation
- Navigating large codebases

---

## Advanced Features

### 6. MCP (Model Context Protocol) Integration
- Connect external tools and services
- Extend capabilities with custom MCP servers
- Access to specialized documentation (Context7)
- Browser automation (Playwright)

### 7. Hooks System
- **PreToolUse** - Run before tool execution (validation, security checks)
- **PostToolUse** - Run after tool execution (formatting, linting)
- **Notification** - Handle notifications
- **Stop** - Handle session stop events
- Matcher patterns to target specific tools

### 8. Subagents
- Spawn independent agents for parallel work
- Context isolation from main session
- Specialized agents (code-reviewer, etc.)
- Custom tools and model configuration per subagent

### 9. Memory System
- **CLAUDE.md** - Project-specific instructions
- Global and local memory files
- Persistent context across sessions

### 10. Git Workflows
- Automatic commit creation with proper messages
- Pull request creation via `gh` CLI
- Branch management
- Code review integration

### 11. Skills System
- Reusable prompt templates
- Custom slash commands
- Plugin-based skill extensions

---

## Configuration Options

### Permission Modes
- `accept-all` - Auto-accept all operations
- `acceptEdits` - Auto-accept file edits
- Interactive prompts for sensitive operations

### Settings
- Allowed tools configuration
- Hook configurations
- MCP server settings
- Environment variables

---

## Usage Scenarios

1. **Code Development** - Write, edit, and refactor code
2. **Debugging** - Analyze errors and fix issues
3. **Code Review** - Review changes for quality and security
4. **Documentation** - Generate and maintain docs
5. **Testing** - Run tests and fix failures
6. **Git Operations** - Commits, branches, PRs
7. **Research** - Web search and documentation lookup
8. **Automation** - Hooks and scripts for repetitive tasks