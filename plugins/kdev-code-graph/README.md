# kdev-code-graph

> Claude Code 插件 - 语义级代码图谱，支持需求追溯、变更爆炸半径分析和文档-代码同步检查

## 功能概述

### 核心能力

| 功能 | 说明 |
|------|------|
| **需求追溯** | 从设计文档(.md/图片)追溯到代码实现，带信心评分 |
| **爆炸半径分析** | 修改代码时分析影响范围，可视化依赖链 |
| **文档-代码同步** | 检查文档与代码的一致性，发现脱节问题 |

### 支持格式

- **代码**: .py, .js, .ts, .go, .java (Tree-sitter AST 解析)
- **文档**: .md (概念提取 + LLM 语义关联)
- **图片**: .png, .jpg, .webp (Claude Vision API 解析)

## 安装方式

```bash
# 方式 1: 从 Git 安装
/plugins install https://github.com/your-org/kdev-code-graph

# 方式 2: 从 npm 安装
/plugins install @your-org/kdev-code-graph

# 方式 3: 本地目录
claude --plugin-dir ./kdev-code-graph

# 方式 4: 验证结构
/plugins validate ./kdev-code-graph
```

## 使用方式

### 1. 需求追溯

```
用户: 追溯认证需求到代码
Claude: [调用 semantic-trace Skill]
       → 构建图谱
       → 语义查询
       → 输出追溯报告 (需求→代码映射 + 实现状态)
```

### 2. 变更影响分析

```
用户: 这个改动会影响什么？
Claude: [调用 code-review-enhanced Skill]
       → 变更检测
       → 爆炸半径分析
       → 输出影响范围 (L1直接/L2间接/L3语义)
```

### 3. 文档同步检查

```
用户: 文档是否需要更新？
Claude: [调用 doc-code-sync Skill]
       → 扫描文档
       → 对比代码
       → 输出同步报告 (✅同步/⚠️需更新/❌缺实现)
```

## 技术架构

```
┌─────────────┐
│ Skills Layer│  semantic-trace / code-review-enhanced / doc-code-sync
├─────────────┤
│ MCP Server  │  semantic_query / detect_changes / doc_code_trace / get_impact_radius
├─────────────┤
│ Parser Layer│  code_parser (AST) / md_parser (NLP) / image_parser (Vision)
├─────────────┤
│ Graph Store │  SQLite + BFS 爆炸半径分析
└─────────────┘
```

详细架构设计见: [docs/architecture-design.md](docs/architecture-design.md)

## 开发路线图

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 基础插件结构 | ✅ 完成 |
| Phase 2 | MCP Server 核心 | 📝 设计完成 |
| Phase 3 | Markdown 解析 | 📝 设计完成 |
| Phase 4 | 图片解析 | 📝 设计完成 |
| Phase 5 | 语义关联 | 📝 设计完成 |
| Phase 6 | Skills 完善 | 📝 设计完成 |

## 系统要求

- Claude Code >= v2.1.x
- Python >= 3.10
- Anthropic API Key (用于 Vision 和语义提取)

## 许可证

MIT License

---

**版本**: 1.0.0
**状态**: 设计完成，待实施