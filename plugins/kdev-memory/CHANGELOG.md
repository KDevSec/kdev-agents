# kdev-memory CHANGELOG

## [0.19.1] - 2026-06-30

对齐 ieidev-team 的两条真 gap（roadmap P1b / P2 配套 D4），均通用、低风险、TDD（520 passed）。

### ✨ hook wrapper 加固（P1b，对齐 ieidev 0.5.0）

`run-python-hook.cmd` 跨平台健壮性：
- 行尾改 CRLF + 新增 `.gitattributes` 锁 `text eol=crlf`（LF 下 cmd.exe 忽略 `@echo off`/`REM` → 窗里刷命令文本，是 Windows GUI 闪窗刷屏根因之一）。
- cmd 块 ASCII-only + 双分支 `PYTHONUTF8=1`（GBK 控制台中文/emoji 不崩）。
- Unix 分支单行 + 尾 `#` 吃 CRLF 的 `\r` + 逐个 `--version` 探测跳 Win Store python3 死垫片 + 命中即 `exec`。
- polyglot 结构不变；实跑验证 bash 分支选对 python3、stdout 回传、exit 0。
- 注：Windows GUI 闪窗根因（Claude Code 没传 `CREATE_NO_WINDOW`）是上游 **not-planned**，本加固让其从"刷一屏命令"降到"干净一闪"；窗口能否彻底消需 Windows 实验闸定夺。

### ✨ PreCompact checkpoint 瘦身（D4，token 经济，对齐 ieidev）

`pre-compact-check.py` 的 checkpoint 从「全文复制 durable md」改为**指针模式**：durable 文件出一行 `<path>（N 行）`、`执行日志.jsonl` 出末条 record_id 指针，只保留并强化"未落盘易失信号（压缩后优先补记）"。叠加在 dual-read 之上不回退（今日态 md∪jsonl 双路保留）。

### 📌 升级须知

- 本版改了 hook/wrapper，需**刷新 marketplace** 才激活（G-004）。

## [0.19.0] - 2026-06-25

对齐 ieidev-team memory 的一批跟进（详见 [docs/skills/kdev-memory/roadmap.md](../../docs/skills/kdev-memory/roadmap.md)）：P0 回归修复 + P1 sync UX + P2 叙事 Step JSONL 主账迁移（采 C1 永久 dual-read）。全程 TDD，516 passed。

> 🧭 **场景定位**：kdev-memory = 单用户·跨会话召回；ieidev-team = 多 Agent·记忆共享。本批借 ieidev 的通用工程改进，在「多 agent 共享机制」上主动分叉（不跟 delegation/scope/events/handoffs/CQO；P2 选 C1 永久 dual-read 而非 ieidev 硬切）。详见决策 Q 20260625-173847。

### 🐛 P0：时间戳 ID 双认回归修复

v0.17（Q-020）起新记录改时间戳 ID（`Q 2026...` 空格分隔），但三处仍硬编码 `X-\d+`，导致 v0.17 后**所有新 Q/G/R/F 被这三处静默漏掉**。改用既有 `id_label_fragment` 双认：
- `weekly.py`：周报 Q/G/R 收录 + 踩坑「已解决」关联判定（修「所有踩坑误判未解决」污染周报/`unresolved_gotchas`）。
- `distill_trigger.py`：auto-distill 新 F/R 计数。
- `distill.py`：skill-feedback 切片双认时间戳形 F。

### ✨ P1：sync UX 三件套（对齐 ieidev 0.5.0）

- **init-local**：无 remote 但 `.kdev/` 非空 → SessionStart 自动 `git init` 建本地 nested 仓 + 首次 commit + 提醒建远程。
- **sync: off**：`kdev-sync.yml` 项目级永久静默开关（`is_sync_off` + `OPTOUT_HINT`）。
- **失败会话内引导**：pull/clone/init 失败不再只打 stderr，改输出 `<kdev-sync-reminder>` 中文引导。
- 保住 kdev 已有的 GCM 非交互三开关（0.18.3）+ UTF-8 subprocess 修复，未回退。

### 🏗️ P2：叙事 Step JSONL 主账迁移（C1 永久 dual-read）

叙事 Step 主账从 `执行日志.md` 迁到 `执行日志.jsonl`；决策/踩坑/改进/反馈/汇总/状态仍**永久 markdown 主存**。**C1 = 历史 `执行日志.md` 冻结、经 dual-read 永久兼容读，不迁存量、不退 md-read**（区别于 ieidev 的硬切）。决策 Q 20260625-173847。

- **Phase A 基座**：`step_log.py`（`append_step` 原子写 + `read_steps`/`steps_for_date` + `validate` 7 hard-gate）、`migrate_jsonl.py`（手动迁移 CLI，幂等、`_migrated_raw` 零丢失）、`scope.recorder_target_jsonl`。
- **dual-read**：`step_dualread.py` 合成器层把 jsonl record 投影成等价 md 喂既有 helper；11 个读 Step 的 reader 改读 `执行日志.md ∪ 执行日志.jsonl`，安全不变式「jsonl 空 → 行为字节级不变」。
- **Phase B**：step-recorder agent 改调 `append_step` 落 jsonl（剥 team 耦合的 delegation、保 dual-read 要的 score_diff）；新增 `daily_render.py` **承重墙**——从 jsonl 确定性渲染每日汇总，取代「LLM 翻多个 md 拼装」。
- **Phase C**：`archive_hint` 执行日志按月切档下线（jsonl append-only 无 rotation + md 冻结；决策/踩坑/改进季度切档照常）；SKILL + references 5 处 + P-C2 spec 按 C1 措辞对齐（spec→canonical 回写铁规）。

### 📌 升级须知

- 本版改了 hook/agent/lib，需**刷新 marketplace** 才激活（G-004：装入 ≠ 生效）。
- 升级后**新** Step 落 `执行日志.jsonl`，**历史** Step 留 `执行日志.md` 经 dual-read 仍读，**无需手动迁移**（存量迁移可选，手动跑 `hooks/lib/migrate_jsonl.py`）。
- checkpoint 瘦身（D4）本版未做，defer。

## [0.18.3] - 2026-06-25

**修复**：kdev-memory SessionStart bootstrap 触发 GCM「Connect to GitHub」弹窗

- `hooks/lib/kdev_sync.py` `_git()` 加 GCM 三开关（对齐 ieidev-team 0.4.7）：
  - env: `GIT_TERMINAL_PROMPT=0`、`GCM_INTERACTIVE=Never`
  - cmdline: `-c credential.interactive=false`
- 行为：已缓存 HTTPS 凭据的机器**不变**（正常 pull/clone/push）；无凭据机器上**静默失败**（stderr 走 `_git()` 返回值，bootstrap 上层 L108-141 已有容错），不再弹 GCM GUI。
- 新增 `tests/test_kdev_sync_noninteractive.py` 覆盖三开关。

## [0.18.2] — 2026-06-23

**commit-tracker 不再自举记忆目录：未初始化工程跑 `git commit` 不再凭空冒出 `.kdev/memory/`。**

### 🐛 修复

- **`hooks/commit-tracker.py` 漏存在性门控（核心修复）**：PostToolUse(Bash) hook 在检测到 `git commit` 后，未像其它 hook 那样先判断 `.kdev/memory/` 是否已存在，就直接调 `pending_commits.append(state_dir, …)`，而 [`lib/pending_commits.py:_write`](plugins/kdev-memory/hooks/lib/pending_commits.py) 里 `state_dir.mkdir(parents=True, exist_ok=True)` 会无条件建目录——于是**任何工程（哪怕从没初始化过 kdev-memory）只要跑过一次 `git commit`，根目录就冒出 `.kdev/memory/state/pending-commits.json`**，随后 SessionEnd / PreCompact 等 hook 接着往里写 `WARN-未记录-*.md`、`checkpoints/`、`state/.rating-setup-shown`，污染了与本插件无关的工程。现于 `main()` 里、确认是 git commit 之后、计算 `state_dir` 之前，加一道与 session-start-brief / session-end-check / pre-compact-check / post-write-check 一致的存在性门控：`if not (repo / ".kdev" / "memory").is_dir(): print(SUPPRESS); return 0`。未初始化工程静默退出，已初始化工程的 commit 累积功能不变。

### 🔍 全量审计（确认无第二处自举点）

逐一核查 `hooks/` 下所有 hook 及 `hooks/lib/` 的 `mkdir` 调用，确认除 commit-tracker 外**无第二处「未门控就 mkdir / 写 `.kdev/memory/`」的自举点**：

- **`lib/pending_commits.py` `_write()`** — `state_dir.mkdir(parents=True)`：唯一未门控的调用方就是 commit-tracker（本次已修）；其余调用方（`stop-check` / `session-start-brief`）只走 `read()` / `format_brief_hint()`（只读），且这两个 hook 自身已门控；step-recorder 的 `clear()` 仅在已初始化上下文（主会话 dispatch 时 `.kdev/memory/` 必已存在）运行。
- **`lib/skill_version.py` `write_cache()`** — `state_dir.mkdir(parents=True)`：唯一调用方 `session-start-brief.main()` 在 `if not kdev_dir.is_dir(): return 0` 门控**之后**才调 `detect_drift`；且 `detect_drift` 仅在 `current_skill_sha`（git log SKILL.md）非 None 时才写——双重安全。
- **`lib/step_id.py` `increment_counter()` / `_dup_index()`** — `state_dir.mkdir(parents=True)`：仅被 `mint_next_step_id` / `mint_record_id` 调用，调用方是 step-recorder subagent 与 distill，均在已初始化上下文运行；无任何未门控 hook 直接调它。
- **`lib/trigger-match.py` `save_dedup_state()`** — `STATE_FILE.parent.mkdir(...)`：`trigger-match.main()` 在 `if not KDEV_DIR.is_dir(): emit_suppress(); return 0`（line 523）门控之后才可能触达。
- **`lib/distill.py` `export_markdown_slices()`** — `out_dir.mkdir(...)`（导出目标目录，非 `.kdev/memory` 本身）：`distill.main()` 自身有 `if not kdev.is_dir(): return 2` 门控；且 distill 仅由 `/kdev-memory-distill` 用户命令或 auto-distill（经已门控的 `session-start-brief`）触发。
- **`lib/migrate_scope.py` `migrate_to_scoped()`** — `staff/<id>` / `shared/` 的 `mkdir`：函数自身先 `if not root.is_dir(): return result`（`.kdev/memory` 不存在即返回）；且本模块是**手动 CLI 迁移工具**（docstring 明示「手动调用，不自动跑」），无任何 hook 自动调用。
- **`lib/migrate.py` `kdev_memory_migrate()`** — `new_dir.mkdir(...)`：自身先 `if not kdev_dir.is_dir(): return`（`.kdev/` 不存在即返回），只在 `.kdev/` 已存在时才建 `.kdev/memory/`（迁移/补建语义，非「凭空」）。
- **`lib/kdev_sync.py` `bootstrap()`** — `kdev.parent.mkdir` + `git clone`：仅当 `kdev-sync.yml` 配了 `memory_repo` remote 时才 clone（用户显式配 sync remote 的合法路径，与本次 bug 不同类）。
- **`session-start-brief._rating_setup_hint()`（marker.parent.mkdir）/ `pre-compact-check` checkpoint_dir.mkdir** — 均在各自 hook 的存在性门控之后。

结论：`lib/` 里的 mkdir 调用本身无需改动——它们都在已门控的调用链下游（或自身带 `if not …is_dir()` 守卫、或仅手动 CLI / 用户显式命令触发）。根因只在 commit-tracker 这一处入口漏门。

### 🧪 测试

- 新增 `test_hook_does_not_bootstrap_kdev_memory_when_uninitialized`（TDD RED→GREEN）：在没 `.kdev/` 的临时仓里模拟一次 git commit 调 commit-tracker，断言事后 `.kdev/` 不存在、pending 为空。
- 调整 `test_hook_resilient_to_missing_state_dir`：原 setup 未建 `.kdev/memory/`（实为测了 bug 行为），现改为建 `.kdev/memory/` 但不建 `state/`——回归「已初始化工程缺 state 子目录 → append 自动补建」这一**仍应保留**的合法行为，与本次「未初始化工程不得自举」门控正交。

