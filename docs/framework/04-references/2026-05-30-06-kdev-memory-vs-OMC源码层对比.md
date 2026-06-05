# kdev-memory vs OMC 源码层对比 + 借鉴清单

> 日期：2026-05-30
> 状态：**源码级实地对比报告**
> 关联：[2026-05-30-05 数字员工架构补遗](2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md) + [2026-05-30-02 5 仓综合报告](2026-05-30-02-5仓源码调研综合报告.md)
> 目的：以 OMC 为 Claude Code plugin 运行时底座的前提下，找出 KDev 现有 plugin 跟 OMC 在源码实现上的差异，决定哪些 OMC 模块可借鉴

---

## 一、调研范围

直接读两边源码：
- `_repos/oh-my-claudecode/src/` (TypeScript, 30+ 子目录)
- `plugins/kdev-memory/` (Python + Markdown, 8 顶层目录)

不再依赖 agent 二手分析，全部一手摸到代码层。

---

## 二、架构层级对比（一张总图）

```
                   kdev-memory                          OMC
                   ─────────────                       ─────
.claude-plugin/    plugin.json                          plugin.json + marketplace.json + .mcp.json
language           Python 3                            TypeScript (编译到 dist/, 通过 bridge/*.cjs 加载)
mcp-server         ❌ 无                                ✅ 单 server bridge/mcp-server.cjs 暴露 ~50 tool
runtime entry      hooks/run-python-hook.cmd            bridge/cli.cjs (3.3MB compiled)
storage format     markdown 主存 + YAML frontmatter     混合：markdown (notepad) + JSON (memory/state)
hook count         6 (SessionStart/UserPromptSubmit/    7 注册点（同 Claude Code 内置 hook）
                   PostToolUse/PreCompact/SessionEnd/   + 内部模块化更细
                   Stop)
hook concept dirs  ❌ 无 hook 概念目录                   ✅ 28+ src/hooks/<concept>/index.ts
HUD                ❌ 无                                ✅ src/hud/ (16 个 ts 文件 + statusLine 集成)
state management   `当前状态.md` (frontmatter)           src/features/state-manager/ + .omc/state/{mode}-state.json
                                                       + .omc/state/sessions/{sessionId}/
                                                       + SQLite job-state-db
modes              ❌ 无显式模式概念                     ✅ 8+ 显式 mode（autopilot/ralph/team/ultrawork/...）
agents/            ❌ 不属于本 plugin（KDev staff 才有）  ✅ agents/ 18 个 agent.md（frontmatter + 角色定义）
skill count        2 skill（kdev-memory + workspace）   40 skill（按 plugin.json 列出 39 + docs-style）
commands           2 (distill / weekly)                30+
shared utilities   hooks/lib/ 19 个 .py helper          src/lib/ + src/utils/ 共享工具库
seminar/missions   ❌ 无                                ✅ 有培训材料 + 复用任务模板
shellmark         ❌ 无                                ✅ shell 执行审计 + index
.clawhip          ❌ 无                                ✅ event telemetry capture
```

---

## 三、文件结构对比

### 3.1 kdev-memory 全貌

