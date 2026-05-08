# kdev-memory

为多迭代项目建立持久跨会话记忆——实时落盘决策/踩坑/执行，智能召回防止重复踩坑。双评分机制（AI+人工）沉淀使用经验，积累改进建议驱动 spec 和 skill 自主优化。

## 这个插件和其他记忆方案的关系

Claude Code 生态里还有两种常见的"记忆"概念，**它们和 kdev-memory 正交而不重叠，推荐同时使用**：

| 解决的问题 | 典型方案 | 记什么 | 存哪里 |
|---|---|---|---|
| **用户个人化画像**（跨项目） | Claude Code 内置 `auto memory` | 用户偏好、协作习惯、外部系统指针 | `~/.claude/projects/<hash>/memory/`（用户机全局） |
| **会话流回放**（让 Claude 记住昨天聊了啥） | 第三方会话压缩类插件 | 压缩后的会话 JSONL 摘要 | 项目内 gitignore 目录（本机私有） |
| **工程过程档案**（本插件） | kdev-memory | 结构化决策/踩坑/Step/评分/改进信号 | `.kdev/memory/`（本地过程目录，默认 gitignore） |

kdev-memory 的差异化设计点：

- **零外部 API 成本**：Claude 自己落盘，不调任何外部 API，不产生 token 以外的费用
- **不依赖关闭 Auto-compact**：实时落盘不靠会话 JSONL，官方压缩吃掉也不丢信号
- **过程/产物分家**：`.kdev/` 是本地过程目录（默认 gitignore）；团队共享产物通过 `/kdev-memory-promote` 沉淀到 `docs/` 等产物通道
- **按需召回 + 渐进式披露**：triggers 字面匹配 → 只给编号/标题/路径指针 → Claude 按需 Read，长项目更省 token
- **双评分 + 下游原料库**：模型自评/用户评分/差值信号，沉淀成改进建议喂给未来 skill 作者

## 核心机制