### 🐛 修复（续）：Windows 中文环境 subprocess 编码

**根因**：测试 helper 与库代码里的 `subprocess.run(..., text=True)` 未指定 `encoding`，在中文 Windows 上默认用 GBK（cp936）解码被调 hook / git 的非 ASCII 输出（中文 nudge、中文分支名、emoji 等），触发 `UnicodeDecodeError: 'gbk' codec can't decode byte ...`——`_readerthread` 崩溃 → `r.stdout` 变 `None` → 后续 `.strip()` / 拼接抛 `AttributeError`，测试直接 FAIL。这与项目已有的 [`lib/_utf8.py`](plugins/kdev-memory/hooks/lib/_utf8.py)（输出侧 reconfigure stdout）是同一编码意识在**输入侧**的缺口。

**修复**：统一给所有 `text=True` 的 `subprocess.run` 加 `encoding="utf-8", errors="replace"`——UTF-8 是 hook / git 输出的实际编码，`errors="replace"` 兜底防崩溃。保持现有 `r.stdout + r.stderr` 字符串拼接逻辑不变，最小侵入。

**范围**（全量审计 `tests/` + `hooks/lib/` 下所有 `text=True` 调用）：

- 测试侧 8 处：`test_stop_check_pending.py` / `test_stop_check.py` / `test_brief_verbosity.py` / `test_session_start_brief_prefix.py` / `test_commit_tracker.py`（2 处）/ `test_step_id.py` / `test_kdev_sync.py` 的 `_run_hook` / `_run` / `_git` helper。
- 库代码侧 2 处：[`lib/step_id.py:_git_query`](plugins/kdev-memory/hooks/lib/step_id.py)（被 `compute_branch_slug` 调用读分支名）、[`lib/kdev_sync.py:_git`](plugins/kdev-memory/hooks/lib/kdev_sync.py)（被 `bootstrap` 调用跑 push/pull）。

**效果**：`test_stop_hook_silent_when_no_pending` / `test_stop_hook_warns_when_pending_age_exceeded` / `test_slug_sanitize_unicode`（中文分支名 "实验/中文分支"）/ `test_sync_push_then_pull_propagates` 等 6 个用例从 FAIL → PASS。

**未修的剩余隐患**（无测试触发，记录待后续）：`lib/worktree_link.py`（2 处 `_git` / mklink）、`lib/skill_version.py`（`detect_drift` 的 git log）、`lib/migrate-v0.7.py`（3 处）的 `text=True` 仍无 `encoding`。当前无测试覆盖且输出多为纯 ASCII（sha / 路径），暂不强制修；后续若这些路径输出中文/emoji 会触发同类崩溃。

**⚠️ 与编码无关的预存并发 bug（未修，超出本任务范围）**：`test_step_id.py::test_dup_index_concurrent_no_collision` / `test_increment_concurrent_no_collision` 在本机稳定/间歇失败——20 线程并发调 `_dup_index` / `increment_counter` 只拿到 11 个结果（少 9 个），是文件锁并发竞争问题，与本次编码修复正交。建议另开任务诊断 `_dup_index` / `increment_counter` 的并发安全。

### 📌 下游同步提醒

本 bug 在下游 fork **ieidev-team 的 `hooks/commit-tracker.py`** 同样存在（同一处漏门控 + 同一 `pending_commits.append` 调用链）。请下游同步补上同一道存在性门控，否则未初始化工程跑 `git commit` 仍会自举 `.kdev/memory/`。

## [0.18.1] — 2026-06-14

**召回扫描器双认补全：时间戳形 G 条目不再静默漏召 + 记录 ID 文法单一真相源。**

### 🐛 修复

- **`trigger-match.scan_g_entries` 漏召时间戳形 G（核心修复）**：heading 正则原为 `^##\s+(G-\d+)…`，只认旧顺序号 `G-NNN`，v0.17（Q-020）起新铸造的时间戳形 `## G <YYYYMMDD-HHMMSS>-<who>` 被**静默 MISS**。踩坑召回是「防重踩」核心通道，漏召 = 用户再撞同类坑时 recall 不提示。现改为双认（旧顺序号 + 时间戳）。当前 .kdev 里 G 全为旧形，属**潜伏 bug**，下一条时间戳 G 铸造即触发。

### 🔄 变更（治根因：消除三处正则漂移）

- **`step_id.id_label_fragment(type)`（新增，单一真相源）** + **`TS_ID_CORE`** 常量 —— 记录 ID 文法（legacy↔时间戳双认）集中托管。`trigger-match` / `distill` / `step_completeness` 三处 heading 正则统一从此构建，杜绝各自维护副本漂移（本次 bug 的根因）。`parse_record_id` 的 `_RE_NEW` 也改从 `TS_ID_CORE` 构建（行为不变）。
- **`trigger-match.scan_step_entries`** —— Step 正则去掉脆弱的 `[\w.-]+` 通配（原靠它"碰巧"兼容时间戳形），改为显式双认 fragment（枚举 `\d+` / `\d+.\d+` / `前缀-N` + 时间戳；覆盖全部历史 Step 形，无回归）。
- **`distill.HEAD_PATTERNS` / `step_completeness.parse_steps`** —— 各自的 `_TS` / `[\w\-\.]+` 局部正则改用 `id_label_fragment`，行为等价。

## [0.18.0] — 2026-06-14

**Schema / 数据完整性整顿：CLAUDE.md 托管块 marker 化 + status 语义去漂移。**

### ✨ 新增

- **`hooks/lib/claude_md_merge.py`** — CLAUDE.md 托管段 marker 化合并：`merge_managed_section()` 幂等 insert-or-replace 三场景（有配对 marker→替换块内正文 / 无 marker 有裸段→retrofit 包住正文不动 / 都没有→末尾追加）；孤儿/逆序 marker 先归一化再合并，杜绝嵌套重复。marker（spec-kit 风格、稳定可正则、含 plugin 标识）：`<!-- BEGIN/END kdev-memory:智能体自动记录规则 ... -->`。
- **`hooks/lib/status_schema.py`** — status 枚举谓词（`is_known_status` / `is_voided_status`）+ 非枚举告警（`warn_unknown_status`）。status = 评分/销账态 only（open|scored|voided-faded|voided-r-NNN）。

### 🔄 变更

- **`claude_md_lint.extract_kdev_section`** — 优先按 BEGIN/END marker 切块；无 marker / 半残 marker 回退按 `## 智能体自动记录规则` 标题切块（老项目兼容、不报错）。
- **`step_completeness` / `distill`** — 用 `status_schema.is_voided_status` 替换硬编码 voided 判定；遇非枚举 status（如修复态 `fixed` 误写）告警一行，不静默当未评分。
- **schema / SKILL / 初始化模板** — 钉死「status=评分/销账态，≠修复态；修复进展写 body「解决」段，不新增 fix_status」（Q `20260614-005123` 决策）；初始化模板段包 marker + 合并策略改 insert-or-replace 三场景；本仓 CLAUDE.md retrofit 包 marker（正文语义不动）。

### 🐛 修复

- **status drift**：清 G-005（fixed）/ G-006（mitigated）/ G-011（处置中）三条踩坑的 status 漂移——status 改回 `scored`，原修复信息移进各自 body「解决/处置进展」段（语义零丢失）。
- **`step_completeness` voided-r-NNN 字面 bug**：原 `VOIDED_STATUSES={"voided-faded","voided-r-nnn"}` 字面集不匹配真实 `voided-r-003`；改用 `is_voided_status` 正则谓词（`voided-r-<digits>`）。

## [0.17.0] — 2026-06-13

**P-C2 Phase A：记录 ID 时间戳化（Q-019 / Q-020）。**

### ✨ 新增

- **`step_id.mint_record_id(type, state_dir)`** — 统一记录 ID 铸造接口：格式 `<Type> <YYYYMMDD-HHMMSS>-<who>[.<n>]`（who = git email 本地部分；无 git 省略后缀，不写 `-None`；同秒同写手 `.N` atomic 去重）。Step / Q / G / R / F 全部走此接口。
- **`step_id.parse_record_id(id_str)`** — 解析双认：同时识别新时间戳格式（`<Type> <ts>-<who>`）与旧顺序格式（`Step <slug>-N` / `Q-NNN` 等），向后兼容现存日志。

### 🔄 变更

- **kdev-step-recorder** — `mint_record_id` 替换 `mint_next_step_id` 作为 Step ID 铸造主路径；per-slug counter drift guard 退役（时间戳无 counter，不需要 drift 检测）。
- **session-start-brief / distill / brief** — `parse_record_id` 双认旧/新形式；brief 不再显示「本次 Step ID 前缀」（时间戳无前缀概念）。
- **`scope.resolve_step_slug`** — 标记为 deprecated for minting（Q-020）；仅留向后兼容/历史解析。slug/counter 机制退出 minting 主路径。

### 🐛 修复

- **G-011**：worktree 并发撞号——时间戳 + who 组合 coordination-free，多 worktree/多机同时落盘不再产生重复 ID。

### 🧱 向后兼容 / 约束

- 现存顺序 ID（`Step main-N` / `Q-NNN` 等）**冻结**：不再 mint，但 `parse_record_id` 持续识别（双认）。
- `mint_next_step_id` 保留在代码库但退出主路径；现有测试锁定其行为不变（backward-compat 层）。
- ⚠️ G-004：bump `0.16.0 → 0.17.0`，用户须刷 marketplace + 重启 session 才生效。

## [0.16.0] — 2026-06-13

**P-C1b：Step 落盘 transcript 溯源 + 模型他评。**

### ✨ 新增

- **commit-tracker stash transcript_path** 进 pending state；step-recorder 用 Bash `sed`/`jq` + `transcript_extract.py` 读真 transcript 抽结构化事实（`tools_invoked` / `errors_hit` / `files_touched` / `commit_shas` / `skills_invoked` / `subagents_dispatched`），并据此 + skills_invoked 做 recorder 侧 `subject` 推断，不再要主会话喂 ~30 行 YAML（用 Bash 切片，非 Read 工具——Read 有 25k 整文件 token 闸）。
- 评估从 `### 模型自评` 改 `### 模型他评`（独立 recorder 读真 transcript，记录层修 MQ-2 confabulate），半残检测兼容两名。

### 🔄 变更

- **nudge 阈值改 age 为主**（TDD 爆量不刷屏）。

### 🐛 修复

- **G-010**：commit-tracker 读 `tool_input`（snake，官方契约）而非 `toolInput` → 复活死掉的 pending nudge。

### 🧱 向后兼容 / 约束

- `pending_commits.read()` 对缺 `since_offset` / `transcript_path` 的旧版 state 文件 `setdefault` 补默认值（round-trip 测试显式锁定该生产安全行为）。
- ⚠️ G-004：bump `0.15.1 → 0.16.0`，用户须刷 marketplace + 重启 session 才生效。

## [0.15.1] — 2026-06-12

**MQ-1：kdev-step-recorder 收尾返回 6 行机器块 → 一句人话确认。**

### 🔄 变更

- `agents/kdev-step-recorder.md` Return format：成功分支从 `STATUS/MINTED_ID/COUNTER/SCOPE/RATING_MODE/TARGET` 6 行审计块，改为一句人话确认（如"已落 Step main-70 → 执行日志.md；当前状态已同步、pending 已清"）。fire-and-forget subagent 的 final text 即返回值、会回显主会话——机器块被反馈"突兀"（§1.5.7 MQ-1）。拒绝分支保留结构化（主会话需照此修正重派）。
- 直接配合 §1.5.6 B 轨：B 轨复用 fire-and-forget 批量派单，recorder 机器块回灌会抵消 B 轨"压刷屏"收益。
- 测试：新增 `test_recorder_return_oneline.py`（成功无机器块 + 一句人话 + 拒绝仍结构化）。

### 🧱 约束

- 不碰 lib 契约（mint/写盘/clear pending 不变，e2e 测试不受影响）；不碰 scope/评分模式逻辑。
- ⚠️ G-004：bump `0.15.0 → 0.15.1`，用户须刷 marketplace + 重启 session 才生效。

## [0.15.0] — 2026-06-11

**kdev-memory 减痛轨 P-C0.5 + P-C1a：评分模式可配 + brief 分级 + subagent 输出精简。**