```
plugins/kdev-memory/
├── .claude-plugin/plugin.json
├── hooks/
│   ├── hooks.json                    # 6 hook 注册
│   ├── session-start-brief.py        # SessionStart: brief 注入
│   ├── user-prompt-trigger.py        # UserPromptSubmit: triggers 召回
│   ├── post-write-check.py           # PostToolUse: 里程碑联动
│   ├── pre-compact-check.py          # PreCompact: 写盘
│   ├── session-end-check.py          # SessionEnd: WARN 兜底
│   ├── stop-check.py                 # Stop: 软提醒
│   ├── run-python-hook.cmd           # Windows 跨平台 launcher
│   └── lib/                          # 19 个 helper 模块
│       ├── trigger-match.py          # 触发匹配核心
│       ├── frontmatter.py            # YAML frontmatter 解析
│       ├── distill.py                # 蒸馏导出
│       ├── distill_trigger.py        # 蒸馏阈值检测
│       ├── promote_scan.py           # promote 候选扫描
│       ├── milestone.py              # PostToolUse 里程碑判断
│       ├── checkpoint.py             # PreCompact 快照
│       ├── missing_summaries.py      # 漏汇总检测
│       ├── step_completeness.py      # Step 四段闸门
│       ├── step_id.py                # Step ID 生成（带分支前缀）
│       ├── claude_md_lint.py         # CLAUDE.md 漂移检测
│       ├── memory_config.py          # config.yaml 加载
│       ├── archive_hint.py           # 归档提示
│       ├── worktree_link.py          # secondary worktree 处理
│       ├── sanitize.py               # 蒸馏前 sanitize
│       ├── promote-list.py           # promote list 助手
│       ├── migrate.py                # v0.x 防御性迁移
│       ├── migrate-v0.7.py           # 旧版迁移
│       └── weekly.py                 # 周报
├── skills/
│   ├── kdev-memory/SKILL.md          # 主 skill（含 references/）
│   └── kdev-memory-workspace/        # eval 用工作区
├── commands/
│   ├── kdev-memory-distill.md
│   └── kdev-memory-weekly.md
├── agents/                           # （内容待查，可能是空目录）
├── evals/                            # 评估用例
├── tests/                            # 单元测试
├── CHANGELOG.md
└── README.md
```

### 3.2 OMC 全貌（精简）

```
oh-my-claudecode/
├── .claude-plugin/
│   ├── plugin.json                   # 39 skill 路径 + mcpServers + commands
│   └── marketplace.json
├── .mcp.json                         # 单 server "t" 指向 bridge/mcp-server.cjs
├── CLAUDE.md                         # 自身 OMC:START..END 标记，注入到用户 CLAUDE.md
├── AGENTS.md                         # 子代理执行协议
├── agents/                           # 18 个 .md（executor/planner/architect/...）
├── commands/                         # 30+ .md（slash 命令路由到 skill）
├── skills/                           # 40 个 SKILL.md
│   ├── ralph/ autopilot/ team/ ...
│   ├── hud/                          # HUD 配置 skill
│   ├── learner/ skillify/            # 自演进 skill
│   └── ...
├── hooks/                            # 命令行入口（bridge 暴露的 cli）
├── bridge/
│   ├── cli.cjs                       # 3.3MB 主入口
│   ├── mcp-server.cjs                # 983KB MCP server
│   ├── team-mcp.cjs                  # 693KB team MCP
│   ├── runtime-cli.cjs               # 351KB
│   └── team-bridge.cjs               # 81KB
├── src/                              # TypeScript 源码（30+ 子目录）
│   ├── tools/                        # 22 个 MCP tool ts 文件
│   │   ├── notepad-tools.ts         (notepad_read / write_priority / working / manual)
│   │   ├── memory-tools.ts          (project_memory_read / write / add_note / add_directive)
│   │   ├── state-tools.ts           (state_read / write / clear / list_active / get_status)
│   │   ├── shared-memory-tools.ts
│   │   ├── session-history-tools.ts
│   │   ├── skills-tools.ts
│   │   ├── lsp-tools.ts
│   │   ├── ast-tools.ts
│   │   └── ...
│   ├── hooks/                        # 28+ hook 概念模块
│   │   ├── notepad/index.ts         (549 行实现 3-layer notepad)
│   │   ├── project-memory/index.ts
│   │   ├── mode-registry/index.ts
│   │   ├── keyword-detector/index.ts
│   │   ├── pre-compact/
│   │   ├── learner/
│   │   ├── persistent-mode/
│   │   └── ...
│   ├── features/                     # 内部功能模块
│   │   ├── state-manager/index.ts   (统一 state 接口)
│   │   ├── notepad-wisdom/           (plan-scoped notepad，4 类目)
│   │   ├── magic-keywords.ts
│   │   ├── model-routing/
│   │   ├── verification/
│   │   ├── delegation-routing/
│   │   ├── boulder-state/
│   │   └── ...
│   ├── hud/                          # 16 个 ts 文件（statusline）
│   │   ├── index.ts
│   │   ├── render.ts
│   │   ├── omc-state.ts
│   │   ├── usage-api.ts
│   │   ├── mission-board.ts
│   │   └── elements/
│   ├── lib/                          # 共享工具
│   │   ├── worktree-paths.ts        (路径解析 + worktree 边界校验)
│   │   ├── atomic-write.ts          (原子写)
│   │   ├── file-lock.ts             (文件锁)
│   │   └── ...
│   ├── team/                         # team-pipeline 实现
│   ├── mcp/                          # MCP server runtime
│   └── ...
├── seminar/                          # 培训材料（slides + notes）
├── missions/                         # 可复用任务模板
├── shellmark/                        # shell 执行审计
└── .omx/ / .clawhip/                 # 自身 dogfood 用的 OMC 运行时
```

