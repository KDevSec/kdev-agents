# kdev-memory CHANGELOG

## 0.2.0 — 2026-04-19

由一份用户反馈驱动的重大升级：Spec Kit 等长流程跑完后会话自然 idle，Stop hook
的 stdout 软提醒永远没有下一轮上下文可以被读到，导致 `.kdev/执行日志.md` 全天空白。
本版本从**六层防线**角度补齐这个缝隙，并引入**状态结构化（YAML frontmatter）**让脚本
和 Claude 都能结构化读写当前项目状态。

### 六层防线（按会话时序）

1. **SessionStart hook** —— 开局注入 `<kdev-memory-brief>` 摘要（WARN / checkpoint / 今日进度 / frontmatter 状态 / 最近 Step+Q+G）
2. **Stop hook** —— 软提醒（今天无汇总 / 汇总过时 / 执行日志今天空）
3. **Strict 模式（opt-in）** —— `touch .kdev/strict` 启用条件阻塞
4. **PostToolUse hook** —— 命中里程碑白名单时提醒追加 Step
5. **PreCompact hook** —— 压缩前写 `.kdev/checkpoints/压缩前-TS.md` 快照（7 天 retention）
6. **SessionEnd hook** —— 会话真正结束时写 `.kdev/WARN-未记录-*.md` 兜底警告

### 新增

- **Strict 模式（opt-in）**：项目根 `touch .kdev/strict` 后启用。执行日志今天空 +
  工作区实质变更 ≥ 2 个文件（或命中里程碑白名单）→ Stop hook `exit 2` 阻塞，
  Claude 必须先落盘才能结束会话。带 `stop_hook_active` 保护避免无限循环。
  `rm .kdev/strict` 即可关闭。
- **PostToolUse hook**（`hooks/post-write-check.sh`）：Claude 用
  `Write/Edit/MultiEdit/NotebookEdit` 命中里程碑白名单时立刻注入软提醒。
  日常源码编辑不打扰。
- **SessionEnd hook**（`hooks/session-end-check.sh`）：会话真正结束时，若执行
  日志今天空 + 工作区有变更 → 写 `.kdev/WARN-未记录-YYYY-MM-DD.md` 兜底警告
  文件，列出变更快照。下次进入项目时 CLAUDE.md 触发规则段会让 Claude 看到并
  提醒补记。
- **SessionStart hook**（`hooks/session-start-brief.sh`）：新会话启动时，通过
  `hookSpecificOutput.additionalContext` 注入 `<kdev-memory-brief>` 摘要。
  按 `source` 字段分档：`startup`/`clear` 完整摘要（待处理 WARN/checkpoint +
  今日进度 + 状态字段 + 最近条目）；`resume` 精简；`compact` 只提醒 checkpoint
  在哪。Claude 开局即知项目全景，不用等用户提"先看下昨天做到哪了"。
- **PreCompact hook**（`hooks/pre-compact-check.sh`）：会话被压缩前（auto 或
  `/compact` 手动触发）写一个 `.kdev/checkpoints/压缩前-YYYY-MM-DD-HHMMSS.md`
  快照——内含今天 `.kdev/` 核心文件原文复制 + 工作区 `git status -uall`。
  压缩后 Claude 即便丢失上下文也能 Read 此文件回读细节。7 天后自动清理
  （`hooks/lib/checkpoint.sh` 的 retention 逻辑）。
- **`.kdev/当前状态.md` YAML frontmatter schema**：状态文件引入结构化字段
  （`phase` / `iteration` / `current_step` / `last_updated` / `pending_decisions` /
  `unresolved_gotchas`），body 保留自由文本。SessionStart hook 直接读 frontmatter
  秒报项目状态给 Claude，不再靠 fuzzy 解析自由文本。实现：`hooks/lib/frontmatter.sh`
  提供 `read_state_field` / `has_state_frontmatter`（python3 优先，bash fallback）。
  兼容旧仓库：没 frontmatter 也能工作。
- **stdin hang 保护**：已有三个 hook（stop/session-end/post-write）的 stdin 读取
  加 `timeout 1` 超时，避免 Claude Code 管道未 EOF 时永久 hang（参考 OMC issue #240
  同类问题）。
- **里程碑白名单统一维护**（`hooks/lib/milestone.sh`）：单一真相源，stop-check
  与 post-write-check 共同 source。覆盖：
  - Spec Kit：`specs/**/*.md`、`specs/**/contracts/*.{yml,yaml}`
  - 迭代 / Sprint：`docs/iterations/**`、`docs/sprints/**`、`docs/sprint-*.md`、`docs/迭代*`
  - ADR / 决策：`docs/adr/**`、`docs/decisions/**`、`adr/*.md`、`adrs/*.md`
  - 架构 / 设计 / PRD / 需求：`docs/architecture/**`、`docs/design/**`、`docs/设计*`、
    `docs/prd/**`、`docs/PRD*`、`docs/requirements/**`、`docs/需求*`
  - 根目录关键文档：`ARCHITECTURE.md`、`ROADMAP.md`、`MIGRATION.md`、
    `CHANGELOG.md`、`DECISIONS.md`
  - 数据库 migration：`migrations/**`、`db/migrate/**`、`db/migrations/**`、
    `prisma/migrations/**`、`supabase/migrations/**`、`alembic/versions/*.py`
  - API / 协议契约：`openapi.{yml,yaml,json}`、`api/openapi.*`、
    `schema.graphql`、`*.proto`、`proto/**`
  - 工程记忆自己的硬规：`.kdev/方法论铁规.md`
- **SKILL.md 触发规则段**：新增"进入项目先处理 `.kdev/WARN-未记录-*.md`"条目，
  促使 Claude 不跳过上次会话留下的兜底警告。

### 变更

- Stop hook 计数逻辑：`.kdev/` 内部自维护文件（除 `方法论铁规.md`）不计入
  "实质变更"，避免 `touch .kdev/strict` 本身触发阻塞。
- README 重写 Hook 章节，分四层防线叙述（Stop 软提醒 / Strict 阻塞 /
  PostToolUse 联动 / SessionEnd 兜底），加入验证方式和新会话自检 prompt。
- SKILL.md 的 Hook 章节从"外部 `settings.json` 样板"改为"插件自带三层" 描述，
  并说明三层缺一不可的原因。

### 兼容性

- 0.1.x 行为保持不变（Stop 软提醒的四种状态检查原样保留）。
- 新增 hook 默认行为都是"静默或软提醒"，不会影响现有用户；Strict 阻塞必须
  用户主动 `touch .kdev/strict` 才启用。

---

## 0.1.1 — 2026-04-16

- Stop hook 新增 `汇总过时` 检测：每日汇总生成后若源文件（执行/决策/踩坑/改进）
  又有更新，提醒 Claude 追加到汇总而不是覆盖。
- 去掉 Stop hook 冗余的 `matcher: "*"` 字段。

## 0.1.0 — 2026-04-16

- 首次发布工程记忆制度插件：`.kdev/` 目录结构 + SKILL.md + Stop hook
  四态软提醒（无 `.kdev/` / 无汇总 / 执行日志空 / 汇总过时）。