### ✨ 新增

- **`rating.mode`（config.yaml，flat dot-key）** — 评分三档：`model-only`（零追问，= Q-002 机读化）/ `user-opt-in`（插件默认，轻提一句不阻塞）/ `user-required`（现行硬闸门）。`memory_config.read_rating_mode` / `rating_mode_configured`。
- **`brief.verbosity`（config.yaml）** — SessionStart brief 三档：`compact`（只注入 WARN + pending_decisions + 今日进度一行，其余写 `.kdev/memory/brief-detail.md`）/ `normal`（现行）/ `verbose`（全量不截断）。`memory_config.read_brief_verbosity`。
- **首次评分提示** — config 无 `rating.mode` 键时 brief 注入一次性 `<kdev-memory-rating-setup>`（`state/.rating-setup-shown` marker 去重）。
- **`hooks/lib/migrate_void_faded.py`** — Q-002 后"仅因用户评分空"的半残 Step 批量盖 `status: voided-faded` + 销账注释（幂等，dry-run 默认 / `--apply` 落盘；按 body 切片重建，对重复标题鲁棒）。

### 🔄 变更

- **`step_completeness`** — `check_step`/`run_check` 加 `rating_mode` 形参（默认 `user-required` 保现状）：`model-only`/`user-opt-in` 下"用户评分段空"不算半残；扣分项缺失**所有模式仍查**（防讨好式满分）。`parse_steps` 补 header 内联 `status:` 解析（修历史 latent bug——Step 1/2/3 的内联 voided-faded 此前从未生效）。
- **`stop-check`** — 按 `rating.mode` 降级：`model-only` 跳过半残检测、`user-opt-in` 软提醒不阻塞、`user-required` 现行（soft + strict 阻塞）。
- **`session-start-brief`** — verbosity 分级 + 首次评分提示 + 给半残扫描传 `rating_mode`。
- **`agents/kdev-step-recorder.md`** — 读 `rating.mode` 决定用户评分段写法（model-only 留空 + 内联 `status: voided-faded` + 销账注释，**绝不伪填自评分**）；Return format 砍 `APPENDED_BLOCK`，只回 6 行审计字段。
- **`SKILL.md` / `六类记录-schema.md`** — 评分动作链按 `rating.mode` 三分支重写；schema 注明 model-only 留空 + voided-faded 标准做法。

### 🧱 向后兼容 / 约束

- **默认温和**：`rating.mode` 默认 `user-opt-in`、`brief.verbosity` 默认 `normal`；`user-required` = 现行行为完整保留。
- **不伪造用户评分**：model-only 用户评分段留空 + voided-faded，绝不拷自评分（污染 misalignment 切片）。
- **不预留** `peer_review`（他评 defer）；**不碰** P-C1b transcript 溯源（commit-tracker offset / step-recorder input 重写均未做）。
- **测试**：新增 `test_rating_mode_config` / `test_brief_verbosity` / `test_stop_check` / `test_migrate_void_faded`，更新 `test_step_completeness`；全量 323 绿。
- **G-004 提醒**：本版 bump `0.14.0 → 0.15.0`，用户侧需刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

## [0.14.0] — 2026-06-10

**P-C1 记忆 scope 分离（数字员工集群 阶段2）：kdev-memory scope-aware，opt-in 向后兼容。**

### ✨ 新增

- **`hooks/lib/scope.py`** — scope 解析单一真相源：`is_scoped`（`shared/` 存在即 scoped）/ `shared_dir`（flat 下 == root，字节级不变量）/ `staff_root` / `staff_dir` / `list_staff` / `staff_log_files` / `state_dir`（永远 root）/ `resolve_step_slug`（shared→分支 slug，员工→canonical id）/ `recorder_target_log`。
- **`hooks/lib/migrate_scope.py`** — flat → scoped 一次性幂等迁移 CLI（手动调用，不自动跑、不在框架仓跑）：markdown 进 `shared/`，建 `staff/<canonical-id>/`，plumbing 留 root，复用 kdev_sync 写 `.kdev/.gitignore`，部分失败显式追踪+告警。

### 🔄 变更

- **scope-aware 改造**（opt-in，flat 行为字节级不变）：`trigger-match`（召回 shared + staff Step，标 scope；铁规走 shared）/ `session-start-brief`（shared 解析 + 👥 员工 scope 进度 block）/ `weekly`（rollup 聚合 staff Step + per-scope 盘点）/ `distill`+`distill_trigger`（dataset 收 staff Step；执行日志/skill-feedback/改进建议 走 shared）/ `frontmatter` `missing_summaries` `archive_hint` `promote_scan` `milestone` `stop-check` `pre-compact-check` `session-end-check`（markdown 走 `shared_dir`，markers/state 留 root）。
- **`step_id.py`** 导出 public `sanitize_slug`；per-scope Step counter 复用现有 slug 机制（`Step <scope-slug>-N`）。
- **`agents/kdev-step-recorder.md`** — dispatch YAML 加 `scope` 字段（缺省 shared）；员工 scope 落 `staff/<id>/执行日志.md` 用 canonical id slug，跳过 shared frontmatter 更新 + drift guard（hard-gate #8 仅对 shared）。
- **`skills/kdev-memory/SKILL.md`** — scoped 布局文档 + Step ID scope 泛化（`Step <scope-slug>-N`）+ dispatch scope 字段 + P-C1b transcript 扩展注记。

### 🧱 向后兼容 / 约束

- **opt-in**：无 `shared/`（无 staff 注册）= flat 默认 = 现状，路径+行为完全不变；现有用户零影响。core 不变量 `shared_dir(root)==root`（flat）保证字节级一致。
- **框架仓 `.kdev` 保持 flat**（主控单轨），`migrate_scope.py` 不自动跑、不在框架仓跑。
- **right-size**：只建 shared + 2 员工（dev-engineer / req-architect）最小机制；P-C2 JSONL 操作层 / P-C3 并发写锁 defer。
- **测试**：新增 scope/frontmatter/trigger/brief/weekly/distill/tier-a/migrate/recorder/集成 共 10 个测试文件；全量 291 passed。
- **G-004 提醒**：本版 bump `0.13.0 → 0.14.0`，用户侧需刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。

## [0.13.0] — 2026-06-06

**P4 git 托管自举（Q-009）：`.kdev/` 独立 nested 记忆仓 + SessionStart 自举 + SessionEnd 推送。**

### ✨ 新增

- **`hooks/lib/kdev_sync.py`** — git 托管自举核心：`decide_action`（pull/clone/init/remind 纯决策）+ `bootstrap`（无 `.kdev/.git` 且本机已有记忆 → init+首推）+ `sync_push`（SessionEnd commit+push）。stdlib-only。
- **`hooks/kdev-sync-bootstrap.py`** — SessionStart hook：无 `.kdev/.git` 有本机记忆 → init+首推；有 → pull；无 remote → 中文托管提醒。best-effort 不阻塞 session。
- **`hooks/kdev-sync-push.py`** — SessionEnd hook：commit+push `.kdev/`（machine-local 的 `state/ checkpoints/ hud.md dataset/` 经 `.kdev/.gitignore` 排除）。
- **`kdev-sync.yml`（仓根 tracked）** — 记忆仓 remote 登记，随 clone 到任何机器。

### 🔄 变更

- **hooks.json** SessionStart 加 `kdev-sync-bootstrap`（在 brief 前）；SessionEnd 加 `kdev-sync-push`。

### ⚠️ 重要（为何本版必须 bump version）

- `plugin.json` version 自 **0.10.1**（2026-05-27 cache）起**未随源码 bump**——Claude Code 插件 cache **按 version 键控**，导致 0.11/0.12（R-001 step-recorder hooks）+ P4（本版 git 托管 hooks）**全部静默未生效**（cache 一直跑 stale 0.10.1）。本次 `0.10.1 → 0.13.0` 触发 cache 重抽取，激活累积的 hook 层。**用户侧需刷新 marketplace（`/plugin` 更新/重装）+ 重启 session** 才生效。详见踩坑日志 G-004。

## [0.12.0] — 2026-06-02

**R-001 集成：kdev-step-recorder dispatch 接入 SKILL.md / CLAUDE.md 主路径 + commit hook 兜底 + R-005 顺手。**

按 R-001 v1 spec（[docs/skills/kdev-memory/specs/2026-05-29-r-001-step-recorder-integration.md](../../docs/skills/kdev-memory/specs/2026-05-29-r-001-step-recorder-integration.md)）+ 14 task plan 实施。

### ✨ 新增

- **`hooks/lib/pending_commits.py`** — pending-commits.json CRUD + threshold helpers (count 默认 ≥3 / age 默认 ≥30min)
- **`hooks/lib/skill_version.py`** — SKILL.md SHA cache + drift detection (R-005)
- **`hooks/commit-tracker.py`** — PostToolUse Bash hook 检测 git commit + 累积 pending。**suppress 规则**：commit message 含 `\(.*?task N/M.*?\)` 圆括号模式时视为 subagent-driven batch 不计入
- **agents/kdev-step-recorder.md** YAML schema v0.3 加 `commits_batch_id` 字段（optional，不参与 hard-gate），action step 5 切到 `pending_commits.clear()` lib
- **`SKILL.md §"用 kdev-step-recorder dispatch 落 step (v0.12+)"`** 新章节 ~50 行——主会话见此就知道用 dispatch
- **`SKILL.md § 下游 拆分`** — R-NNN→升铁规 移到 § 规则升级流程 下作子§「原料来源」；§ 下游 改名"知识蒸馏"只讲蒸馏切片

### 🔄 变更

- **CLAUDE.md 第 1 条铁规重写**："实时落盘" → "实时 dispatch step-recorder 落盘"。模板同步。
- **stop-check.py** 加 pending-commits 阈值软提醒 (rule 8)
- **session-start-brief.py** 加 (a) pending-commits 状态展示 (b) SKILL.md SHA drift ⚠️ 提醒；`_read_source()` 返回 tuple (source, session_id)
- **hooks.json** 注册新 PostToolUse Bash matcher 指向 commit-tracker.py

### 🔧 兼容

- 老历史 Step / 现有半残 Step 不迁移；新机制上线后逐步消化
- `.kdev/memory/state/pending-commits.json` + `skill-version-cache-*.json` 是 session-local 状态，跟 step-counter-*.txt 共生（继承 `.kdev/` 现状 sync 策略）
- agents/kdev-step-recorder.md v0.2 的 8 hard-gate 全保留；YAML schema 是向后兼容追加

### 📋 升级

升级到 v0.12.0：
1. 拉取代码（plugin update）
2. **重启所有运行中的 Claude Code 会话**（否则旧 session 不感知新 SKILL.md / hook；新机制 R-005 SHA drift 会在重启后 brief 提醒看到）
3. CLAUDE.md 项目根的"实时落盘"段会被自动对齐到新模板

### ✅ 测试

- `tests/test_pending_commits.py`：11 用例
- `tests/test_skill_version.py`：8 用例
- `tests/test_commit_tracker.py`：10 用例（含 task N/M suppress 矩阵 + gitlab prefix + -C flag）
- `tests/test_session_start_brief_prefix.py`：+2 用例（pending hint + SHA drift）
- `tests/test_stop_check_pending.py`：2 用例
- `tests/test_step_recorder_e2e.py`：1 e2e
- 完整测试套：236 通过 + 1 known pre-existing 失败（[R-002](.kdev/memory/改进建议.md)）

---

## [0.11.0] — 2026-05-28

**Step ID 加分支前缀：解决 secondary worktree symlink 共享 `.kdev/` 架构下并发 ID 冲突。**

经 Q-003 决策（[.kdev/memory/决策日志.md](../../.kdev/memory/决策日志.md)）+ 13 任务 plan 实施。新增 `hooks/lib/step_id.py`（slug + counter + mint 一站式接口），SessionStart brief 展示当前分支前缀，SKILL.md / references 全面对齐。

### ✨ 新增功能

