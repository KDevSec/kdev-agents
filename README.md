# kdev-agents

KDev 系列 Claude Code 插件集合 —— 工程记忆、流程辅助等。

## 已有插件

| 插件 | 说明 |
|-----|------|
| [kdev-memory](plugins/kdev-memory) | 工程记忆制度：实时落盘决策/踩坑/执行/评分，自动 hook 提醒每日汇总 |

## 安装方式

```bash
# 1. 注册 marketplace（一次性）
claude plugin marketplace add KDevSec/kdev-agents

# 2. 按需安装插件
claude plugin install kdev-memory@kdev-agents
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
├── .claude-plugin/
│   └── marketplace.json       # marketplace 清单
└── plugins/
    └── kdev-memory/           # 插件实体
        ├── .claude-plugin/plugin.json
        ├── skills/kdev-memory/SKILL.md
        ├── hooks/
        │   ├── hooks.json
        │   └── stop-check.sh
        └── README.md
```

新增插件：在 `plugins/` 下新建目录 + 在 `marketplace.json` 的 `plugins` 数组里追加条目。

## License

MIT