### 3.3 量化对比

| 维度 | kdev-memory | OMC |
|---|---|---|
| 顶层目录 | 8 | 26+ |
| 源码文件数 | ~30 .py | ~300 .ts |
| Hook 注册点 | 6 | 7 |
| Hook 概念模块 | 0（lib/ 是 helper 不是 hook 概念）| 28+ |
| MCP tool 数 | 0 | ~50（22 tool 文件，每文件多个 tool）|
| skill 数 | 2 | 40 |
| slash 命令数 | 2 | 30+ |
| HUD | 无 | 完整（16 个 ts + statusLine）|
| state 文件类型 | 1 (markdown frontmatter) | 6+ (per-mode JSON / per-session / mission / job / team / 遥测) |

---

## 四、实现技术栈对比

### 4.1 kdev-memory：Python + Markdown

| 选择 | 表现 |
|---|---|
| **语言** | Python 3 + 标准库 + PyYAML | hook 启动 ~50-200ms（cold start） |
| **存储** | markdown 主存（YAML frontmatter for schema）| 用户可手改、版本控制友好、grep 即可召回 |
| **架构** | hook 脚本 + hooks/lib/ 模块化 helper | 6 hook 各自薄壳，核心逻辑沉到 lib |
| **跨平台** | run-python-hook.cmd 桥接 Windows GBK 编码 | 跨 Win/Mac/Linux 良好（_utf8.force_utf8_stdio()） |
| **migration** | 入口必跑 `migrate.kdev_memory_migrate()` 防御 | 老项目升级自动兼容 |

### 4.2 OMC：TypeScript + 多 mcp-server + 混合存储

| 选择 | 表现 |
|---|---|
| **语言** | TypeScript → compiled .cjs (bundle 后 3.3MB cli + 983KB mcp-server) | Node 启动 ~100-300ms |
| **存储** | mixed: `.omc/notepad.md` (markdown 3-section) + `.omc/project-memory.json` (JSON 6-section) + `.omc/state/{mode}-state.json` per-mode + SQLite job-state-db | 强 schema + 类型安全；但用户手改成本高（JSON 没有 narrative）|
| **架构** | tools/hooks/features/hud/lib 分层；每个概念有独立目录 + types.ts + index.ts + __tests__/ | 工程级、可维护、可单测；编译开销大 |
| **MCP** | 单 MCP server 暴露 ~50 个 tool | Claude 可显式调用工具操作记忆，affordance 强 |
| **HUD** | statusLine 集成（写到 ~/.claude/hud/omc-hud.mjs）| 用户实时可见运行时状态 |

### 4.3 设计哲学对比

| 哲学 | kdev-memory | OMC |
|---|---|---|
| **用户主权** | markdown 文件用户可读可改可手编 | JSON 文件难手改，依赖 MCP tool API |
| **代码量 vs 配置量** | 代码少 + 配置约定多（CLAUDE.md 接口契约） | 代码多 + 行为隐藏在 binary cjs 后 |
| **可调试性** | hook 脚本直接 `python xxx.py` 跑 | bridge cjs 是 bundle 后产物，需要源码层 |
| **Affordance** | Claude 用 Read/Write/Edit 通用工具读写文件 | Claude 用专门 MCP tool（notepad_read 等）|
| **架构态度** | 数据 + 协议优先（接口契约 → schema） | 工具 + 模块优先（每个 hook 是独立模块）|