- **`hooks/lib/step_id.py`** — slug + counter + mint 一站式接口：
  - `compute_branch_slug()`：git rev-parse → 干净的 ASCII slug（`feature/X` / `feat/X` 去前缀；非法字符 sanitize；detached HEAD → `detached`；非 git → `unknown`）
  - `read_counter(slug, state_dir)` / `increment_counter(slug, state_dir)`：每分支独立计数器，flock 保护 atomic 递增（POSIX `fcntl` / Windows `msvcrt`），committed 20 线程并发测试零冲突（reviewer 临时扩到 100 线程也零冲突，未入测试套）
  - `mint_next_step_id(state_dir, slug=None)` → `"Step <slug>-<N>"`
- **`SessionStart brief`** 在「今日进度」段加 `- 本次 Step ID 前缀：\`<slug>-\``，让智能体新会话立刻知道用什么前缀
- **`step_completeness` regex 兼容性回归测试**：显式覆盖 `Step main-9` / `Step cluster-x1-1` / 历史无前缀混合解析

### 🔄 变更

- **Step ID 格式**：从 `Step N` 全局递增 → `Step <branch-slug>-N` 每分支独立递增
- **`当前状态.md` frontmatter `current_step` 字段类型**：int → string（如 `main-9`）。`frontmatter.py:read_state_field` 已返回 str，reader 层无 breaking change
- **SKILL.md / 六类记录-schema.md / triggers-写法.md / 切档与归档.md / subject-推断与评分裂解.md / README.md / 初始化-claude-md-模板.md** 全面更新示例 + 新增「多 worktree 并发场景」一节

### 🔧 兼容性

- **历史 Step 1~9 不迁移**：保持无前缀格式不动以保护既有锚点链接；`执行日志.md` 头部加 `<!-- step_id_prefix_since: 2026-05-28 -->` 注释标识切换点
- **main 分支计数器初始化为历史最大 Step 编号**（本仓库为 9），下一条 = `Step main-10`，保持时间线连贯
- **新建分支** 计数器从 0 起，下一条 = `Step <slug>-1`

### 📋 升级指南

升级到 v0.11.0 的项目需要执行一次性初始化：
1. 在 `执行日志.md` header 段加 `<!-- step_id_prefix_since: YYYY-MM-DD -->`
2. 计算历史最大 Step 编号 N，创建 `.kdev/memory/state/step-counter-<main-slug>.txt` 内容为 `N`（`echo N > .kdev/memory/state/step-counter-main.txt`）
3. CLAUDE.md 添加 v0.11 新格式提醒（见模板 [`初始化-claude-md-模板.md`](skills/kdev-memory/references/初始化-claude-md-模板.md)）

### ✅ 测试

- `tests/test_step_id.py`：19 用例（8 slug + 7 counter + 4 mint）
- `tests/test_session_start_brief_prefix.py`：2 用例
- `tests/test_step_completeness.py`：+3 prefix 兼容回归
- 完整测试套：200 通过 + 1 pre-existing 失败（`test_distill_trigger.py::test_old_distill_with_new_f_triggers`，与本变更无关）

---

## [0.10.1] — 2026-05-27

**Patch：修 Linux/macOS 上 hook 全线 "Permission denied" 报错。**

### 🐛 修复

- `hooks/run-python-hook.cmd` 加 +x 位（git mode 100644 → 100755）。该文件是 7 个 hook 事件（SessionStart / UserPromptSubmit / Stop / PostToolUse / PreCompact / SessionEnd）的共用入口，`hooks.json` 直接把它当可执行文件调用；之前唯独这个文件没有执行位，Linux/macOS 上每次 hook 触发都报 `/bin/sh: ... .cmd: Permission denied`（non-blocking 不阻断，但日志噪声大）。Windows 不受影响。
- **已装 0.10.0 的用户升级到 0.10.1 后自动修复**。如果暂不升级，本地 `chmod +x ~/.claude/plugins/cache/kdev-agents/kdev-memory/0.10.0/hooks/run-python-hook.cmd` 也可绕过。

## [0.10.0] — 2026-05-16

**蒸馏管道 + 自动蒸馏机制：subject 路由全栈打通——F-NNN 反馈通道 + /kdev-memory-distill 统一蒸馏入口 + SessionStart hook 自动触发。**

经 5+ 轮设计讨论确认 5 条核心决策（详见 .claude/memory/kdev-memory-distillation-design.md）。
3 个 commit 累计：c153aca（蒸馏管道改造）+ 98253f4（promote+export-md 合并）+ 796555c（自动蒸馏机制）。
单测 145/145 PASS（新增 18 distill_trigger 测试）+ skill-quality eval 19/19 PASS（iter-2 + iter-3 三轮跑通）。

### ✨ 新增功能

#### F-NNN 反馈通道（七类记录扩展）

- **新增 `skill-feedback.md`**（F-NNN）—— 与 R-NNN 物理隔离的"对外部 skill / plugin / 工具 / 方法论反馈"通道
- 三铁规：`subject` 必填、`verbatim`（用户原话）必填不可改写、`score` 显式可空
- 智能体在主对话流自动识别 5 类语义（RFE / 痛点 / bug / 表扬 / 困惑），起草后**落盘前一句话向用户确认**避免误采
- 新增 `references/skill-反馈通道-F.md`：完整 schema + 识别规则 + 边界（哪些不属于 F-NNN）

#### subject 三级自动推断（数据路由器）

- 每条评分/反馈必须显式标记 subject：`project` / `skill:X` / `plugin:X` / `tool:X` / `methodology:X` / `collaboration:X` / `unknown`
- **三级推断策略**：L1 显式提及（~40%）+ L2 上下文推断（~50%）+ L3 候选 disambiguate（~10%），共 90% 场景不打扰用户
- **评分裂解**：用户评分时夹带 skill 反馈（如"4 分但 X 太吵"）自动拆两条独立条目，绝不塞同一条
- 推不出时归 `unknown`，绝不默认归 `project`（避免污染项目评分子集）
- 新增 `references/subject-推断与评分裂解.md`

#### /kdev-memory-distill 统一蒸馏入口

合并旧 `/kdev-memory-promote`（人沉淀）+ `/kdev-memory-export-md`（机器训练）为一个命令——按 subject 字段路由数据：

```
.kdev/memory/ 全量原始记录
       ↓ 按 subject 路由
       ├── subject = project             ──→ promote 阶段（人工挑选）
       │                                    ──→ docs/ 反哺项目
       └── subject = skill/plugin/        ──→ dataset 阶段（自动打包）
           tool/methodology/                 ──→ 三个 markdown 切片包：
           collaboration                       - dataset-full.md
                                               - dataset-misalignment.md
                                               - dataset-skill-feedback-by-subject/<slug>.md
```

- **不引入 JSONL**——markdown 主存 + markdown 切片包导出，现代蒸馏管道（Axolotl / Unsloth / HuggingFace SFT）原生支持 markdown，多一层中间格式徒增维护并丢失因果链 reasoning trace
- 新增 `hooks/lib/distill.py`（端到端切片导出 + sanitize + 验证）
- 新增 `hooks/lib/sanitize.py`（PII 脱敏：email / home 路径 / API key / Bearer / 私网 IP / 内部 URL）
- 新增 `references/markdown-切片导出.md`

#### 自动蒸馏机制（auto / manual 两档）

- **默认 auto**：SessionStart hook 检测阈值满足时后台 `subprocess.Popen distill.py --auto-context --skip-promote`（detach 子进程，hook 立刻返回）；brief 注入"🤖 已开始后台自动蒸馏"
- **manual 模式**：仅 brief 注入"📋 建议蒸馏：[原因]，跑 /kdev-memory-distill"，不自动跑
- **触发条件（AND 语义）**：距上次蒸馏 ≥ 7 天 AND（F 新增 ≥10 OR misalign Step 新增 ≥3 OR R 新增 ≥5）
- **promote 阶段永远不自动**（写 docs/ 是版本控制相关高风险动作，必须人工挑选）
- **失败显式 WARN**：写 `WARN-distill-failed-*.md`，下次 SessionStart 显眼提醒（不静默）
- **配置**：`.kdev/memory/config.yaml` 的 `distill.mode` / `reminder_days` / `reminder_new_f` / `reminder_new_misalign`
- 新增 `hooks/lib/distill_trigger.py`（阈值检测）+ `references/蒸馏触发机制.md`

#### subagent 落盘两档配置

- **`record_mode: hybrid`（默认）** —— 小高频（Step / Q / G / R / F 落盘 / subject 推断）留主会话内联；大单次（每日汇总 / weekly / distill）+ F-NNN 实体写入走 subagent
- **`record_mode: inline`** —— 全部主会话内联（平台不支持 subagent 或用户偏好极简）
- F-NNN 实体写入是 **fire-and-forget 异步落盘最大杠杆点**——让用户随口吐槽不打断对话
- 新增 `references/subagent-落盘机制.md` + `hooks/lib/memory_config.py`（嵌套 yaml parser + 配置读取）

### 🔧 schema 扩展

- 执行日志 Step §3：顶部加 `about` 字段（缺省 = project），评分裂解段（用户评分夹带 skill 反馈时如何拆条目）
- 七类记录总览表 + 速览：F-NNN 作为第六类列入，原 6 / 7 类编号顺延为 7 / 8

### 📊 验证

- **单测**：145/145 PASS（既有 127 + 新增 18 个 distill_trigger / config / sanitize / 端到端测试）
- **skill-quality eval**：
  - iter-2 47/47 = 100%（5 个新 case 覆盖 F-NNN/评分裂解/L3 disambiguate/误采防护/切片导出）
  - iter-3 19/19 = 100%（3 个新 case 覆盖自动蒸馏 auto/manual/无触发，**实跑脚本验证** trigger-check.json + brief-output.txt 硬证据）

### 🔗 升级指引

兼容老项目：
- 老项目无 `.last-distill` 时 fallback 到 `.last-promote` mtime——平滑过渡
- `/kdev-memory-promote` 和 `/kdev-memory-export-md` 旧命令已删除，全部走新 `/kdev-memory-distill`（含历史迁移说明段供新用户理解 v0.9 → v0.10 演进）
- `record_mode` / `distill.mode` 未配置 → 默认 hybrid + auto（fail-open 偏 UX 友好），无需配置即可享受新能力

跑 `/plugin update kdev-memory@kdev-agents` 即可。

### 📝 相关文档

- `.claude/memory/kdev-memory-distillation-design.md`（4 条核心决策完整论证）
- `plugins/kdev-memory/skills/kdev-memory/references/skill-反馈通道-F.md`
- `plugins/kdev-memory/skills/kdev-memory/references/subject-推断与评分裂解.md`
- `plugins/kdev-memory/skills/kdev-memory/references/markdown-切片导出.md`
- `plugins/kdev-memory/skills/kdev-memory/references/subagent-落盘机制.md`
- `plugins/kdev-memory/skills/kdev-memory/references/蒸馏触发机制.md`

---

## [0.9.0] — 2026-05-03

**SKILL.md 极简重构：从 1326 词精简至 944 词（-28.8%），符合 skill-creator <5k 词规范。**

iter-12 discriminating eval 验证：精简不逆转 iter-7 收益，行为 100% 一致。

### ✨ 架构优化

- **SKILL.md 主文精简**：从 1326 词 → 944 词（-28.8%）
  - 移除低频场景细节（初始化模板、切档流程、升级流程等）→ 已承接至 references/
  - 移除冗余描述（如"为什么这样设计"解释段）→ 精简为"参考 xxx reference"
  - 移除 hook 实现细节列表 → 改为"见 references/自动化机制-hooks.md"
  - 移除反模式枚举 → 精简为核心铁规
- **references/ 承接完整**：移出的内容全部有对应 reference 文件承接，无信息丢失
- **符合 skill-creator 规范**：944 词 < 5k 词限制，降低每次触发 token 成本

### 📊 iter-12 discriminating eval 结果

| 指标 | Baseline (v0.8.x) | With Simplification | 差异 |
|------|-------------------|--------------------|------|
| SKILL.md 词数 | 1326 | 944 | -28.8% |
| 总 tokens | 134,194 | 134,540 | +0.26% |
| 总 tool_uses | 47 | 44 | -6.4% |
| Pass rate | 100% (13/13) | 100% (13/13) | 一致 |

**结论**：行为完全一致，tool_uses 略降，精简不逆转 iter-7 的显式化收益。

### 🔗 相关文档

