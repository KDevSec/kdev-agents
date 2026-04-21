# kdev-memory

工程记忆制度插件 —— 为多迭代项目建立持久的跨会话记忆。

## 这个插件和其他记忆方案的关系

Claude Code 生态里还有两种常见的"记忆"概念，**它们和 kdev-memory 正交而不重叠，推荐同时使用**：

| 解决的问题 | 典型方案 | 记什么 | 存哪里 |
|---|---|---|---|
| **用户个人化画像**（跨项目） | Claude Code 内置 `auto memory` | 用户偏好、协作习惯、外部系统指针 | `~/.claude/projects/<hash>/memory/`（用户机全局） |
| **会话流回放**（让 Claude 记住昨天聊了啥） | 第三方会话压缩类插件 | 压缩后的会话 JSONL 摘要 | 项目内 gitignore 目录（本机私有） |
| **工程过程档案**（本插件） | kdev-memory | 结构化决策/踩坑/Step/评分/改进信号 | `.kdev/memory/`（**跟代码 commit**） |

kdev-memory 的差异化设计点：

- **零外部 API 成本**：Claude 自己落盘，不调 Haiku/不调任何 API，不产生 token 以外的费用
- **不依赖关闭 Auto-compact**：实时落盘不靠会话 JSONL，官方压缩吃掉也不丢信号
- **可跟代码一起 commit**：项目内的工程决策/踩坑属于**项目资产**，应该进 git（不是只存在于个人机器）
- **按需召回 + 渐进式披露**：triggers 字面匹配 → 只给编号/标题/路径指针 → Claude 按需 Read，**长项目更省 token 更精准**（vs 全量注入）
- **双评分 + 下游原料库**：模型自评/用户评分/差值信号，沉淀成改进建议喂给未来 skill 作者，不是只服务当前会话

什么时候装 kdev-memory：做**多迭代、多决策、长周期**的工程项目，希望踩过的坑不再重栽、做过的决策能复用、用户评分能沉淀成方法论改进。

什么时候**不要只装** kdev-memory：如果你还需要"上次会话聊了什么"那种对话流回放，搭配一个会话压缩类插件一起用。三类工具组合起来才是完整的记忆栈。

## 核心机制

- **实时落盘**：每步完成、每次踩坑、每个决策、每次评分，立刻写进 `.kdev/memory/` 对应文件
- **快速汇总**：说"写今天的总结"时，从 `.kdev/memory/` 当天条目聚合拼装，不翻会话记录
- **智能召回**：用户提到相关话题时，UserPromptSubmit hook 自动注入 `<kdev-memory-recall>` 指针让 Claude 按需 Read 细节——**已经踩过的坑不再重复、做过的决策能自然复用**
- **双评分**：模型自评 + 用户评分，差值暴露方法论盲区
- **经验外溢**：积累的改进建议喂给未来 skill 作者提炼新 skill
- **跨会话续航**：SessionStart 注入摘要、PreCompact 写 checkpoint、SessionEnd 兜底 WARN，多管齐下保住记忆不丢

## 安装

```bash
# 第一次使用者：注册 marketplace
claude plugin marketplace add KDevSec/kdev-agents

# 安装插件（自动带 hook）
claude plugin install kdev-memory@kdev-agents
```

## 命名空间约定

`.kdev/` 是 kdev 系列插件的**命名空间容器**，每个插件建自己的子目录互不干扰：

```
.kdev/
├── memory/     # kdev-memory 的地盘（本插件）
├── commit/     # 未来 kdev-commit 的地盘（若它要落盘状态）
└── <其他>/     # 未来其他 kdev 插件
```

本插件只管 `.kdev/memory/`，不碰同级其他目录。

## Hook 行为（七层防线）

按会话时序由前到后七层 hook 协同工作：

### 1. SessionStart hook —— 开局注入 + 自动迁移

新会话启动时，脚本扫 `.kdev/memory/` 当前状态，通过 `additionalContext` 注入一段结构化摘要给 Claude：

- 有无 `WARN-*.md` / `checkpoints/` 待处理
- 今日执行日志 / 每日汇总状态
- `当前状态.md` frontmatter 字段（phase / iteration / current_step 等）
- 最近一条 Step / Q / G 编号