---

## 五、功能 gap 矩阵

### 5.1 kdev-memory 有 / OMC 无

| 功能 | kdev-memory 做法 | OMC 是否有 |
|---|---|---|
| **F-NNN skill 反馈通道**（5 类语义 + verbatim 原话）| skill-feedback.md + subject 三级推断 + 评分裂解 | ❌ 无 |
| **subject 三级路由 + unknown fallback** | L1/L2/L3 推断 + 蒸馏切片按 subject | ❌ 无 |
| **Step 四段闸门**（执行事实 / 模型自评 / 用户评分 / 评分差异）| step_completeness.py 校验 | ❌ 无（OMC 用 PRD 模型完成率，不是评分）|
| **每日汇总从文件聚合** | session-end-check 检测漏汇总 + skill 触发聚合 | ❌ 无（OMC 用 mission-state / session state）|
| **接口契约化 CLAUDE.md 漂移检测** | claude_md_lint.py 扫各 hook 标签 | ⚠️ OMC 有 OMC:START..END 标记升级机制，但没 lint |
| **promote 沉淀通道**（subject=project 走人工选→ docs/）| /kdev-memory-distill 双路径之一 | ❌ 无 |
| **markdown 切片蒸馏**（dataset-full / misalignment / by-subject）| distill.py + 三 markdown 切片包 | ❌ 无 |
| **自动蒸馏阈值检测**（7d AND 数据增长）| distill_trigger.py + SessionStart Popen 后台跑 | ❌ 无 |
| **subagent 落盘两档（hybrid/inline）** | memory_config.yaml 切换 | ❌ 无（OMC 不区分）|
| **跨 worktree 软链 + step ID 分支前缀** | worktree_link.py + step_id.py | ⚠️ OMC 有 worktree-paths.ts 路径解析但不分支 ID |
| **按月/季度归档切档** | archive_hint.py 提醒 | ❌ 无 |
| **每步评分双轨（模型自评 + 用户评分）+ misalignment 蒸馏** | step_completeness + dataset-misalignment.md | ❌ 无（OMC 评分体系不同——是 PRD passes:true/false）|

**结论**：kdev-memory **不是 OMC 的子集**——它有大量 OMC 没做的"工程过程记忆 + 评分 + 蒸馏"独家能力。

### 5.2 OMC 有 / kdev-memory 无

