# Claude Code 主要功能列表

根据 Anthropic 官方文档 (https://docs.anthropic.com/en/docs/claude-code) 整理。

## 核心定位

Claude Code 是 Anthropic 官方的智能编码工具，作为终端代理 (agentic coding tool)，能够理解您的代码库，帮助您更快地编码。

## 主要功能

### 1. 构建功能与修复 Bug

- **构建新功能**: 用自然语言描述您想要的功能，Claude Code 会规划方法、跨多个文件编写代码并验证其功能
- **修复 Bug**: 描述问题，Claude Code 会追踪问题根源、定位相关代码、理解上下文、实现解决方案并运行测试

### 2. 代码导航与搜索

- **代码库导航**: 理解整个代码库结构
- **文件搜索**: 通过模式匹配查找文件 (Glob)
- **内容搜索**: 搜索文件内容 (Grep)

### 3. 文件操作

- **读取文件**: 查看文件内容
- **编辑文件**: 修改现有文件
- **写入文件**: 创建新文件

### 4. 终端命令执行

- 运行终端命令 (如 `npm test`, `git status`)
- 执行构建和测试流程
- 集成终端环境

### 5. Git 工作流

- 自动化 Git 操作
- 查看仓库状态
- 管理提交和分支
- 创建 Pull Request
- 代码审查

### 6. 测试与验证

- 编写测试用例
- 运行测试套件
- 修复测试失败

### 7. 代码解释

- 解释复杂代码
- 解释编程概念
- 代码审查和建议

### 8. 扩展能力

- **Skills (技能)**: 自定义工作流程
- **MCP (Model Context Protocol)**: 集成外部服务和工具
- **Hooks (钩子)**: 自动化操作
- **Subagents (子代理)**: 任务委托
- **Custom Tools**: 自定义工具定义

### 9. 内置工具

| 工具 | 功能 |
|------|------|
| Read | 读取文件 |
| Write | 写入文件 |
| Edit | 编辑文件 |
| Bash | 终端命令和 Git 操作 |
| Monitor | 监控后台脚本 |
| Glob | 按模式查找文件 |
| Grep | 搜索文件内容 |
| WebSearch | 网络搜索 |
| WebFetch | 获取网页内容 |
| AskUserQuestion | 交互式用户输入 |

### 10. 多平台支持

- **终端 (Terminal)**: 命令行界面
- **IDE**: VS Code 集成扩展
- **Desktop App**: 桌面应用程序
- **Browser**: 浏览器访问
- **GitHub**: 通过 @claude 标签调用

### 11. Agent SDK

- Python/TypeScript SDK 支持构建自定义代理
- 可配置允许的工具和权限模式
- 流式消息处理

### 12. 协作功能

- 内联差异比较 (inline diffs)
- 会话历史
- 代码变更可视化

---

**来源**: Anthropic Claude Code 官方文档 (code.claude.com / docs.anthropic.com)