- **实时落盘**：每步完成、每次踩坑、每个决策、每次评分，立刻写进 `.kdev/memory/` 对应文件
- **快速汇总**：说"写今天的总结"时，从 `.kdev/memory/` 当天条目聚合拼装，不翻会话记录
- **智能召回**：用户提到相关话题时，UserPromptSubmit hook 自动注入 `<kdev-memory-recall>` 指针让 Claude 按需 Read
- **双评分**：模型自评 + 用户评分，差值暴露方法论盲区
- **跨会话续航**：SessionStart 注入摘要、PreCompact 写 checkpoint、SessionEnd 兜底 WARN

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件（自动带 hook）
claude plugin install kdev-memory@kdev-agents
```

## 使用

### 初始化（新项目首次使用）
> "建立工程记忆" / "加 .kdev" / "搞记忆机制"

### 日常（自动，无需干预）
CLAUDE.md 触发规则段让智能体在每步完成后自动记录。

### 每日汇总
> "写今天的总结" / "生成每日汇总" / "交接给明天" / "总结一下今天"

### 恢复跨会话上下文
> "昨天做到哪了" / "之前聊到什么" / "上次进度" / "继续上次的工作" / "恢复上下文"

新会话直接开问 —— SessionStart 注入会让 Claude 立刻给出上下文概览。

### 切档归档（长项目）
> "切档" / "归档一下" / "整理主文件"

执行日志按月切、踩坑/决策按季度切，搬老条目到 `归档/` 子目录。

### 规则升级（沉淀方法论）
> "这条以后都要遵守" / "加到项目规则" / "升级成铁规"

Claude 会问三件事：升不升级 / 放哪 / 加不加 triggers。源条目原文保留。

### 修 CLAUDE.md 漂移
> "修 CLAUDE.md 漂移" / "接口漂移" / "claude.md 对齐 skill"

SessionStart 自动检测 CLAUDE.md 与 skill 接口契约是否一致，漂移时提醒用户。召唤 skill 即可一键精确 diff patch 对齐。

### 启用严格模式（推荐长流程项目）
```bash
touch .kdev/memory/strict
```

### 沉淀团队产物
> "/kdev-memory-promote" —— 列出 pending 沉淀候选，用户确认后写入 docs/

### 周总结
> "/kdev-memory-weekly" —— 滚动 7 天周总结（汇报四段骨架：过程资产/经验总结/问题教训/开发进展）

## 六类记录

| 触发时机 | 写入文件 | 编号 |
|---------|---------|------|
| 需人做决策（有歧义、多选项、不可逆） | 决策日志.md | Q-NNN |
| 踩坑 / 绕路 / 报错 / 命令失败 | 踩坑日志.md | G-NNN（带 triggers）|
| 每步/每里程碑完成 | 执行日志.md | Step N（双评分）|
| 用户当场反馈体验/规则 | 执行日志.md 评估区 | — |
| 会话结束前 | 每日汇总/YYYY-MM-DD.md | — |
| 评分差值 ≥ 2 或反复出现的感受信号 | 改进建议.md | R-NNN |
| 流程状态变更 | 当前状态.md | — |

详细 schema 见 `skills/kdev-memory/references/六类记录-schema.md`。

## Hook 行为（七层防线）

按会话时序由前到后七层 hook 协同工作：

### 1. SessionStart hook —— 开局注入

新会话启动时注入结构化摘要：
- 有无 `WARN-*.md` / `checkpoints/` 待处理
- 今日执行日志 / 每日汇总状态
- `当前状态.md` frontmatter 字段（phase / iteration / current_step 等）
- 最近一条 Step / Q / G 编号
- CLAUDE.md 接口漂移检测结果

### 2. UserPromptSubmit hook —— 智能召回

用户每次发 prompt 时，扫 `.kdev/memory/` 里所有标了 `triggers:` 的条目，字面匹配命中就注入 `<kdev-memory-recall>` 指针。**渐进式披露**——只给编号+标题+路径，Claude 判断相关再 Read 细节。

扫描数据源：踩坑日志 G-NNN（全部） / 执行日志 Step（今日/昨日） / 方法论铁规（全部） / 项目级 spec 文件 7 个约定路径。

防误触发：Prompt sanitize strip 代码块/XML/URL/文件路径/git diff。
防刷屏：每 session 同一条只注入一次（60min TTL），单次最多 3 条。

### 3. Stop hook —— 软提醒

检查 `.kdev/memory/` 状态并提醒：今天无汇总 / 汇总过时 / 执行日志空 / 主文件跨期需归档。

### 4. Strict 模式 —— 条件阻塞

`touch .kdev/memory/strict` 启用。执行日志空 + 工作区实质变更 → `exit 2` 阻塞，必须落盘才能结束。

### 5. PostToolUse hook —— 里程碑联动

命中里程碑白名单（Spec Kit、ADR、迭代/Sprint、PRD/架构、数据库 migration、API 契约等）时提醒追加 Step。

### 6. PreCompact hook —— 压缩前写盘

会话即将被压缩时，写 `.kdev/memory/checkpoints/压缩前-*.md`（核心文件原文 + 工作区快照）。7 天后自动清理。

### 7. SessionEnd hook —— 兜底警告

会话结束时若执行日志空 + 工作区有变更 → 写 `.kdev/memory/WARN-未记录-*.md`。下次 SessionStart 会显眼列出。

## .kdev/ 目录结构

```
.kdev/
└── memory/                    # kdev-memory 的全部产物
    ├── 当前状态.md             # 工作状态单一真相源（YAML frontmatter）
    ├── 决策日志.md             # Q-NNN
    ├── 踩坑日志.md             # G-NNN（每条带 triggers: [...]）
    ├── 执行日志.md             # Step N + 双评分 + triggers
    ├── 每日汇总/               # YYYY-MM-DD.md
    ├── 改进建议.md             # R-NNN（不切档，保完整）
    ├── 方法论铁规.md           # 可选
    ├── 归档/                   # 长项目切档产物
    │   ├── 执行日志-YYYY-MM.md
    │   ├── 踩坑日志-YYYYQN.md
    │   └── 决策日志-YYYYQN.md
    ├── strict                  # 启用 Strict 阻塞
    ├── WARN-未记录-*.md        # SessionEnd 兜底
    ├── state/                  # hook 运行时状态
    │   └── trigger-sessions.json
    └── checkpoints/            # PreCompact 快照（7 天 retention）
```

## 当前状态.md YAML frontmatter

```markdown
---
phase: exec
iteration: "Sprint 1"
current_step: 23
last_updated: 2026-04-19
pending_decisions: [Q-007, Q-008]
unresolved_gotchas: [G-014]
---

# 当前状态

（自由文本 body）
```

每次完成 Step 要顺手更新 `current_step` + `last_updated`。

## Worktree 与多分支

`.kdev/` 默认 gitignore 后，切分支时记忆不变；SessionStart brief 显示当前分支。

Secondary worktree 自动 symlink：SessionStart 检测后自动建 `.kdev → 主 worktree/.kdev`（Linux/macOS 用 ln -s，Windows 用 NTFS junction）。所有 worktree 透明共享记忆。

## 项目级 spec 文件自动扫描

UserPromptSubmit hook 自动扫描以下路径的 triggers：
- `constitution.md` / `spec.md` / `principles.md` / `AGENTS.md`（项目根）
- `.specify/constitution.md`
- `docs/constitution.md` / `docs/principles.md`

## 更新

```bash
/plugin marketplace update kdev-agents
/plugin update kdev-memory@kdev-agents
```

第三方 marketplace 默认不自动更新。完整升级方式见 [仓库根 README](../../README.md#更新)。

## 验证 hook 是否生效

```bash
# 1. 确认插件启用
grep -A3 enabledPlugins ~/.claude/settings.json

# 2. 手动跑 SessionStart
python3 ~/.claude/plugins/marketplaces/kdev-agents/plugins/kdev-memory/hooks/session-start-brief.py < /dev/null

# 3. 手动跑 Stop hook
python3 ~/.claude/plugins/marketplaces/kdev-agents/plugins/kdev-memory/hooks/stop-check.py < /dev/null

# 4. 开调试模式
claude --debug
```

## License

MIT