| OMC 模块 | OMC 实现 | KDev 是否需要 |
|---|---|---|
| **Notepad 三层**（priority always-loaded / working 7d auto-prune / manual never-prune）| src/hooks/notepad/index.ts 549 行 + src/tools/notepad-tools.ts MCP tool | ⚠️ 部分需要（详见 §6.1） |
| **Project Memory** 类目化 JSON（techStack/build/conventions/structure/notes/directives）| src/hooks/project-memory/index.ts | ❌ KDev 用 markdown narrative，不抄 JSON 类目 |
| **HUD statusLine** | src/hud/ 16 ts 文件 + ~/.claude/hud/omc-hud.mjs | ✅ **强烈建议借**（详见 §6.2） |
| **Mode Registry**（autopilot/ralph/team/ultrawork/... 8+ 模式 + per-mode state） | src/hooks/mode-registry/index.ts + state-tools | ⚠️ **部分需要**（KDev staff 需要类似概念但词表不同） |
| **State Manager 统一接口**（local + global state + 缓存 + atomic write + 5s TTL）| src/features/state-manager/index.ts | ✅ **借**（KDev 当前是 markdown frontmatter，state 多了后必要）|
| **shellmark shell 审计** | shellmark/sessions/{id}/manifest.json + events/ + indexes/ | ⚠️ 看需求（CQO 监督可能用） |
| **`.clawhip` 事件遥测** | .clawhip/state/prompt-submit.json | ⚠️ 看需求 |
| **session-history-tools** + per-session state dir | src/tools/session-history-tools.ts + .omc/state/sessions/{sid}/ | ⚠️ KDev 当前 checkpoints/ 是合并的，per-session 隔离会更好 |
| **MCP tool 暴露**（让 Claude 显式调用而非直接 R/W file） | src/tools/*.ts 22 文件 | ⚠️ **可选**（详见 §7） |
| **`<!-- OMC:START -->...END -->` 标记法**（CLAUDE.md 安全升级替换） | CLAUDE.md 头部标记 | ✅ **强烈建议借**（详见 §6.3） |
| **atomic-write + file-lock**（并发安全） | src/lib/atomic-write.ts + src/lib/file-lock.ts | ✅ **强烈建议借**（详见 §6.4） |
| **Worker Preamble Protocol**（防 sub-agent 套娃） | src/agents/preamble.ts + agents/*.md 引用 | ✅ kdev-staff 必须借（kdev-memory 不需要） |
| **disallowedTools frontmatter**（agent read-only 硬约束） | agents/*.md frontmatter | ✅ kdev-staff 必须借 |
| **Skill keyword priority queue + magic-keywords.ts** | src/features/magic-keywords.ts + src/hooks/keyword-detector/index.ts | ⚠️ kdev-memory triggers 字面匹配已经类似，但 OMC 有优先级 |
| **agents/ 18 个角色定义** | agents/<name>.md 带 frontmatter (name/description/model/level/disallowedTools)| ✅ kdev-staff 用 |
| **Notepad Wisdom（plan-scoped 4 类目：learnings/decisions/issues/problems）**| src/features/notepad-wisdom/ | ⚠️ 跟 KDev 已有 G/Q/R 高度重叠，不抄 |
| **bridge MCP server 单 server 暴露全部 tool** | bridge/mcp-server.cjs | ✅ **强烈建议借**（Phase 2 跨平台必需，详见 §6.5） |
| **statusLine 集成 ~/.claude/settings.json** | hud skill 写 settings.json + omc-hud.mjs | ✅ 跟 §6.2 一起 |

---

## 六、强推荐借鉴的 5 项（按优先级）

### 6.1 ✅ Notepad working memory（部分借）

**OMC 实现**（`src/hooks/notepad/index.ts`）：

```
## Priority Context
<!-- ALWAYS loaded. Keep under 500 chars. Critical discoveries only. -->

## Working Memory
<!-- Session notes. Auto-pruned after 7 days. -->

## MANUAL
<!-- User content. Never auto-pruned. -->
```

**KDev 现状**：
- "Priority" 等价 = `当前状态.md` body + frontmatter
- "Working Memory" = ❌ 无
- "MANUAL" 等价 = 改进建议.md / 决策日志.md

**建议**：只借 **Working Memory** 一层 ——`.kdev/memory/notepad-working.md`，7 天自动清理，给 Claude 写"临时事项 / scratch"。priority / manual KDev 已用 当前状态.md 覆盖，不需重复。

**实施**：
- 新增 `hooks/lib/notepad_working.py`，照抄 OMC 的 prune 逻辑
- session-start-brief.py 把 working memory 最近 3 条注入 brief
- PostToolUse 触发自动写入临时事项（"刚改了 X 文件" 类微 reminder）

### 6.2 ✅ HUD statusLine（**强烈建议借**）

**OMC 实现**（`src/hud/index.ts` 1000+ 行）：
- 注册到 `~/.claude/settings.json` 的 `statusLine` 字段
- 实时显示：context 占用 / 当前 model / 当前 mode（ralph/autopilot/...）/ rate limit / 成本
- 多 preset：minimal / focused / full / status

**KDev 现状**：完全无。

**对 KDev 的价值**：
- 显示当前 Step ID（`main-19` 跨会话不丢）
- 显示当前阶段（来自 当前状态.md 的 phase）
- 显示未销账 G-NNN / 待处理 R-NNN 数
- 显示是否在 hybrid/inline 模式
- 显示距离上次蒸馏多久

**建议**：抄 OMC 的 HUD pattern 但写自己的 elements：

```typescript
// 抄 OMC hud 模块
// 但显示 KDev 自己的数据：
//   [Step main-19] | [pending: 3 G + 1 R] | [last distill: 5d] | [phase: 开发]
```

实施：单独开一个 `plugins/kdev-hud/` plugin（或 kdev-core 的子模块），不污染 kdev-memory。

### 6.3 ✅ `<!-- KDEV:START -->...END -->` CLAUDE.md 安全升级标记法

**OMC 实现**（CLAUDE.md 头尾）：

```markdown
<!-- OMC:START -->
<!-- OMC:VERSION:4.9.1 -->

# oh-my-claudecode - Intelligent Multi-Agent Orchestration
...
<!-- OMC:END -->
```

**KDev 现状**：CLAUDE.md 当前是手写段落，升级时只能 manual diff。

**建议**：所有 KDev plugin 写入 CLAUDE.md 时用 `<!-- KDEV:<PLUGIN_NAME>:START -->...END -->` 包裹。升级时整段替换，不破坏用户手写部分。

**实施**：
- claude_md_lint.py 已经在做"接口漂移检测"，扩展它支持 START..END 标记
- 升级 kdev-memory SKILL 时自动重写标记之间的内容
- 用户手写的内容放在标记**外**，永远不被覆盖

### 6.4 ✅ atomic-write + file-lock（并发安全）

**OMC 实现**（`src/lib/atomic-write.ts` + `src/lib/file-lock.ts`）：

```typescript
import { atomicWriteFileSync } from "../../lib/atomic-write.js";
import { lockPathFor, withFileLockSync } from "../../lib/file-lock.js";

withFileLockSync(lockPathFor(notepadPath), () => {
  atomicWriteFileSync(notepadPath, newContent);
});
```

**KDev 现状**：
- hooks 直接 `pathlib.Path.write_text()`，**无文件锁**
- secondary worktree + 多 hook 并发场景可能 race

**建议**：抄过来 Python 版：

```python
# hooks/lib/atomic_write.py
import os
import fcntl  # Unix
import tempfile

def atomic_write_text(path: Path, content: str) -> None:
    """原子写：先写 temp file 再 rename。"""
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(content, encoding='utf-8')
    os.replace(tmp, path)

@contextmanager
def file_lock(lock_path: Path):
    """fcntl.flock 实现的 advisory lock（Unix）。Windows 用 msvcrt."""
    ...
```

实施：4 hour 一个上午就能做完，避免未来出现并发写错乱的难调 bug。

### 6.5 ✅ MCP server 单 server 暴露（Phase 2 跨平台必需）

**OMC 实现**（`.mcp.json` + `bridge/mcp-server.cjs`）：

```json
{
  "mcpServers": {
    "t": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/bridge/mcp-server.cjs"]
    }
  }
}
```

暴露 ~50 tool 包括 notepad / project_memory / state / shared_memory / session_history 等。

**KDev 现状**：完全无 MCP server，Claude 只能用 Read/Write/Edit 工具操作 `.kdev/memory/` 文件。

**对 KDev 的价值**：
- 跨平台目标（Cursor / OpenCode / Qoder / TRAE）必经之路
- Affordance 更强——Claude 能调 `kdev_memory_recall(query, scope)` 而不是 grep 文件

**建议工具集**（v0.x 实施时定）：

```
kdev_memory_recall(query, scope?, limit?)        # 召回（替代 hook 自动注入）
kdev_memory_write_step(step_id, segments)        # Step 四段写入
kdev_memory_write_q(question, options)           # Q-NNN
kdev_memory_write_g(triggers, gotcha, fix)       # G-NNN
kdev_memory_write_r(rule, scope)                 # R-NNN
kdev_memory_write_f(verbatim, subject, type)     # F-NNN（评分裂解后）
kdev_memory_subject_infer(text, context)         # L1/L2/L3 推断
kdev_memory_distill(scope, mode)                 # 蒸馏命令
kdev_memory_daily_aggregate(date)                # 每日汇总
```

**实施路径**：v0.x 现在的 Python hooks 不动；新增 `kdev-memory-mcp-server`（Python FastAPI 仿 OpenMemory）作为 v1.x phase 2 跨平台准备。

---

## 七、可选借鉴的 3 项

### 7.1 ⚠️ State Manager 统一接口

**借的价值**：state 文件多了后（HUD state / distill state / brief cache / 等）统一抽象。

**何时借**：现在 KDev state 只有 当前状态.md，单一文件不需要 manager。等出现 3+ state 文件再借。

### 7.2 ⚠️ per-session state（`.omc/state/sessions/{sessionId}/`）

**借的价值**：多 worktree 并发不混。

**KDev 现状**：worktree_link.py 已经处理软链，但 state 还是合并的。

**何时借**：并发 worktree 场景频繁踩坑时再上。

### 7.3 ⚠️ MCP tool 暴露 vs hook 自动注入

**两种 affordance 对比**：

| affordance | 哪种 |
|---|---|
| Claude 主动 `kdev_memory_recall("X")` 显式调用 | MCP tool（OMC 模式）|
| UserPromptSubmit hook 拦截 prompt 自动注入 `<kdev-memory-recall>` | hook 模式（KDev 当前）|

**结论**：**两种并存最好**——hook 自动注入做 brief / triggers 命中召回；MCP tool 给 Claude 显式调用（写 Step / 评分 / 蒸馏 等）。

---

## 八、明确不借的 5 项

| 不借什么 | 理由 |
|---|---|
| **Project Memory JSON 类目**（techStack/build/conventions/structure/notes/directives） | KDev 哲学守 markdown narrative，不抄 JSON schema |
| **Mode Registry 8+ 模式** | OMC modes (autopilot/ralph/...) 是 OMC 自己 skill，KDev 没必要照搬词表 |
| **Notepad Wisdom (plan-scoped learnings/decisions/issues)** | KDev 已有 G/Q/R 全局编号体系，再加 plan-scoped 反而割裂 |
| **bridge/cli.cjs 3.3MB bundle** | KDev Python 直接跑就行，不需要 bundle |
| **AGENTS.md 全套 codex prompts schema** | KDev 不引入 codex / gemini provider routing（v0.x 单 Claude） |

---

## 九、整体借鉴清单（推荐落地顺序）

| 优先级 | 借鉴项 | 工作量 | 收益 |
|---|---|---|---|
| **P0 立即** | atomic-write + file-lock | 半天 | 防并发 race（无成本风险） |
| **P0 立即** | `<!-- KDEV:<PLUGIN>:START..END -->` 标记法 | 1 天 | CLAUDE.md 升级安全 |
| **P1 短期** | HUD statusLine（新开 kdev-hud plugin） | 1 周 | 实时反馈 KDev 状态（Step ID / 待销账 / 蒸馏倒计时） |
| **P1 短期** | Notepad working memory（7 天 auto-prune） | 2 天 | scratch 区，临时事项不污染主存 |
| **P2 中期** | kdev-memory-mcp-server（FastAPI 仿 OpenMemory） | 1-2 周 | Phase 2 跨平台前置 |
| **P3 长期** | per-session state（多 worktree 隔离） | 视需求 | 并发场景必要 |
| **P3 长期** | State Manager 统一接口 | 视需求 | state 文件多了后 |

---

## 十、kdev-staff（未来 plugin）必借的 OMC 模块

下面这些 OMC 模块**不属于 kdev-memory 范围**，是 **kdev-staff plugin 未来需要的**。列出来防止以后重复调研：

| 模块 | 路径 | 用途 |
|---|---|---|
| **Worker Preamble Protocol** | `src/agents/preamble.ts` | 阻止 sub-agent 套娃 |
| **agents/<name>.md frontmatter** | `agents/executor.md` 等 | agent 角色定义模板（name/description/model/level/disallowedTools）|
| **disallowedTools 字段** | agent frontmatter | read-only 评审员硬约束 |
| **team-pipeline 5 阶段** | `src/team/stage-router.ts` + `skills/team/SKILL.md` | plan→prd→exec→verify→fix |
| **Mode Registry** | `src/hooks/mode-registry/index.ts` | 显式 mode 注册 + state 文件命名 |
| **magic-keywords + priority queue** | `src/features/magic-keywords.ts` + `src/hooks/keyword-detector/index.ts` | skill 触发优先级 |
| **ralph PRD 模式** | `skills/ralph/SKILL.md` + state | 评审循环 PRD 驱动 |
| **self-improve 算法骨架** | `skills/self-improve/SKILL.md` | CQO 监督（plateau + circuit breaker 双信号）|

---

## 十一、未决问题

1. **HUD 单独开 plugin 还是塞进 kdev-core**？OMC HUD 是顶层 src/hud/，跟 plugin 同级；KDev 如果走 plugin 化，应该 kdev-hud 独立装
2. **MCP server 用 Python 还是 Node**？KDev plugin 主体 Python，但 MCP 主流 server 是 Node/FastMCP；如果加 Node 依赖会复杂化用户安装
3. **atomic-write 用 Python 哪个库**？stdlib `os.replace` 足够；file-lock 用 `fcntl`（Unix）+ `msvcrt`（Windows）跨平台
4. **notepad working memory 跟 G-NNN 重叠吗**？G-NNN 是踩坑（永久），working memory 是临时事项（7 天），定位不冲突
5. **CLAUDE.md START..END 标记跟现有"接口契约段"如何对齐**？建议：把"接口契约段"全部包在 `<!-- KDEV:kdev-memory:CONTRACT:START -->...END -->` 里，升级时整段替换

---

## 十二、引用

### 12.1 kdev-memory 源文件
- `plugins/kdev-memory/hooks/hooks.json` — 6 hook 注册
- `plugins/kdev-memory/hooks/session-start-brief.py` — brief 注入入口
- `plugins/kdev-memory/hooks/user-prompt-trigger.py` — triggers 召回入口
- `plugins/kdev-memory/hooks/lib/trigger-match.py` — 召回核心
- `plugins/kdev-memory/hooks/lib/distill.py` — 蒸馏导出
- `plugins/kdev-memory/skills/kdev-memory/SKILL.md` — 主 skill

### 12.2 OMC 源文件
- `_repos/oh-my-claudecode/.claude-plugin/plugin.json` — 39 skill + mcpServers + commands
- `_repos/oh-my-claudecode/.mcp.json` — 单 server
- `_repos/oh-my-claudecode/src/tools/notepad-tools.ts` — MCP tool 实现
- `_repos/oh-my-claudecode/src/tools/memory-tools.ts` — project_memory MCP tool
- `_repos/oh-my-claudecode/src/tools/state-tools.ts` — state MCP tool（开头 120 行已细读）
- `_repos/oh-my-claudecode/src/hooks/notepad/index.ts` — 549 行 notepad 三层实现
- `_repos/oh-my-claudecode/src/features/state-manager/index.ts` — 统一 state 接口
- `_repos/oh-my-claudecode/src/features/notepad-wisdom/index.ts` — plan-scoped notepad
- `_repos/oh-my-claudecode/src/hud/index.ts` — HUD 主入口
- `_repos/oh-my-claudecode/CLAUDE.md` — `<!-- OMC:START -->..END` 标记示范

### 12.3 KDev 内部文档关联
- v3.0 5 层架构：[01-design/2026-04-08-03-KDev融合架构设计.md](../01-design/2026-04-08-03-KDev融合架构设计.md) §6
- 双轨提案：[2026-05-30-03](2026-05-30-03-KDev记忆架构对齐分析与双轨提案.md)
- 数字员工架构补遗：[2026-05-30-05](2026-05-30-05-数字员工架构补遗-多agent+自演进+跨IDE.md)

---

## 十三、变更记录

| 日期 | 改动 |
|---|---|
| 2026-05-30 | v0.1：源码层实地对比 + 借鉴清单（5 强推 + 3 可选 + 5 不借）|