Claude 一开局就知道项目全景，不用等用户提"先看下昨天做到哪了"。

按 `source` 分档：`startup`/`clear` 完整摘要；`resume` 精简（Claude 已有上下文）；`compact` 只提醒 checkpoint 在哪。

**额外职责**：检测 0.2.0 平铺结构（`.kdev/执行日志.md` 等），自动搬到 `.kdev/memory/` 子目录，留 `.kdev/MIGRATED-YYYY-MM-DD.md` 说明。从旧版升级完全无感。

### 2. UserPromptSubmit hook —— 智能召回（triggers）

用户每次发 prompt 时，扫 `.kdev/memory/` 里所有标了 `triggers:` 的条目，字面子串匹配命中就注入 `<kdev-memory-recall>` 指针给 Claude。**渐进式披露**——只给编号+标题+路径，Claude 判断相关再 Read 细节。

扫描的四个数据源：

| 数据源 | 召回范围 |
|---|---|
| `.kdev/memory/踩坑日志.md` 的 G-NNN | 全部（永久有效）|
| `.kdev/memory/执行日志.md` 的 Step N | 今日/昨日（日期过滤，避免翻旧账） |
| `.kdev/memory/方法论铁规.md` 的每条规则 | 全部 |
| 项目级 spec 文件 7 个约定路径 | 全部（frontmatter / 行内两种格式） |

约定的 spec 路径：`constitution.md` / `spec.md` / `principles.md` / `AGENTS.md` / `.specify/constitution.md` / `docs/constitution.md` / `docs/principles.md`。

**防误触发**：Prompt sanitize 会 strip 代码块、XML 标签、URL、文件路径、git diff 块，避免用户在贴 README / 错误输出时字面量误触。

**防刷屏**：每 session 同一条记忆只注入一次（60 分钟 TTL 去重，状态文件 `.kdev/memory/state/trigger-sessions.json`）；单次最多注入 3 条。

**依赖 python3**。缺 python3 静默降级。

### 3. Stop hook —— 软提醒

每次 Claude 要停下时检查 `.kdev/memory/` 状态并 stdout 注入提醒：

| 场景 | 提醒 |
|-----|-----|
| 项目未启用 `.kdev/memory/` | 静默，不干扰其他项目 |
| 今天还没生成每日汇总 | 提醒 Claude 聚合生成 |
| 汇总存在 + 源文件有后续更新 | 提醒追加新增条目 |
| 执行日志里今天没条目 | 提醒实时追加 Step |

软提醒的局限：会话自然 idle 时永远不会被下一轮读到。下面几层补上这个缝隙。

### 4. Strict 模式（opt-in，条件阻塞）

`touch .kdev/memory/strict` 启用。执行日志今天空 + 工作区实质变更 ≥ 2 或命中里程碑白名单 → `exit 2` 阻塞 Stop，Claude 必须落盘才能结束。

里程碑白名单由 `hooks/lib/milestone.sh` 统一维护，覆盖 Spec Kit、ADR、迭代/Sprint、PRD/架构/设计、根目录关键文档、数据库 migration、API/协议契约等。

阻塞带 `stop_hook_active` 保护不会无限循环。`rm .kdev/memory/strict` 关闭。

### 5. PostToolUse hook —— 里程碑联动

Claude 用 `Write/Edit/MultiEdit/NotebookEdit` 命中里程碑白名单时立刻提醒追加 Step。日常源码编辑不打扰。

### 6. PreCompact hook —— 压缩前写盘

会话即将被压缩时（`/compact` 或自动触发），写一个 `.kdev/memory/checkpoints/压缩前-YYYY-MM-DD-HHMMSS.md`，内容是今天所有 `.kdev/memory/` 核心文件的原文复制 + 工作区快照。**压缩后细节丢了也能回读原件。**

7 天后自动清理。如需长期保留某个 checkpoint，手工 `mv` 出 `checkpoints/` 目录。

### 7. SessionEnd hook —— 兜底警告

会话真正结束时（客户端关闭、切项目），若执行日志今天空 + 工作区有变更 → 写 `.kdev/memory/WARN-未记录-YYYY-MM-DD.md`。下次进入项目时 SessionStart 的注入摘要会把它显眼列在顶部。

