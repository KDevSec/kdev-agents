# fixtures 目录分工

本目录下有**两类 fixture**，给两条独立的 eval 线用：

## `project-state/` — trigger-match 召回测试 fixture

- **给谁用**：[`../evals.json`](../evals.json) 的 10 条 prompt
- **特点**：共享的**静态** `.kdev/memory/`——一套记忆被 10 个 prompt 反复读（测的是 hook 脚本的召回规则，不是 skill 行为）
- **修改原则**：只读，跑 hook 不会改动

内容：一个完整模拟的项目状态，包含：
- `.kdev/memory/踩坑日志.md` — G-012（pnpm）+ G-014（aiohttp）等带 triggers 的条目
- `.kdev/memory/执行日志.md` — Step 23（今日）+ Step 24（昨日）
- `.kdev/memory/方法论铁规.md` — commit 粒度 + API 设计
- `.kdev/memory/当前状态.md` — 带 YAML frontmatter
- `.kdev/memory/决策日志.md` — Q-001 / Q-008
- `constitution.md` — 项目宪章（带 frontmatter triggers）

## `skill-quality/eval-N-<name>/` — skill-creator eval fixture

- **给谁用**：[`../skill-quality/evals.json`](../skill-quality/evals.json) 的 8 条 eval
- **特点**：每个场景一个独立的 `target-project/`，subagent 跑测时 **`cp -r`** 到 sandbox 里去改（fixture 保持只读）
- **修改原则**：fixture 只读；sandbox 在 `workspace-*/` 里由 subagent 自由修改（workspace 已 gitignored）

当前 8 个场景：

| 目录 | 场景 | 类型 |
|---|---|---|
| `eval-0-init/` | 初始化：空项目 → 建骨架 + CLAUDE.md + Q-001 | core-flow |
| `eval-1-daily-summary/` | 每日汇总：从 `.kdev/memory/` 聚合当日条目 | core-flow |
| `eval-2-rule-upgrade/` | 规则升级：R-NNN 升到项目宪章 | core-flow |
| `eval-3-archive/` | 切档归档：跨月/跨季度搬老条目 | core-flow |
| `eval-4-merge-conflict/` | 边缘：CLAUDE.md 已有同名章节合并策略 | edge-case |
| `eval-5-missing-data/` | 边缘：`.kdev/memory/` 今日无条目坦白报告 | edge-case |
| `eval-6-cross-session-resume/` | 核心：新会话回读上下文"昨天做到哪了" | core-flow |
| `eval-7-warn-file/` | hook 交互：处理 SessionEnd hook 留的 WARN-未记录-*.md | hook-interaction |

## 为什么分两套（而不是用同一份 fixture）

本质区别是**测什么**：

- **project-state**：测"给定 prompt，hook 脚本扫 triggers 是否命中"——需要**静态丰富**的数据（多种条目类型、带 triggers / 不带 triggers、代码块混入等，让召回规则被充分触发）
- **skill-quality/eval-N**：测"给定 prompt，skill 按规范做出的产出是否合格"——每个场景需要**独立最简**的初始状态（不污染其他 eval、边缘情况精准设计）

共用同一份 fixture 会让两类测试互相耦合——加一个 G-NNN 满足召回测试可能干扰 skill 测试的基线；改 skill 测试的 Step 又可能影响召回命中率。分开后两条线各自演进互不干扰。

## 新增 fixture 的约定

**加入 project-state**（为 trigger-match 测试服务）：
- 条目要有明确的 `triggers:` 字段
- 加条目前查 `evals.json` 确认新测试 prompt 需要什么
- 条目写得**有代表性而非真实**（三种 triggers 格式覆盖 / sanitize 陷阱等）

**加入 skill-quality**（为 skill 行为测试服务）：
- 建 `eval-N-<short-name>/target-project/` 目录
- 内部放一个**完整但最简**的项目状态（.kdev/memory/ + CLAUDE.md + 少量源码）
- 在 `../skill-quality/evals.json` 里加对应 eval 定义（prompt + fixture 路径 + assertions）
- N 严格递增，name 用 kebab-case
