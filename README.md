# kdev-agents

KDev 系列 Claude Code 插件集合 —— 工程记忆、流程辅助、代码提交等。

## 已有插件

| 插件 | 说明 |
|-----|------|
| [kdev-memory](plugins/kdev-memory) | 工程记忆制度：实时落盘决策/踩坑/执行/评分，七层 hook 兜会话续航 + 按月/按季度归档 |
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

### 关键事实：第三方 marketplace 默认**不**自动更新

Claude Code 对官方 Anthropic marketplace 默认启用 auto-update，但对第三方（包括 kdev-agents）**默认禁用**。这意味着：**即便我们发布了新版本，你也不会自动收到**——除非你主动拉更新或开启 auto-update。

升级检查机制是看每个插件 `plugin.json` 的 `version` 字段做语义版本比较，不看 git tag。我们每次发布都会 bump `version` 并更新对应插件的 `CHANGELOG.md`，[推到 main 分支](https://github.com/KDevSec/kdev-agents) 即生效。

### 方式 A：手动更新（默认方式）

```bash
# 先刷新 marketplace 本地缓存（否则 Claude Code 不知道有新版本）
/plugin marketplace update kdev-agents

# 再升级具体插件
/plugin update kdev-memory@kdev-agents
/plugin update kdev-commit@kdev-agents
```

两步都要跑——`marketplace update` 只刷新元数据，`plugin update` 才真正升级。

### 方式 B：开启 auto-update（一次性配置，之后每次启动自动拉新）

**UI 方式（推荐）**：

```
/plugin → Marketplaces 标签 → 选中 kdev-agents → 打开 Auto-update 开关
```

**settings.json 方式**（在项目或全局 `.claude/settings.json`）：

```json
{
  "extraKnownMarketplaces": {
    "kdev-agents": {
      "source": { "source": "github", "repo": "KDevSec/kdev-agents" },
      "autoUpdate": true
    }
  }
}
```

配置后 Claude Code 每次启动会自动 `/plugin marketplace update kdev-agents`，发现新版本立即升级。

### 如何知道有新版本

- **CHANGELOG**：每个插件目录下的 `CHANGELOG.md` 记录了每个版本的改动（如 [plugins/kdev-memory/CHANGELOG.md](plugins/kdev-memory/CHANGELOG.md)）
- **GitHub watch**：在 [KDevSec/kdev-agents](https://github.com/KDevSec/kdev-agents) 点 Watch → Custom → Releases，有新 release 时收邮件通知
- **当前版本自查**：`/plugin` → Marketplaces → 看 installed version vs latest version

### 环境变量全局开关

如果你想全局禁用所有 plugin 自动更新（包括官方 marketplace）：

```bash
export DISABLE_AUTOUPDATER=1
```

如果只想禁 Claude Code 本体更新但保留 plugin 更新：

```bash
export DISABLE_AUTOUPDATER=1
export FORCE_AUTOUPDATE_PLUGINS=1
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
    │   ├── hooks/                        # 七层 hook（SessionStart/UserPromptSubmit/Stop/PostToolUse/PreCompact/SessionEnd/Strict）
    │   │   ├── hooks.json
    │   │   ├── lib/                      # trigger-match.py / archive-hint.sh / frontmatter.sh / ...
    │   │   └── *.sh
    │   ├── tests/                        # stdlib unittest（trigger-match.py 单元测试）
    │   ├── evals/                        # skill-creator 式 eval（端到端 hook 召回验证）
    │   ├── CHANGELOG.md
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