- `plugins/kdev-memory/evals/skill-quality/iterations/20260429-01-skill-simplification/`：完整 eval 数据
- `docs/skills/kdev-memory/dev-notes/2026-04-29-kdev-memory-subagent记录模式方案-修订版.md`：方案 D+E 决策背景

### ⚠️ 升级指引

无任何用户行为变化，行为完全等价于 v0.8.2。
跑 `/plugin update kdev-memory@kdev-agents` 即可。

---

## [0.8.2] — 2026-04-27

**Windows python3 命令兼容性修复：polyglot wrapper 自动选择正确的 Python 解释器。**

### 🐛 兼容性修复
- 新增 `hooks/run-python-hook.cmd`：polyglot wrapper（单文件同时支持 Windows cmd + Unix bash）
  - Windows 优先级：`py -3` → `python` → `python3`
  - Unix/Mac 优先级：`python3` → `python`
  - `py -3` 使用 Windows Python launcher，明确指定 Python 3，避免 Python 2 混淆
- `hooks/hooks.json`：6 处 `python3 "..."` 全改为 `run-python-hook.cmd <script>.py`
- 解决 Windows 上 `python3` 指向 Windows Store stub（返回 exit code 49）的问题
- 解决旧系统 `python` 可能指向 Python 2 的问题

### 📚 相关文档
- `docs/skills/kdev-memory/dev-notes/2026-04-27-windows-python3-hook兼容性问题.md`：问题分析与解决方案对比

## [0.8.1] — 2026-04-25

**收口：把 v0.8.0 的 emoji 编码兼容修复扩展到所有相关 hook（dac5cfe 漏修了）。**

### 🐛 修复

- 新增 `hooks/lib/_utf8.py` —— `force_utf8_stdio()` helper，把 sys.stdout/stderr
  切到 UTF-8（如果当前不是），失败静默不阻断 hook
- `session-start-brief.py` / `stop-check.py` / `pre-compact-check.py`
  顶部加 `force_utf8_stdio()` 调用，覆盖原 dac5cfe 漏掉的入口：
  - session-start-brief 通过 `print(json.dumps(..., ensure_ascii=False))` 注入
    含 🔴🟡⚪📊🎯📝💡 的 brief —— 之前在 Windows GBK 下含 emoji 时会抛
    UnicodeEncodeError
  - stop-check 的 `sys.stdout.write` reminders 含 ⚠️ 📦 —— 同样风险
  - pre-compact 当前 stdout 暂无 emoji，但保险起见统一加（防未来 reminders 加 emoji 时回归）
- `weekly.py` 改用共享 helper（替代 dac5cfe 的 inline reconfigure）

### 🐛 触发场景

v0.8.0 在 Windows 上之所以验证通过，是因为测试场景是干净临时项目
（无 pending 沉淀候选、无跨期归档、无 P0 阻塞），session-start-brief 走的是
"📊 今日进度"分支，**未触发 emoji-密集的 P0/P1/P2 块**。一旦真实项目积累内容
触发到沉淀提醒（含 🔴 / 📝）、归档提醒（含 📦）等，Windows GBK console 会
炸 UnicodeEncodeError 导致 hook JSON 注入失败。本版本预防性收口。

### 📚 文档微修

- `hooks/lib/claude_md_lint.py` 注释里残留的 "session-start-brief.sh" 引用
  补成 "session-start-brief.py（v0.7 之前是 .sh）"

### ⚠️ 升级指引

无任何用户行为变化，行为完全等价于 v0.8.0；只是更稳。
跑 `/plugin update kdev-memory@kdev-agents` 即可。

## [0.8.0] — 2026-04-25

**纯 Python 化：bash 入口与 helper libs 全部转 Python，去除 bash 依赖。**

### 🔄 实现层重构（无用户感知行为变化）
- 14 个 .sh 文件（6 个 hook 入口 + 8 个 source'd helper libs）全部转为 Python
- `hooks/hooks.json`：6 处 `bash "..."` 全改为 `python3 "..."`
- 跨平台分叉全部消除：`stat -c` vs `stat -f` / `date -d` vs `date -v` / `ln -s` vs `mklink /J` / `find -newer` —— 现在用 `os.stat().st_mtime` / `datetime` / `os.symlink` / `Path.rglob` 一份代码三平台跑
- Windows 用户**不再依赖 Git Bash**——只需 Python 3.7+ 与 git CLI

### 转换清单

**Phase A**（v0.7.2 → v0.8.0 之间，标记为 [Unreleased] 中）：
- `init-gitignore.sh` → `init-gitignore.py`
- `migrate-v0.7.sh` → `migrate-v0.7.py`
- `promote-list.sh` → `promote-list.py`
- `weekly.sh` 删除 + `weekly.py` 增强 argparse

**Phase B helpers**（v0.8.0 落地）：
- `frontmatter.sh` → `frontmatter.py`
- `missing-summaries.sh` → `missing_summaries.py`
- `milestone.sh` → `milestone.py`（路径 glob 用 fnmatch 替代 bash case 匹配）
- `checkpoint.sh` → `checkpoint.py`
- `archive-hint.sh` → `archive_hint.py`
- `migrate.sh` → `migrate.py`（v0.2 → v0.3 自动迁移）
- `worktree-link.sh` → `worktree_link.py`（os.symlink + cmd /c mklink /J 两路兜底）
- `promote-scan.sh` → `promote_scan.py`

**Phase B entries**（v0.8.0 落地）：
- `session-start-brief.sh` → `session-start-brief.py`（最大入口，原 299 行 bash → 约 280 行 Python，逻辑全保留）
- `session-end-check.sh` → `session-end-check.py`
- `user-prompt-trigger.sh` → `user-prompt-trigger.py`
- `stop-check.sh` → `stop-check.py`
- `pre-compact-check.sh` → `pre-compact-check.py`
- `post-write-check.sh` → `post-write-check.py`

### 🐛 兼容性修复
- 测试基础设施全部去 bash 依赖：`tests/test_*.py` 改用 `sys.executable` 直接调 .py，删 `BASH` 常量、`as_posix()` 转换、UTF-8 二进制解码 hack（保留 `LANG=en_US.UTF-8` env 防 Windows GBK 影响 Python subprocess）
- `evals/run-hook-selftest.sh` 改调 `python3 user-prompt-trigger.py`

### 📚 文档
- README：里程碑白名单引用从 `milestone.sh` → `milestone.py`，验证 hook 命令从 `bash X.sh` → `python3 X.py`
- SKILL.md / 切档与归档.md：bash 路径改 python3 路径
- `commands/kdev-memory-promote.md` / `commands/kdev-memory-weekly.md`：脚本调用改 python3

### ⚠️ 升级指引

**对你的项目没有任何要求**：
- `.kdev/memory/` 目录格式不变
- CLAUDE.md 不需要改
- 不需要跑迁移脚本
- 跑 `/plugin update kdev-memory@kdev-agents` 后下一次会话自动生效

**Python 版本下限**：3.7（覆盖内网旧设备）。每个 .py 文件用 `from __future__ import annotations` + `typing.List/Optional/Dict` 兼容，运行时不依赖 PEP 604 / PEP 585 现代语法。

**外部脚本依赖 .sh**：v0.8 删除了 `plugins/kdev-memory/hooks/*.sh` 和 `plugins/kdev-memory/hooks/lib/*.sh`，无 wrapper 兼容。如果你的 CI/脚本直接调用过 plugin 的 .sh 文件，请改调对应的 .py。

## [0.7.2] — 2026-04-25

### 🔧 跨平台一致性
- **`weekly.sh` 重构**：把内嵌 `python3 - <<EOF` heredoc 拆到独立的 `hooks/lib/weekly.py`。weekly.sh 缩为薄 wrapper（参数解析 + 默认日期 + 调 `python3 weekly.py`），逻辑一行不少，可维护性更好
- **修 Windows Git-Bash subprocess 兼容**：原 heredoc 在 Windows Git-Bash 通过 Python subprocess 调用时 stdin 失败（returncode 49），重构后该限制消除
- **`test_weekly_aggregate.py` 移除 `@skip_on_windows`**：v0.7.1 的 7 个 weekly 跳过测试现在在 Linux/macOS/Windows 三平台都跑（v0.7.1 Windows 跑 117/13 → v0.7.2 应 124/6）

### 📚 文档
- 报告：[`docs/WINDOWS-COMPAT-REPORT.md`](../../docs/WINDOWS-COMPAT-REPORT.md) 已记录 v0.7.1 修复路径，本版本补齐其中"建议后续工作 #1"

## [0.7.1] — 2026-04-25

### ✨ 新增
- **Worktree 自动共享记忆**：secondary worktree（`.git/worktrees/<name>`）启动时 SessionStart hook 自动检测并建 symlink/junction `.kdev → 主 worktree/.kdev`，让多 worktree 共享同一份记忆（Step 编号、评分、决策实时同步）。`hooks/lib/worktree-link.sh` 新增
  - Linux / macOS：`ln -s`
  - Windows (Git-Bash / MSYS)：`cmd /c mklink /J`（NTFS junction，**无需管理员权限**）
- **Brief 增加「当前分支」一行**：让 Claude 在切分支后立刻知道分支语境

### 🐛 修复
- 测试 `test_promote_scan.py::test_time_trigger_over_7_days` / `test_escalate_to_p0_over_30_days`：把 flush 文件 mtime 锚定到测试硬编码的 `today=2026-04-24` 而不是真实时间，避免随真实日期推进出现 7 天边界漂移导致的测试不稳定（同 v0.7 trigger-match fixture date drift 同类问题）

### 📚 文档
- README 新增「Worktree 与多分支」章节：Linux/macOS/Windows 三平台 symlink/junction 行为、主 worktree 切分支不做特殊处理的理由、Windows 手动 fallback

### 🔧 兼容性
- 跨平台审计：`stat -c` / `date -d` 已有 BSD fallback（macOS）；`find -newer` / `grep -qxF` 跨平台 OK；新加的 worktree-link 在 MINGW/MSYS/CYGWIN 三种 Windows shell 环境下走 `mklink /J` 路径

## [0.7.0] — 2026-04-24

### 🔄 立场反转（breaking change in philosophy, not API）
- `.kdev/` 从"项目资产、跟代码 commit"改为"**本地过程目录，默认 gitignore**"
- init 时自动 append `.kdev/` 到项目 `.gitignore`（`KDEV_GIT_TRACK=1` 可跳过）
- 团队共享产物改走 `/kdev-memory-promote` + `docs/` 通道

### ✨ 新增
- **`/kdev-memory-promote`** 命令：列出 pending 沉淀候选 + 推荐去向，用户确认后写入 docs/ 并更新 promote_status
- **`/kdev-memory-weekly`** 命令：滚动 7 天周总结（默认 today-6 ~ today，可用 --from/--to 覆盖），输出按**汇报四段骨架**组织：
  - 📦 **过程资产**（机械盘点：Step/Q/G/R 条数、每日汇总覆盖率、条目索引）
  - 💡 **经验总结**（正向信号：4.5+ 高分 Step、踩坑升规则、稳扎稳打条目）
  - ⚠️ **问题教训**（负向信号：差值 ≥ 1.5 的 Step、低评分、未升规则的高频踩坑）
  - 🚀 **开发进展**（业务视角：主线叙事、里程碑、下期展望）
- **Schema 扩展**：Step / R / Q / G frontmatter 新增 `status: open | scored | voided-faded | voided-r-nnn`，R / Q / G / 改进建议新增 `promote_status: pending | done | skipped` + `promote_target` + `promote_date`
- **Brief 三层分层**：P0 硬阻塞（WARN / 今日欠评）/ P1 需核对（跨天汇总缺失 / 接口漂移 / 沉淀提醒）/ P2 参考（checkpoint / growth backlog）
- **销账识别**：Brief 欠评扫描优先读 `status` frontmatter，fallback 启发式 grep（`褪色补录` / `保留占位` / `非原生当场采集` / `## Step M-`）—— 解决 iter 5~8 meta 回补条目被反复报"待处理"问题
- `hooks/lib/init-gitignore.sh`：helper，初始化自动配 gitignore
- `hooks/lib/promote-scan.sh`：Brief P1 集成的沉淀候选扫描器
- `hooks/lib/promote-list.sh`：`/kdev-memory-promote` 命令聚合脚本
- `hooks/lib/weekly.sh`：`/kdev-memory-weekly` 命令聚合脚本
- `hooks/lib/migrate-v0.7.sh`：v0.6 → v0.7 软迁移（保留历史 commit）