## `.kdev/memory/当前状态.md` 的 YAML frontmatter

状态文件既要人可读，又要脚本可读。格式：

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

（自由文本 body：正在做什么、最近决策、预期下一步）
```

SessionStart hook 读 frontmatter 秒报项目状态。**每次完成 Step 都要顺手更新 frontmatter**（至少改 `current_step` + `last_updated`）。

已有项目的 `当前状态.md` 没 frontmatter 也能工作（hook fallback 到"无 frontmatter"模式）。

## 更新
```bash
claude plugin update kdev-memory@kdev-agents
```

## 使用

### 初始化（新项目首次使用）
> "给这个项目建立工程记忆"

### 日常（自动，无需干预）
CLAUDE.md 触发规则段让智能体在每步完成后自动记录。

### 每日汇总
> "写今天的总结" / "生成每日汇总" / "交接给明天"

### 启用严格模式（推荐长流程项目）
```bash
touch .kdev/memory/strict
```

### 恢复跨会话上下文
新会话直接开问"昨天做到哪了" / "继续上次的工作" —— SessionStart 注入会让 Claude 立刻给出上下文概览。

## 验证 hook 是否生效

```bash
# 1. 确认插件启用
grep -A3 enabledPlugins ~/.claude/settings.json

# 2. 手动跑 SessionStart 看注入
bash ~/.claude/plugins/marketplaces/kdev-agents/plugins/kdev-memory/hooks/session-start-brief.sh < /dev/null

# 3. 手动跑 Stop hook 看输出
bash ~/.claude/plugins/marketplaces/kdev-agents/plugins/kdev-memory/hooks/stop-check.sh < /dev/null

# 4. 开调试模式跑一轮，观察所有 hook 触发日志
claude --debug
```

## .kdev/ 目录结构

```
.kdev/
├── MIGRATED-YYYY-MM-DD.md     # 自动迁移记录（0.2.0 → 0.3.0，一次性）
└── memory/                    # kdev-memory 的全部产物
    ├── 当前状态.md             # 工作状态单一真相源（带 YAML frontmatter）
    ├── 决策日志.md             # Q-NNN（当前季度；老条目切到 归档/）
    ├── 踩坑日志.md             # G-NNN（当前季度；每条带 triggers: [...] 供智能召回）
    ├── 执行日志.md             # 每步记录 + 双评分 + triggers（当前月；老条目切到 归档/）
    ├── 每日汇总/               # YYYY-MM-DD.md
    ├── 改进建议.md             # R-NNN（喂给未来 skill 作者；**不切档**，保完整）
    ├── 方法论铁规.md           # 可选，业务规则择机迁到项目根 constitution.md/spec.md
    ├── 归档/                   # 长项目切档产物（0.4.0+）
    │   ├── 执行日志-YYYY-MM.md       # 按月归档（如 执行日志-2026-03.md）
    │   ├── 踩坑日志-YYYYQN.md        # 按季度归档（如 踩坑日志-2026Q1.md）
    │   └── 决策日志-YYYYQN.md        # 按季度归档
    ├── strict                  # 可选空文件，touch 后启用 Strict 阻塞
    ├── WARN-未记录-*.md        # SessionEnd hook 自动生成的兜底警告
    ├── state/                  # hook 运行时状态
    │   └── trigger-sessions.json  # UserPromptSubmit 去重（60min TTL）
    └── checkpoints/            # PreCompact hook 自动生成（7 天 retention）
        └── 压缩前-YYYY-MM-DD-HHMMSS.md
```

**归档机制**（0.4.0+）：长项目主文件会膨胀，Claude 在 Stop hook 看到主文件最早条目跨月（执行日志）或跨季度（踩坑/决策日志）时会 📦 提醒用户切档。详见 SKILL.md 的「文件切档与归档」章节。踩坑日志归档后仍参与 triggers 召回——老坑也要防重踩。

项目级 spec 文件（UserPromptSubmit 自动扫描，存在即扫）：
- `constitution.md` / `spec.md` / `principles.md` / `AGENTS.md`（项目根）
- `.specify/constitution.md`（Spec Kit 新版）
- `docs/constitution.md` / `docs/principles.md`
