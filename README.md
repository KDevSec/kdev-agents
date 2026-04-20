# kdev-agents

KDev 系列 Claude Code 插件集合 —— 工程记忆、流程辅助等。

## 已有插件

| 插件 | 说明 |
|-----|------|
| [kdev-memory](plugins/kdev-memory) | 工程记忆制度：实时落盘决策/踩坑/执行/评分，六层 hook 兜会话续航 |
| [kdev-commit](plugins/kdev-commit) | AI commit + push 一体化：AI 用 `<name>-AI` 身份提交，push 前弹 IDE 权限框让用户确认 |

## 安装方式

```bash
# 1. 注册 marketplace（一次性）
claude plugin marketplace add KDevSec/kdev-agents

# 2. 按需安装插件
claude plugin install kdev-memory@kdev-agents
claude plugin install kdev-commit@kdev-agents
```

## 更新

```bash
claude plugin marketplace update kdev-agents
claude plugin update <plugin-name>@kdev-agents
```

## 开发

本地目录结构：

```
kdev-agents/
├── .claude-plugin/marketplace.json       # marketplace 清单
└── plugins/
    ├── kdev-memory/                      # 工程记忆插件
    │   ├── .claude-plugin/plugin.json
    │   ├── skills/kdev-memory/SKILL.md
    │   ├── hooks/                        # 六层 hook（Session/Stop/PreCompact/...）
    │   │   ├── hooks.json
    │   │   ├── lib/
    │   │   └── *.sh
    │   └── README.md
    └── kdev-commit/                      # AI commit + push 插件
        ├── .claude-plugin/plugin.json
        ├── skills/kdev-commit/SKILL.md
        ├── hooks/                        # 纯 Node，零外部依赖
        │   ├── hooks.json
        │   ├── block-unattributed-commit.js
        │   └── confirm-push.js
        └── README.md
```

新增插件：在 `plugins/` 下新建目录 + 在 `marketplace.json` 的 `plugins` 数组里追加条目。

## License

MIT