### 🐛 修复
- SessionEnd WARN 不再依赖 git（立场反转后 `.kdev/` 默认 gitignore，git status 拿不到变化）—— 改为 `.last-flush` mtime 比对
- `post-write-check.sh` 写入 `.kdev/memory/*` 时自动 `touch .last-flush`（与 SessionEnd 的 mtime 机制联动）
- `trigger-match.py` 支持 `KDEV_TRIGGER_TODAY=YYYY-MM-DD` 环境变量固定"今日"基准，selftest 用它把 fixture 硬编码日期钉在 `2026-04-20`——修了 fixture date drift 导致 `should-trigger-Step-今日` eval 随真实时间推进而失败的长期问题（selftest 现稳定 10/10）

### 📚 文档
- README：对比表第三行最后一列、差异化设计点第 3 条全部重写；新增「为什么 .kdev/ 默认 gitignore」小节；新增「从 v0.6 升级到 v0.7」章节
- SKILL.md：新增"条目状态与沉淀字段"章节、"v0.7+ 自动加 .kdev/ 到 .gitignore"段
- references/六类记录-schema.md：Q / G / Step / R 各段同步 status / promote_* 字段
- 开发历程.md：新增 v0.7 立场反转章节

### ⚠️ 迁移指引
已装 v0.6 且 `.kdev/` 已 git tracked 的项目：

```bash
bash "${CLAUDE_PLUGIN_ROOT}/hooks/lib/migrate-v0.7.sh"
git diff --cached  # 核对
git commit -m "chore: .kdev/ 转为本地过程目录（kdev-memory v0.7 立场反转）"
```

历史 commit 保留（dog-fooding 证据）；未来 `.kdev/` 变更不再进 git。

## 0.6.0 — 2026-04-24

**特性**：Step 执行事实段新增「使用的 skill」结构化字段（方案 A 落地）+ Step 粒度指引（自然停顿点三信号 + 三映射 + 反模式）+ 当前状态.md body 的 TodoWrite 跟随记约定 + iter-8 discriminating eval 验证（eval-11 with_field 11/11 vs baseline 7/11）。

### 背景

0.5.1 之后回头看 2026-04-22 dev-note「skill 使用记录与体验评分维度缺口」——token-statistics Step 11 评分时用户反馈"没用到 skill 感受不明显"暴露出两件事：

1. **事实层缺 skill 追踪**：skill 使用情况散落在自由文本里，不是结构化字段 → 跨 Step 按 skill 聚合分析无锚点
2. **Step 粒度定义模糊**：SKILL.md 说"粒度比 commit 粗、比迭代细"——没说清"phase 级"还是"todo 级"，导致 skill 面对大需求拆 20 todos 4 phases 的场景无判断依据

session 决策采**方案 A**（事实层加字段，评分维度不动），不走方案 B（分两个评分维度）。方案 A 的理由：skill 正/负贡献能融进顺畅度 + 一句话评价；分两个数是过度设计。

粒度信号则从对话迭代中明确为**自然停顿点**（时长 / 干预 / 验收）三信号，不机械按 phase 或 todo 切。

### 新增

- **references/六类记录-schema.md §3「使用的 skill」字段**：
  - 事实段 schema 加 `- 使用的 skill：[bmad-create-architecture, subagent-driven]` 行
  - 字段语义块：列表 / 「无」/「N/A（对话驱动）」三态；硬规"触发过就必须列名"
  - N/A vs 无区分：N/A = 任务天然不需 skill；无 = 本该触发但没触发（异常信号）
  - 用途：跨 Step 按 skill 聚合做"skill 体感"分析的字段锚点

- **references/六类记录-schema.md §3「Step 粒度：自然停顿点」**：
  - 三停顿信号：时长（≥ 约 30min-1h / 工具调用约 30 次以上）/ 干预（需决策 Q-NNN）/ 验收（有可 review 产出）
  - 三种 phase 映射合法：1 phase → 1 Step（默认）/ 2 phase → 1 Step（都短 + 无干预）/ 1 phase → N Steps（有决策点切开）
  - 反模式：每 todo 一 Step（评分疲劳）/ 整需求一 Step（信号失真）/ 机械按 phase（phase 可能只是思维组织）
  - 闸门触发时机段：看三个停顿信号，不是看 todos 状态

- **references/六类记录-schema.md §7「进行中 Step 的 todos 分解」body 段**：
  - 当前状态.md body 示例加 todos 段
  - 更新时机列表加一条：TodoWrite 首次 emit 3+ todos 落段；状态变化顺手同步；Step 完成清空
  - 目的：跨 session 接力回读"当前 Step 做到哪了"；单个 todo completed 不触发 Step 闸门

- **SKILL.md 主文微扩**（+1 行净）：
  - L68 闸门字段枚举加「使用的 skill」（+0 行，同行扩）
  - L149 速览段 §3 括号里加粒度 anchor + 使用的 skill 字段（+1 行）
  - **主文净增 +1 行（287 → 286，功能表达反而更清晰）**

- **evals/fixtures/skill-quality/eval-11-skill-used-field/**：webhook-platform 项目
  - 半残 Step 52（Webhook 重试机制）：用了 bmad-create-architecture + subagent-driven，用户评分段空
  - 新建 Step 53 场景：纯对话驱动目录整理（skill N/A 用例）

- **evals/skill-quality/evals.json 新增 eval-11**（id=11）：
  - prompt 同时测"有 skill 使用场景"和"N/A 对话驱动场景"
  - 11 条 assertions，核心测字段是否被结构化落盘 + N/A 是否正确识别 + 粒度判断 + 锁定铁规

- **iter-8 discriminating eval**（`evals/skill-quality/iterations/20260424-08-skill-used-field/`）：
  - baseline（v0.5.1）：**7/11 (≈64%)** — fail #1/#2/#3，partial #7，全指向 schema 层缺字段
  - with_field（v0.6.0 候选）：**11/11 (100%)**
  - 关键：baseline subagent 主动识别局限"想聚合分析哪些 Step 没用 skill / 哪些 skill 最高频时只能全文扫描"
  - 额外：with_field subagent 自发补"补录感受褪色"备注（超预期诚信）+ 准确区分 N/A vs 无语义

### iter 数据累积

| iter | 场景 | 结果 | 决策 |
|---|---|---|---|
| iter-8 | eval-11 使用的 skill 字段 + Step 粒度 discriminating | 7/11 → 11/11 | **合入**（behavior 质量提升，非成本下降）|

### 向后兼容

- **老 Step 条目不追溯**：v0.6.0 前的 Step 没有「使用的 skill」字段是正常的，skill 不会倒着改老条目
- `claude_md_contract` 未变：字段属 skill 实现细节，不是接口契约（dev-note 明确排除）
- CLAUDE.md 模板零改动：规则段不复述 schema 字段
- 0.5.x 老项目升级 0.6.0 后，下次触发新 Step 时自动按新 schema 写（老条目保持不变）

### 设计决策

- **为什么是 minor（0.6.0）不是 patch**：schema 字段扩展是隐式接口变化——未来 hook（如 check-step-completeness）会看到字段；评判为 minor bump 是精确表达
- **为什么不加 skill 体验感评分维度（方案 B）**：
  - skill 正/负贡献判断和顺畅度是同一把尺（"这 skill 帮到我没"）——分两个数字是过度设计
  - 两个数让用户每步做两次判断，采集负担 +1，ROI 不划算
  - 单一顺畅度 + 事实层 skill 名单：跨 Step 聚合分析靠"skill 名单 + 顺畅度"已经够
  - dev-note §决策源原文明确排除方案 B
- **为什么 Step 粒度是"自然停顿点"而不是"phase = Step"**：
  - 硬规则 phase = Step 有反例：两个短 phase 中间无干预就应合；一个长 phase 有决策点就应切
  - 真正的判断依据是"人-模型协作节奏"—— 30min-1h 连续独立执行 / 需决策 / 有可 review 产出
  - 这把决策权还给 skill 的判断，给出三信号作 anchor
- **为什么 SKILL.md 主文只加 1 行**：每次 skill 触发都要加载主文，行数直接等于 token 成本；iter-7 教训是一次性 vs 每次成本分开算——细则全放 references（按需读），主文只留 anchor
- **为什么跑 discriminating eval 而不是"直接合"**：iter-7 启示是不要预判经济性——跑一轮数据验证字段加入是否真让 skill 行为变好。本次结果确认 64% → 100%，behavior 质量信号清晰

### 不纳入 v0.6.0 的候选（留 v0.7.x）

- **PostToolUse matcher=TodoWrite hook**：自动在 phase 末端提醒 Step 闸门——先让手动约定跑 2 周观察痛点频率
- **跨 Step "skill 体感"聚合分析召唤词**（"分析 skill 体感 / skill 质量盘点"）：留 v0.7.x 的新能力扩展
- **多会话同项目编号冲突检测**：暂靠文档约定（git 原生分支处理）+ 后续加 Stop hook 检测 warn；不做 assignment 代码

### 相关 commit

- commit `<本 commit>` feat(kdev-memory): 0.6.0 — Step 事实层加「使用的 skill」+ Step 粒度指引 + todos 跟随记 + iter-8 验证

## 0.5.1 — 2026-04-23

**特性**：SKILL.md 新增「🔴 Step 完成硬闸门（四段必填）」章节 + Step 完整度
lint（P1-5/6 落地）+ iter-5/6/7 三轮 eval 数据归档。

### 背景

0.5.0 发布后做了两件事：一是 iter-5 补齐跨会话续航场景覆盖（skill description
承诺的 5 个核心触发场景至此全部 eval 过）；二是 iter-6 落地审计 P1-5/6（Step
完整度 lint，覆盖 SessionStart brief 欠评告警 + Stop hook check-step-completeness
阻塞）；三是 iter-7 用 discriminating eval 回答"审计 P0-1 Step 完成闸门章节是否
应当加"。

iter-7 初步结论"不加"，但 user 反问"如果 baseline 换成 with_gate，是不是效果
一样的情况下，还减少了 md 的内容"——这个反问点出经济性估算的 bug：
- SKILL.md +22 行是**一次性**成本（约 +500 tokens/加载）
- skill 推理 + 搜索引用是**每次**成本（with_gate 比 baseline 省 -12,143 tokens）
- 净收益：**每次触发净省 ~11.6k tokens**（扣除加载成本后）

按 kdev-memory 活跃项目每天触发 20+ 次算，每天净省 ~230k tokens。+22 行文档是
值得的。**决策反转：合入闸门章节**。

### 新增

- **SKILL.md 新增「🔴 Step 完成硬闸门（四段必填）」章节**（约 26 行，替换
  v0.5.0 留下的 placeholder 注释）：
  - 四段必填硬判定（执行事实 / 模型自评 / 用户评分 / 评分差异分析 任一缺 = 未完成）
  - 动作链（模型写自评 → 公布 → 主动追问 → 锁定时分戳 → 才能开下一步）
  - 反模式声明（"模型写完自评就认为 Step 完成"）
  - 用户明确跳过评分时走 R-NNN 销账（不走默认路径）
  - iter-7 数据注记（-21% tokens / -35% tool uses）
- **`hooks/lib/step_completeness.py`**（203 行，纯 Python 无外部依赖）：
  扫执行日志最近 N 条 Step，检测用户评分段时分戳空 / 扣分项空 / 完全无用户评分段
- **`tests/test_step_completeness.py`**（33 tests）：项目累计 **98 tests pass**
- **SessionStart hook 集成 Step 完整度 lint**：brief ⚠️ 段加欠评 Step 告警
- **Stop hook 集成 Step 完整度 lint**：今日新增半残 → 软提醒；strict 模式下 exit 2 阻塞
- **`evals/skill-quality/evals.json` 新增 eval-9 (step-half-complete-fix) + eval-10
  (step-gate-discriminating)**，共 **10 个场景** + **7 轮 iteration**

### iter 数据累积

| iter | 场景 | pass rate | 发现 |
|---|---|---|---|
| iter-5 | eval-6 跨会话续航 | 8/8 | skill 严格只读回读，语义理解到位 |
| iter-6 | eval-9 Step 半残修复 | 8/8 | skill"坦诚反思"路线补齐（超预期） |
| iter-7 | eval-10 Step 闸门 discriminating | 2 configs 行为一致 | P0-1 应当加（经济性驱动）|

### 审计 §5.1 落地最终状态：7/8

| 审计项 | 状态 | iter |
|---|---|---|
| P0-1 Step 完成闸门 | ✅ 合入 SKILL.md | iter-7 + 0.5.1 |
| P0-2 动词链 | ✅ 已隐含（P0-1 章节带动作链）| iter-7 + 0.5.1 |
| P0-3 豁免动作化 | 🟡 v0.6.0 候选 | — |
| P0-4 Step 脱离状态机 | ✅ 已隐含 | Phase 1 |
| P1-5 brief 欠评告警 | ✅ | iter-6 + 0.5.1 |
| P1-6 Stop check-step-completeness | ✅ | iter-6 + 0.5.1 |
| P1-7 CLAUDE.md 漂移检测 | ✅ | iter-4 |

### 向后兼容

- 0.5.x 内部升级完全兼容：SKILL.md 增量字段、新 lib、hook 非阻塞集成
- 老项目 CLAUDE.md 零改动——闸门章节在 skill 本体不需要出现在 CLAUDE.md
- Strict 模式仍需 opt-in（`touch .kdev/memory/strict`）

### 设计决策

- **为什么是 patch 而不是 minor**：
  - SKILL.md 闸门章节是"显式化已有隐含规则"——baseline 数据已证明行为一致
  - Step 完整度 lint / hook 改动是 hook 层内部扩展，对外接口不变
  - 不新增召唤触发词、不改 `claude_md_contract`
- **为什么 iter-7 结论会反转**：
  - 初次分析把 SKILL.md +22 行当"代价"、-21% tokens 当"收益"
  - 但两者不同量纲：+22 行是一次性写入，-12k tokens 是每次触发
  - user 反问点破这个误判，基于"长期 × 频率"的经济性修正了决策

### 相关 commit

- commit `c7e125c` feat: Step 完整度 lint（P1-5/6）+ iter-6 eval-9
- commit `f695370` test: iter-7 P0-1 discriminating（初版 "不加" 结论）
- commit `<本 commit>` chore: 0.5.1 + 合入闸门章节 + iter-7 决策反转

---

## 0.5.0 — 2026-04-22

**特性**：SKILL.md 拆分为 references/ 渐进式披露（-65% 行数，-19.6% 触发
token）+ CLAUDE.md 规则段接口 / 实现解耦（`claude_md_contract` 契约化）+
`claude_md_lint.py` 自动漂移检测 + 修漂移一键 diff patch 流程 + skill-quality
eval 线（4 轮 iteration 14 runs 数据驱动）。

### 背景

0.4.0 之后发现更深层问题：**项目 CLAUDE.md 的规则段与 skill 会漂移**。
根因审计（见 `docs/skills/kdev-memory/dev-notes/2026-04-22-skill-CLAUDEmd
模板漂移审计-token-statistics与KDevSec对照.md`）指出：

- token-statistics 项目 CLAUDE.md 是 v0.2.0 时代写的 snapshot
- skill 从 v0.2 → v0.3 → v0.4.0 升级了 6 版，每版都有新内容
- 老项目 CLAUDE.md 永远停留在首次初始化时的版本 → 规则失效 → 执行失守
- 原 SKILL.md 没有"项目升级时重写 CLAUDE.md"的路径

同时 SKILL.md 本身也膨胀到 734 行，渐进式披露没有真正落地——每次 skill
被触发都要把所有场景细节拉入上下文，浪费 context 预算。

### 新增

- **SKILL.md 拆分为 6 个 references/**（Phase 1 重构）：
  - `六类记录-schema.md` / `triggers-写法.md` / `初始化-claude-md-模板.md`
  - `切档与归档.md` / `规则升级流程.md` / `自动化机制-hooks.md`
  - SKILL.md 从 734 行瘦身到 260 行（-65%）；description 从 ~1400 字精简到
    ~640 字。每次触发 skill 只拉 SKILL.md 本体，场景相关细节按需 Read
    对应 reference —— iter-2 验证：tokens 平均省 -19.6%，pass rate 100%
    vs 100% 与 0.4.0 行为等价。

- **CLAUDE.md 规则段接口 / 实现解耦**：
  - `references/初始化-claude-md-模板.md` 顶部加 YAML frontmatter
    `claude_md_contract` —— 显式声明 skill 对外的稳定接口：
    - `cross_session_rules`：3 条贯穿 session 铁规（实时落盘 / 文件聚合
      不翻会话 / 优先处理 hook 产出）
    - `hook_injection_tags`：`<kdev-memory-brief>` / `<kdev-memory-recall>`
    - `hook_file_patterns`：`.kdev/memory/WARN-未记录-*.md` /
      `.kdev/memory/checkpoints/压缩前-*.md`
  - CLAUDE.md 规则段**只放接口**，删掉 17 行触发表 / 评分机制 / 编号规则 /
    hook 行为响应表——这些都是 skill 实现细节，随版本演进会变，留 SKILL.md
    本体。
  - iter-3 验证：eval-0 init 场景 CLAUDE.md 从 57 行精简到 38 行（-33%），
    边缘场景（eval-4 合并冲突 / eval-5 数据缺失 / eval-7 WARN 处理）全部
    0 regression。

- **`hooks/lib/claude_md_lint.py`** 接口漂移检测工具：
  - 读 skill 的 `claude_md_contract` + 项目 `CLAUDE.md` 规则段，字面子串
    匹配 + 关键词宽松命中，识别缺少的 hook 标签 / 文件模式 / 贯穿铁规
  - 5 种状态：`ok` / `drift` / `no-claude-md` / `no-kdev-section` /
    `contract-parse-error`
  - 纯 Python 无外部依赖，CLI + 库双用途
  - 21 个单元测试（tests/test_claude_md_lint.py），项目累计 65 tests pass

- **SessionStart hook 集成 lint**：
  - 每次新会话自动比对，漂移时在 `<kdev-memory-brief>` 的 ⚠️ 待处理段
    里列出缺什么 + 提示用户召唤 skill 说「修 CLAUDE.md 漂移」
  - 失败静默降级（contract 解析错 / lint 库缺失都不影响其他 brief 内容）

- **`references/初始化-claude-md-模板.md` 加「修漂移」流程章节**：
  - 6 步动作路径：读 contract → 读 CLAUDE.md → 逐项比对生成最小化 diff
    → 展示给用户 → 用户批准后 Edit → lint 复验 `status=ok`
  - 4 条铁规：只管辖 kdev 章节 / 用户手改保留 / 展示+批准+执行分离 /
    降级安全
  - SKILL.md description 加召唤触发词"修 CLAUDE.md 漂移 / 接口漂移 /
    claude.md 对齐 skill / claude.md 升级"

- **skill-quality eval 线**（evals/skill-quality/）：
  - skill-creator 风格的完整 eval 基础设施：8 场景 fixture（init /
    daily-summary / rule-upgrade / archive / merge-conflict / missing-data /
    cross-session-resume / warn-file）+ contract 接口变更专测
    eval-8-claude-md-drift
  - 4 轮 iteration 数据：
    - iter-1 首轮 3 场景探索（基础 assertions）
    - iter-2 扩展 6 场景（升级 assertions + 12 runs，验证 Phase 1 重构）
    - iter-3 解耦 4 场景（8 runs，CLAUDE.md 57→38 行且零 regression）
    - iter-4 lint 落地 1 场景（2 runs，with_skill 100% vs baseline 75%）

### 向后兼容

- **0.4.x 老项目 CLAUDE.md 零改动继续工作**：lint 只是 ⚠️ 提示，不阻塞
  任何动作；缺少新接口条目时 hook 不会阻断，只是用户看不到新功能的完整
  体验
- `claude_md_contract` 遵循 append-only 原则：新增 hook 标签 OK，改名或废弃
  要走 deprecation 周期
- 所有现有 hook / triggers / `.kdev/memory/` 结构 / 编号体系（Q-NNN /
  G-NNN / R-NNN / Step N）完全不变
- 项目内用户自定义加入规则段的内容（如第 4 条贯穿铁规）**受保护**，修漂移
  流程只加不删用户手写的行

### 设计决策

- **为什么是"解耦 + lint"而不是审计原方案（版本号标记 + 一键重写）**：
  - 版本号标记需要用户理解语义化版本 + 需要"迁移脚本"思路 → 每次升级都是
    风险点
  - `claude_md_contract` 让"什么是接口"成为机器可读声明 → lint 自动比对
    → diff 自动生成 → 用户只审 3 行 patch 而不是审整段合并
  - 用户手改保护天然成立：lint 只管辖 contract 里声明的字段，其他行不碰
- **为什么 SKILL.md 本体里保留 3 条贯穿铁规**：这些需要 Claude 每一步都
  下意识遵守（实时落盘 / 不翻会话 / hook 产出响应），不能依赖"被召唤"才
  触发。其他场景（初始化 / 切档 / 升级）都是用户主动发起 → 被动召唤就够
- **为什么不在 plugin 升级时自动硬改 CLAUDE.md**：硬改有三个风险——覆盖
  用户自定义、合并策略复杂、失败难恢复。改为"hook 只检测 + skill 召唤
  时执行 + 用户批准"三步分离，每一步单一职责
- **为什么 baseline 6/8 pass 也是可接受结果**：iter-4 对照显示 iter-3
  解耦架构本身就 self-documenting——baseline 通过 `claude_md_contract` +
  合并策略能正确推理出行为（识别漂移 + 暂停等用户裁决）。新版的增量是
  把多轮裁决压到单步闭环，不是"修复 baseline 的错误"

### 相关文档

- 审计文档：`docs/skills/kdev-memory/dev-notes/2026-04-22-skill-CLAUDEmd
  模板漂移审计-token-statistics与KDevSec对照.md`
- session 对账：`docs/skills/kdev-memory/dev-notes/2026-04-22-审计修订
  对账-session-end-state.md`
- iter-3 解耦 notes：`plugins/kdev-memory/evals/skill-quality/iterations/
  20260422-03-decoupled-claude-md/notes.md`
- iter-4 lint notes：`plugins/kdev-memory/evals/skill-quality/iterations/
  20260422-04-claude-md-lint/notes.md`

---

## 0.4.0 — 2026-04-21

**特性**：长项目的按期归档机制（执行日志按月、踩坑/决策按季度）+ 单元测试层
（44 个 stdlib unittest，覆盖 trigger-match.py 的 7 类核心逻辑）+ README 差异
化定位（与 Claude 官方 auto memory / claude-remember 等方案的关系说明）。

### 背景

0.3.0 引入 triggers 智能召回后，`.kdev/memory/` 主文件会随项目推进线性膨胀。
半年下来执行日志 1000+ 行、踩坑日志 几十条 G-NNN，Claude Read 效率下降、
UserPromptSubmit hook 全文扫描性能也吃力。SKILL.md 原本有"超 500 行按迭代切
档"的人工建议，但无自动化提醒、无归档约定、无配套扫描支持。

同时 Anthropic marketplace 上出现同类记忆方案（如 claude-remember），用户需要
判断"什么时候装哪个 / 会不会重复造轮子"——README 需要给出差异化定位。

### 新增

- **`.kdev/memory/归档/` 子目录约定**：
  - `执行日志.md` 按月切到 `归档/执行日志-YYYY-MM.md`
  - `踩坑日志.md` 按季度切到 `归档/踩坑日志-YYYYQN.md`
  - `决策日志.md` 按季度切到 `归档/决策日志-YYYYQN.md`
  - `改进建议.md` **不切档**——它是喂给未来 skill 作者的原料库，完整性优先
- **`hooks/lib/archive-hint.sh`**：新建共享库，日期→季度换算 + 跨期检测。
  用最早条目日期而非行数阈值判断，避免"拍脑袋定多少行"。
- **Stop hook 第 6 条软提醒**：主文件最早条目不在当月（执行日志）或当季（踩
  坑/决策日志）时注入 📦 归档提醒文本，指向 `归档/` 子目录下的目标文件名。
- **trigger-match.py 的 `_iter_memory_files()` 辅助**：所有归档扫描统一走
  "主文件 + `归档/` 子目录"两路。踩坑日志归档后**仍参与召回**（老坑也要防重
  踩），执行日志归档后被今日/昨日过滤剔除，实际等效只扫主文件。
- **`tests/test_trigger_match.py`**：44 个 stdlib unittest（零外部依赖），覆盖
  SanitizePrompt / ParseTriggersValue / ParseMultilineTriggers / MatchEntries /
  DedupFilter / TTLPrune / GlobScan。包含"归档目录隔离"测试——防止
  glob 误把同目录下其他前缀的归档文件（如 `执行日志-2026-03.md`）混入
  踩坑扫描结果。
- **SKILL.md §「文件切档与归档」**：整章新增，含切档规则一览 / 何时提醒 /
  操作步骤 / 铁规（搬家而非删除、编号保留、主文件顶部留"历史归档"索引）/
  召回逻辑变化说明。SKILL description frontmatter 加"切档 / 归档一下 / 归档
  执行日志"触发词，让 Claude 能在用户说切档时自动召唤本 skill。
- **`plugins/kdev-memory/README.md` §「这个插件和其他记忆方案的关系」**：顶
  层章节，讲清楚三类记忆工具（官方 auto memory / 会话压缩类 / 本插件）正交
  不重叠、五大差异化设计点、推荐同装。未点名任何第三方插件避免维护负担。
- **`docs/design-notes/2026-04-21-三方记忆方案对比-官方auto-memory-vs-claude-remember-vs-kdev-memory.md`**：
  三方机制对比、互补性矩阵、借鉴项决策的设计文档。

### 向后兼容

- 0.3.x 项目升级到 0.4.0 **零改动即可运行**：没有 `归档/` 子目录时，glob
  扫描退化为单主文件，行为完全一致。
- 归档是**人工触发 + Claude 提醒**，不自动执行——收到 📦 提醒后必须询问用
  户同意才能切档，避免误迁老数据。
- 现有 triggers 条目、编号体系（G-NNN / Step N / Q-NNN / R-NNN）跨档保持不
  变，切档只是"搬家"不改结构。

### 设计决策

- **为什么按月/按季度而不是统一按季度**：执行日志粒度最细（每步一条）、膨
  胀最快，按月切合理；踩坑/决策是慢积累，按月会造成过多小碎片，按季度刚好。
- **为什么改进建议不切档**：消费者不是当前项目而是未来 skill 作者——跨项目
  review 需要看全集，切档会损害聚类归纳的质量。
- **为什么不用 Haiku 做压缩归档**（借鉴了 claude-remember 但没照抄）：
  - 会违背 kdev-memory 的"零外部 API 成本"卖点
  - Haiku 压缩会丢失 R-NNN 的"用户原话 / 事实段 / 评分差值"——这些恰恰
    是下游 skill 作者最需要的原始证据
  - 切档比压缩简单、可逆、无信息损失，是更合适的工具
- **为什么归档放子目录不平铺**：几年后顶层会被几十个归档文件淹没，子目录让
  `ls .kdev/memory/` 的输出始终整洁，glob 扫描也更精确。

### 自验证

- 44 个 unit tests 全通过（`python3 -m unittest discover tests`）
- 端到端：构造主文件 + `归档/` 子目录的 fixture，UserPromptSubmit hook 正确
  从归档文件召回老 G-NNN 条目，注入路径显示 `.kdev/memory/归档/踩坑日志-2026Q1.md`
- Stop hook 跨期场景输出 📦 提醒，格式和路径（`归档/执行日志-YYYY-MM.md`）
  正确；无跨期数据时静默不误报

### 文档同步

- `plugins/kdev-memory/README.md` 顶层差异化卖点 + 目录结构加归档子目录
- `plugins/kdev-memory/skills/kdev-memory/SKILL.md` 切档章节 + 触发规则段 📦 + description 加触发词
- `plugins/kdev-memory/hooks/hooks.json` description 补归档提醒/两路扫描
- `plugins/kdev-memory/.claude-plugin/plugin.json` description 补归档切档；keywords 加 archive
- `plugins/kdev-memory/evals/README.md` 加"纯单元测试"章节指向 tests/
- `README.md`（仓库根）六层 → 七层（0.3.0 历史遗漏顺手修）+ 目录示例补 tests/ 和 evals/

### 文档后续完善（post-release，纯文档无代码变化）

- `SKILL.md` 新增「**规则升级流程**」章节：定义"R-NNN 同主题 ≥ 2 次 / 方法
  论铁规被引用 ≥ 3 次 / 用户明确表达"三类升级触发信号；规定 Claude 必须问
  用户三件事（升不升级 / 放哪 / 加不加 triggers）、严禁替用户拍板；定义升级
  搬家规则——**标记而非删除**，源 R-NNN 原文一字不改，只在末尾加
  `> 升级状态：YYYY-MM-DD 升级到 xxx` 标记，改进建议.md 作为"下游 skill
  作者的原料库"完整性不被"已升级"破坏；和「文件切档与归档」正交（切档按
  时间搬家、升级按重要性搬家）
- SKILL description frontmatter 加升级触发词（"这条以后都要遵守 / 加到项目
  规则 / 写进宪章 / 变成硬规矩 / 升级成铁规"），让 Claude 能在用户这么说时
  自动召唤 skill
- 触发规则段模板加一条 🔴 铁规 + 表格一行，把升级流程同步给每个新项目的
  CLAUDE.md
- 「方法论铁规.md」章节补一段"和项目级宪章的关系"，明确铁规.md（只给 AI 看）
  vs 项目根 `constitution.md/AGENTS.md`（对外宣称、人类也读）的分层语义

---

## 0.3.1 — 2026-04-21

**增强**：跨天会话场景的每日汇总兜底提醒。

### 背景

Claude Code 的 hook 体系是事件驱动（SessionEnd / Stop / PostToolUse / ...），
没有"日期变更"事件。晚上 23:55 干到次日 01:30 不关会话的真实场景下：
SessionEnd 不触发 → 昨天的每日汇总被静默遗漏 → 第二天新会话开局 Claude
也不知道有缺口。0.3.0 的 Stop hook "今天无汇总"规则只看今日，无法覆盖
这个 gap。

### 新增

- **`hooks/lib/missing-summaries.sh`**：共享库函数
  `list_missing_past_summaries()`。扫 `.kdev/memory/{执行日志,决策日志,
  踩坑日志,改进建议}.md` 里所有 `日期：YYYY-MM-DD` 行，返回"严格早于今日
  且 `每日汇总/<date>.md` 缺失"的日期（最近 5 个，升序）。
- **Stop hook 第 5 条软提醒**：发现过去日期缺汇总时注入提醒文本，显式说明
  "典型原因是跨天会话未关"，指引 Claude 按日聚合源文件而不是回翻会话。
- **SessionStart hook `<kdev-memory-brief>` ⚠️ 待处理段**：startup / resume /
  compact 三种模式都会把缺失的过去汇总日期列出。这样即便用户忽略了 Stop
  的提醒、新开会话时还能再看到一次。
- **SKILL.md § "三层触发方式"**：Stop hook 描述从"三条提醒"扩到"四条提
  醒"，明确说明跨天会话场景。

### 设计原则

- 软提醒、不阻塞：跨天遗漏一天不写汇总没到 strict 模式 `exit 2` 的严重
  级别。strict 仍只管"今天执行日志空 + 工作区有变更"。
- 不回翻会话：提醒文本显式禁止 Claude 凭印象补写，要求按日期从源文件聚合；
  若某日源文件信息不足，在汇总里坦白标注。
- 最近 5 条封顶：防止老项目启用 kdev-memory 时刷屏。

### 自验证

- 10/10 evals 通过（`run-hook-selftest.sh`），未破坏既有召回机制
- 端到端 fixture 测试：2 个缺失日期在 Stop 和 SessionStart 都正确浮现

---

## 0.3.0 — 2026-04-20

从 0.2.0 的"六层防线"升级到 **"七层防线 + 目录命名空间化 + 智能召回"**。
核心目标：把记忆从"档案馆"升级为"会主动浮现"的闭环系统——已经踩过
的坑不再重复，做过的决策能自然复用。

### 新增

- **UserPromptSubmit hook**（`hooks/user-prompt-trigger.sh` +
  `hooks/lib/trigger-match.py`）：用户每次发 prompt 时扫
  `.kdev/memory/` 里所有带 `triggers:` 的条目做 literal substring
  匹配，命中就注入 `<kdev-memory-recall>` 指针给 Claude。**渐进式
  披露**——只给编号+标题+路径，不塞全文，让 Claude 自己决定是否
  Read 细节。
  - 扫描 4 个数据源：G-NNN 全部 / Step 今日-昨日 / 方法论铁规 全部 /
    项目级 spec 7 个约定路径
  - Prompt sanitize：strip 代码块 / XML tag / URL / 文件路径 /
    git diff（避免字面量误触发）
  - Session 去重：`.kdev/memory/state/trigger-sessions.json`，
    60 分钟 TTL，每 session 限额 3 条（借 OMC 经验 + 避开 issue #240
    的同类坑）
  - 借 OMC (oh-my-claudecode) 的成熟做法设计：literal 子串匹配、
    toLowerCase、文件落盘去重；但放弃 OMC 直接塞全文的做法，改用
    渐进式披露
- **triggers 字段写法规范**（SKILL.md §8 新增章节）：
  明确 G-NNN / Step / 铁规 / spec 四类条目的 triggers 标注方式、
  三种合法格式（JSON 数组 / 逗号分隔 / YAML 多行）、关键词选择原则
  （3-5 个、中英文、口语词、场景+特征）
- **项目级 spec 约定路径扫描**：`constitution.md` / `spec.md` /
  `principles.md` / `AGENTS.md` / `.specify/constitution.md` /
  `docs/constitution.md` / `docs/principles.md`——存在即扫，支持
  文件级 frontmatter 或行内 `## 规则 + triggers` 两种格式

### 变更（破坏性 → 零感知迁移）

- **`.kdev/` 重构成插件命名空间容器**：所有 kdev-memory 产物从
  `.kdev/` 根目录平铺迁到 `.kdev/memory/` 子目录。未来其他 kdev
  插件（kdev-commit、kdev-triggers 等）可以建兄弟子目录互不干扰。
- **自动迁移**（`hooks/lib/migrate.sh`）：所有 hook 启动时调
  `kdev_memory_migrate`，检测 0.2.0 平铺结构自动搬家到
  `.kdev/memory/` 子目录，留 `.kdev/MIGRATED-YYYY-MM-DD.md`
  清单给用户看。**从 0.2.0 升级完全无感**——第一次打开项目
  就自动完成，用户不用手工做任何事。
- 所有 hook 脚本 `KDEV_DIR` 从 `.kdev` 改到 `.kdev/memory`；软提
  醒文本里的路径同步更新到 `.kdev/memory/*`
- `hooks/lib/milestone.sh` / `hooks/lib/frontmatter.sh` 兼容新旧
  两种路径（优先新路径，fallback 老路径）
- SKILL.md 目录结构图重绘；描述增加 triggers / 召回相关触发词
- README.md Hook 章节从"六层防线"改写为"七层防线"，加"命名
  空间约定"和"UserPromptSubmit 智能召回"两个新章节

### SKILL.md 里新增的触发规则段铁规（CLAUDE.md 贴段）

- 🔴 每写一条新 G-NNN / Step / 铁规，紧跟标题下一行加
  `triggers: [...]` 关键词列表（3-5 个用户会说的词，中英文都要）
- 🔴 看到 `<kdev-memory-recall>` 注入时先判断相关性，字面子串
  匹配有假阳性；相关再 Read，不相关忽略，不要为了"用起来"强行
  靠拢

### 兼容性

- 0.2.0 → 0.3.0 完全向后兼容（自动迁移 + 双轨 fallback）
- 没标 `triggers:` 的条目不影响现有功能，只是不会被自动召回
  （退回到 0.2.0 的"档案馆"体验）
- 缺 python3 → UserPromptSubmit 静默降级（其他 6 层 hook 继续工作）

---

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
