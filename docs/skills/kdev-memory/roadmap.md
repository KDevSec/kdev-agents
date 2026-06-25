# kdev-memory Roadmap — 对齐 ieidev-team memory 的跟进清单

> 生成于 2026-06-25。对比基线：kdev-memory **0.18.3**（本仓 `plugins/kdev-memory/`） vs ieidev-team memory **0.5.0**（`/home/lyadmin/Projects/ieidev-team/`）。
> 两套子系统**同源 fork**（`hooks/lib/` 同构、SKILL/references 一一对应），互相回流（kdev 0.18.3 刚从 ieidev 0.4.7 backport 了 GCM 非交互修复）。本文只盘点 **ieidev 领先、kdev 该跟** 的部分，并区分「通用记忆能力（该跟）」与「数字员工 team 编排耦合（不该照搬进独立插件）」。
> 对比方法：4 路并行只读 diff（新增 lib 模块 / 共享 lib / SKILL+references / hooks+agent+CHANGELOG），命名噪音（ieidev↔kdev、.ieidev↔.kdev）已 `sed` 归一化后再判实质差异。P0 断言已按项目 **R-009「先核代码再信设计」** 直接核 kdev 源码确认（见每条「✅ 已核实」）。

---

## TL;DR — 三个层级

| 层级 | 内容 | 与架构决策的关系 | 建议 |
|------|------|------------------|------|
| ~~P0 立刻修~~ ✅ | 时间戳 ID 双认回归（weekly / distill_trigger / distill 漏认 Q-020 后的新条目） | **完全独立**，纯 bug | **已实施 2026-06-25**（commit `a8377a6`，+6 TDD 用例） |
| ~~P1 短期跟~~ ✅ | sync 层三件套（`init-local` / `sync: off` / 失败会话内提示） | 独立于 JSONL | **已实施 2026-06-25**（commit `6f4296f`，+14 TDD 用例） |
| **P1b 调查中** | Windows hook 控制台闪窗（上游缺陷）+ wrapper 加固 backport（CRLF/.gitattributes/PYTHONUTF8/单行 exec） | 加固独立普惠双队列；闪窗本身 = Claude Code 上游 **not-planned**，pythonw 可能白费 | 加固**随 P1 一批做**；闪窗走 Windows 实验闸定夺 |
| **P2 需决策** | JSONL 叙事主账（Plan D Phase 2）+ checkpoint 瘦身 | **大架构升级**，已有 P-C2 设计稿未实施 | 先拍「kdev-memory 是否迁 JSONL」，再排实施 |

**不跟清单**（team 编排耦合，独立 kdev-memory 无意义）：`delegation.py`、`recall.py` 的 events/handoffs 部分、`block-advance-past-gate.py`、`cqo-event-audit.py`、`claude_md_merge.py` 的 shim 化。详见 §5。

**kdev 反而领先、别回退**：Windows UTF-8 subprocess 修复、`brief.verbosity` 三档、正确的 `kdev-memory:` marker 前缀。详见 §6。

---

## P0 — 时间戳 ID 双认回归（真 bug，已在生效）　✅ 已实施 2026-06-25（commit `a8377a6`）

**背景**：kdev 自 **Q-020 / v0.17** 起所有新记录改用时间戳 ID（`Q 20260617-...`、`F 20260613-...`，空格分隔），legacy 顺序 ID（`Q-001`）冻结。双认逻辑由 [`step_id.py:268` `id_label_fragment()`](plugins/kdev-memory/hooks/lib/step_id.py#L268) 单一托管。kdev 已在 [distill.py:72](plugins/kdev-memory/hooks/lib/distill.py#L72)、`step_completeness.py`、`trigger-match.py` 用了它——**但漏改了下面三处**，仍是硬编码 `X-\d+`。ieidev 已全部堵上。

**后果**：v0.17 之后所有新 Q/G/R/F 都是时间戳形，被这三处**系统性静默漏掉**。这与当前 brief 里「改进建议 8 条 pending、踩坑 11 条 pending」长期堆积、周报/蒸馏不提醒的现象吻合。

### 三处漏点（✅ 已核实 kdev 源码）

| # | 位置 | 现状（硬编码） | 漏掉什么 | 修法 |
|---|------|----------------|----------|------|
| 1 | [weekly.py:89-91](plugins/kdev-memory/hooks/lib/weekly.py#L89) | `r"^##\s+Q-\d+.*$"` / `G-\d+` / `R-\d+\|建议...` | 周报漏掉所有时间戳形 Q/G/R 条目 | 换 `id_label_fragment('Q'/'G'/'R')` |
| 2 | [weekly.py:95](plugins/kdev-memory/hooks/lib/weekly.py#L95) + [:163](plugins/kdev-memory/hooks/lib/weekly.py#L163) | `re.search(r"R-\d+", g["body"])` | 关联 R 判定失效 → 所有踩坑被误判「未解决」，污染周报 + `当前状态.md` 的 `unresolved_gotchas` | 换 `id_label_fragment('R')` |
| 3 | [distill_trigger.py:194-195](plugins/kdev-memory/hooks/lib/distill_trigger.py#L194) | `r"^##\s+F-\d+"` / `R-\d+` | auto-distill 新增 F/R 计数漏报 → 沉淀候选堆积却不触发蒸馏提醒 | 换 `id_label_fragment('F'/'R')` |
| 4 | [distill.py:238](plugins/kdev-memory/hooks/lib/distill.py#L238) | `is_skill_feedback_high()` 用 `entry_id.startswith("F-")` | 时间戳形 `F 2026...`（空格）漏认 → skill-feedback 切片缺高分反馈（同文件 [:380](plugins/kdev-memory/hooks/lib/distill.py#L380) 计数已双认，唯独这里没跟） | 改 `startswith("F-") or startswith("F ")`，或走 id 解析 |

> ✅ **已核实**：`grep` 实测 kdev 这四处仍是硬编码；`id_label_fragment` 已存在且被同仓其它模块正常使用，故修复=把同一模式补到这三个文件，低风险。

**验收**：补 TDD 用例——构造一条时间戳形 `## Q 20260625-...` / `## F 20260625-...`，断言 weekly 收录、distill_trigger 计数 +1、distill skill-feedback 切片含该条。预计 ~半天（含测试）。

---

## P1 — sync 层三件套（通用、低难度，独立于 JSONL）　✅ 已实施 2026-06-25（commit `6f4296f`）

> 落地细节：以 kdev 现有 `_git` 为底座叠加 ieidev 三件能力，保住了 kdev 已有的 GCM 三开关 + UTF-8 修复；`has_git` 无 remote 语义由 `pull` 改为 `remind`（对齐 ieidev，连带改 4 个既有用例）。

ieidev 0.4.0 → 0.5.0 把「记忆仓 git 同步」从「失败只打 stderr（用户看不见）」升级成一套自洽的引导体验。kdev 只完成了 0.18.3 的 GCM 非交互修复，下面三件未跟。来源对照 [`ieidev_sync.py`] vs [`kdev_sync.py`](plugins/kdev-memory/hooks/lib/kdev_sync.py) + [`kdev-sync-bootstrap.py`](plugins/kdev-memory/hooks/kdev-sync-bootstrap.py)。

| 特性 | ieidev 行为 | kdev 现状 | backport 难度 |
|------|-------------|-----------|---------------|
| **`init-local`** | 无 remote 但 `.kdev/` 非空 → SessionStart 自动 `git init` 建本地 nested 仓 + 首次 commit + 提醒建远程 | `decide_action()` 无此分支，无 remote 直接 `remind` | 低（加一条 `decide_action` 路径 + bootstrap 承接） |
| **`sync: off`** | `kdev-sync.yml` 项目级退出开关，入库后全队永久静默（`is_sync_off()` + `OPTOUT_HINT` 附在每条提醒末） | 无 | 低~中（需配 `kdev-sync.yml` schema 一个字段） |
| **失败会话内提示** | pull/clone/init 失败不报 stderr，改 `<kdev-sync-reminder>` XML 标签 + 中文引导（教 `gh auth login` 一次缓存凭据） | 失败 `print` 到 stderr，用户不可见 | 低（`sync_failed_reminder_text()` + bootstrap 上层改打印通道） |

> 💡 本会话 SessionStart 弹的 `<ieidev-sync-reminder>「检测到工程记忆尚未 git 托管…」`正是这套体验的产物——kdev 目前给不出等价的会话内引导。

---

## P1b — Windows hook 控制台闪窗 ＋ wrapper 加固（新增 2026-06-25，调查中）

> 起源：用户报"Windows 上 hook **一直启停闪控制台窗**"。0.18.3 CHANGELOG 只修了 GCM「Connect to GitHub」弹窗（GUI 凭据框，与闪窗**正交**），**没碰闪窗根因**（✅ 核实：`git diff d9be67e HEAD` 对 [run-python-hook.cmd](plugins/kdev-memory/hooks/run-python-hook.cmd) 和 [hooks.json](plugins/kdev-memory/hooks/hooks.json) 均空）。本节落账调查结论，避免丢失。

### 现象与场景判定（✅ 已核实控制台模型）

- **闪窗 = 每次 hook 触发弹一个 cmd.exe 控制台窗**，高频（PostToolUse 命中每次 Write/Edit/MultiEdit/NotebookEdit/Bash，SessionStart 连闪两下）。
- **精确命中 = Windows × GUI 宿主**（VSCode/JetBrains 原生扩展 / Claude Desktop）；**Windows × 终端 CLI 不闪**（hook 继承终端 console）。Linux/macOS 全程无关。
- 用户实际用户面（2026-06-25 确认）：**原生扩展（闪）＋ 终端 CLI（不闪）双队列共存** → 推出修法**红线：对终端 CLI 队列必须无害**（pythonw 改的是整个 Windows 分支，会触及这拨）。

### 根因：Claude Code 上游缺陷，非 kdev（✅ 机制独立推导 ＋ claude-code-guide 网查吻合）

- Claude Code 在 Windows GUI 宿主派生 command hook 时**没传 `CREATE_NO_WINDOW`（0x08000000）** → OS 给 cmd.exe 新分配 console 并显示。**不是 kdev bug**：任何带 command hook 的插件都中招，kdev 只是 6 类事件高频显眼。
- 官方**主动不修**：RFE「给 hook 加 windowsHide」被 closed as **not planned**；无任何隐藏窗口的 settings/env 配置。
- ⚠️ **可信度**：上游 issue 号系 claude-code-guide 网查所得（个别 URL 畸形，按 R-009 引用前须自核）；但"缺 CREATE_NO_WINDOW ＋ 无配置 ＋ RFE not-planned"的**定性**与从控制台模型独立推导的机制**一致**，高可信。
- ⚠️ **pythonw 可能白费**：v2.1.143 起 Claude Code 派生 claude.exe 子进程做沙箱再跑 hook。若那个缺 flag 的窗口是 **claude.exe 沙箱子进程**的（在我们 cmd.exe 之上一层），插件侧换 pythonw/wscript 也消不掉它。窗口归谁随 Claude Code 版本而变（老版本 spawn cmd.exe→窗口是 cmd.exe 的、或许能动；新版本沙箱 fork→窗口是 claude.exe 的、无解），**从 Linux 无法判定**。

### ✅ 可立刻做 ＋ 普惠双队列：wrapper 加固 backport（ieidev 0.5.0 领先，kdev 0.18.3 该跟）

**契合本 roadmap「ieidev 领先、kdev 该跟」主题，是 4 路 diff 漏掉的一项。** kdev 的 [run-python-hook.cmd](plugins/kdev-memory/hooks/run-python-hook.cmd) 是**纯 LF 且无 .gitattributes**（✅ `file` 实测）；ieidev 同名文件 CRLF ＋ `.gitattributes` 锁 ＋ 更硬：

| 加固项 | ieidev 0.5.0 | kdev 0.18.3 | 影响 | 难度 |
|--------|-------------|-------------|------|------|
| 行尾 CRLF ＋ `.gitattributes` 锁 `hooks/run-python-hook.cmd text eol=crlf` | ✅ | ❌ 纯 LF，无 .gitattributes | 🔴 LF→cmd.exe 忽略 `@echo off`→窗里/终端里刷命令文本（GUI 闪得脏、CLI 终端有噪声） | 低 |
| cmd 块 ASCII-only（中文只放 bash 行）| ✅ | ⚠️ 注释英文但无强约束 | GBK 控制台中文乱码 | 低 |
| `PYTHONUTF8=1` | ✅ 双分支 set | ❌ 无 | GBK 下中文/emoji 输出更稳 | 极小 |
| Unix 分支单行 ＋ 尾 `#` 吃 `\r` | ✅ | ❌ 多行（CRLF 化后 `\r` 会弄坏路径/关键字） | **与 CRLF 改动绑定**：若锁 CRLF 必须同改 | 低 |
| `exec` 单次执行 ＋ `--version` 探测跳 Win Store python3 死垫片 | ✅ | ❌ `python3 \|\| python` | 避免 Store stub 假成功 | 低 |

> **绑定关系**：一旦把 .cmd 锁成 CRLF，Unix/bash 分支**必须**同步改成 ieidev 那种「单行 ＋ 尾 `#`」写法，否则 CRLF 的 `\r` 会弄坏 bash 分支——两件事不可拆。
> **价值独立于"窗口能否消"**：加固让闪窗从「刷一屏命令」降到「干净一闪」、消终端 CLI 噪声、修 LF 潜在跨平台 bug、对齐 ieidev。**即使窗口最终消不掉也值得做。**

### ❌ 不可借鉴：autoserve 的 DETACHED 手法

ieidev 的 `autoserve.py`（`pyieidev/ieidev_hud/`，`_spawn_serve()` 行 188-191）会用 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` 无窗起后台 HUD 服务——但它 `stdin/stdout/stderr` 全 DEVNULL，是发射后不管。**hook 必须回传 stdout ＋ exit code 给 Claude Code，照搬会断回传。** 只能当"团队会用 creationflags"的存在证明，非现成解。

### 决策点（拍板前别动手）

1. **Tier-1 wrapper 加固**：建议**直接做**（独立成立、零风险、双队列普惠）。产物：改 [run-python-hook.cmd](plugins/kdev-memory/hooks/run-python-hook.cmd)（CRLF ＋ ASCII cmd ＋ PYTHONUTF8 ＋ 单行 exec bash）＋ 新增 `.gitattributes` 锁 CRLF ＋ TDD（保两分支仍能选对解释器）。
2. **窗口本身走实验闸**：在 Windows 扩展环境把某 hook 临时换成 trivial `pythonw` 脚本——**还闪 = 窗口是 claude.exe 的（plugin 无解，转文档化）；不闪 = 窗口是 cmd.exe 的（pythonw 有救，再正式投）**。10 分钟换确定性，避免盲投。
3. **文档化兜底**（若实验证明 plugin 无解）：README/CHANGELOG 标明「Windows GUI 宿主闪窗 = Claude Code 上游已知缺陷（非本插件），官方 not-planned，受影响用户可去上游 issue +1 或改终端 CLI」。

**落地顺序**：Tier-1 随 P1 一批做（同属低风险 ieidev-backport）；窗口实验需用户 Windows 机器配合，结果回写本节。

---

## P2 — JSONL 叙事主账（Plan D Phase 2）【需决策】

**这是 ieidev 领先 kdev 的最大一块，也是后续一长串下游 diff 的总根。** ieidev 0.3.0（2026-06-23）落地，kdev 有设计稿 [`docs/superpowers/specs/2026-06-13-P-C2-JSONL操作层+token优化-design.md`](docs/superpowers/specs/2026-06-13-P-C2-JSONL操作层+token优化-design.md) 但**截至 0.18.3 未实施**，仍是 markdown 单一主存。对应记忆决策 **Q 20260617-182852「员工记忆层 JSONL 主账化（md 退日总结派生）」**。

### 架构差（一句话）

> 把**叙事 Step** 的物理主账从 LLM 可读的 `执行日志.md` 升级到机器可查询的 `执行日志.jsonl`（append-only + schema 验证），旧 md 冻结为 `执行日志.archive.md`；决策/踩坑/F/R 仍 markdown 主存。在此之上把「靠 LLM 自律翻 md 拼日总结」换成「确定性脚本强制聚合」。

### 组件清单（ieidev 已有，kdev 全缺）

| 模块 | 作用 | 通用 vs team | 难度 |
|------|------|--------------|------|
| `step_log.py` | JSONL 唯一读写口：`append_step()`（O_APPEND 原子写）/ `read_steps()` / `steps_for_date()` / `validate()`（内含 7 hard-gate 确定性子集） | **通用核心** | 中 |
| `migrate_jsonl.py` | 一次性 `执行日志.md`→`.jsonl` 迁移，幂等，原 md 冻结为 `.archive.md`，保留 `_migrated_raw` 兜底零丢失 | 通用 | 小 |
| `daily_render.py` | **承重墙**：从 jsonl 确定性渲染每日汇总 5 段（完成/未完成/明日计划/当日新增 Q-G-R/负面评价观察），LLM 润色降为可选叠加层 | **通用** | 小（依赖 step_log 先落地） |
| `scope.py` 加 `recorder_target_jsonl()` | jsonl 路径解析（flat/scoped 路由），与现有 `recorder_target_log` 同拓扑 | 通用 | 极小（~5 行） |

### 下游 reader 切换（同一批次，14+ 文件）

step-recorder agent 改 JSONL 落盘（[kdev-step-recorder.md](plugins/kdev-memory/agents/kdev-step-recorder.md) 从 heredoc append md 改调 `step_log.append_step()`）；以及全部从读 md 改读 jsonl 的 reader：`stop-check` / `pre-compact-check` / `session-end-check` / `session-start-brief`（今日 Step 精确计数，现状用 `## Step ` 正则扫 md「含历史」不准）/ `missing_summaries` / `distill` / `distill_trigger` / `weekly` / `promote-list` / `step_completeness`（`_record_issues` + `_PLACEHOLDER_DED` + voided 跳过）/ `trigger-match` / `archive_hint`（执行日志月度切档 gate off，jsonl append-only 无需 rotation）。

### 文档层同步（SKILL + 6 references）

[SKILL.md](plugins/kdev-memory/skills/kdev-memory/SKILL.md)（每日汇总动作路径改「先跑 daily_render 脚本」+ 架构段标注 JSONL 主账）、`references/六类记录-schema.md`（§3 加 Phase 2 迁移声明「不要再手写 `## Step` 进 md」）、`切档与归档.md`（执行日志切档下线）、`markdown-切片导出.md`（导出层 vs 存储层解耦框注）、`自动化机制-hooks.md`（trigger-match 改读 jsonl）。

### 决策点（拍板前别动手）

1. **独立 kdev-memory 是否需要 JSONL？** 收益：日总结确定性化（消 LLM 漏步/错读）、checkpoint token 大降、结构化可查询；成本：14+ 文件接触面、存量 md 迁移、需处理 P-C2 spec 里 **G-011（worktree 下 Step-ID 前缀按 cwd 现算 + `.kdev` symlink 共享 store → 同会话两套不连号 ID 轨）** 这个 open 隐患。
2. **若迁，分阶段**：Phase A 落 `step_log.py` + `migrate_jsonl.py` + `scope.recorder_target_jsonl` + 双读兼容（reader 同时认 md/jsonl）；Phase B 切 step-recorder 落盘 + `daily_render.py`；Phase C reader 退 md + 文档同步 + 切档下线。
3. **若暂不迁**：至少在 [SKILL.md](plugins/kdev-memory/skills/kdev-memory/SKILL.md) 和 P-C2 spec 显式标注「kdev-memory 仍 markdown 单一主账，JSONL 迁移 defer」，避免文档/spec 与代码漂移（呼应项目 R-009 + spec→canonical 回写铁规）。

---

## P2 配套 — PreCompact checkpoint 瘦身（D4，token 经济）

ieidev 把 [pre-compact-check.py](plugins/kdev-memory/hooks/pre-compact-check.py) 的 checkpoint 从「全文复制 durable md（执行/决策/踩坑/改进）」改为**指针模式**——durable 文件压缩后磁盘仍在、有召回通道、有 git 历史，三重冗余无需抄；checkpoint 只留**易失叙事信号**（未落盘 Step 警告，措辞强化为「易失信号·压缩后优先补记」）。

- **指针格式部分**：独立于 JSONL，可单独 backport（kdev 现状仍全文拷贝多个 md，checkpoint 偏大）。难度低。
- **「今日 Step 数」判断部分**：依赖 `step_log.steps_for_date()`，跟 P2 JSONL 一起走。

---

## 5. 不跟清单（team 编排耦合，独立插件无意义）

| 项 | 为何不跟 |
|----|----------|
| `delegation.py` | CEO recorder 从 `events.jsonl`+`handoffs/` 派生员工委派工作——纯 ieidev 多员工流水线产物 |
| `recall.py` 的 `recall_events()`/`recall_handoffs()` | 依赖 `.ieidev/features/<slug>/events.jsonl`、`handoffs/*.json`，单项目无此结构。**注**：其中 `recall_pointers()`（triggers 字面匹配返指针）与 kdev `trigger-match.py` 同构，若想给「派单前主动查询 CLI」可选择性瘦身 backport，但非必需 |
| `block-advance-past-gate.py` | PreToolUse 拦截 `kdev_core advance/dispatch-start` 越过未确认 human_gate——flow 编排硬停，完全耦合引擎 gate 接口 |
| `cqo-event-audit.py` | CQO 逐事件规则全检落 WARN——CQO 监督层，针对 ieidev_core 事件流 |
| `claude_md_merge.py` shim 化 | ieidev 把逻辑上移进 `ieidev_core.memory_scaffold`（引擎层）只留 42 行 re-export；kdev 无对应引擎层，[claude_md_merge.py](plugins/kdev-memory/hooks/lib/claude_md_merge.py) 自包含实现反而是逻辑真相源，**保持现状** |
| `migrate_scope.py` `DEFAULT_STAFF` | ieidev 收窄为 `["reviewer","cqo"]`（Q-019），kdev 仍 `["dev-engineer","req-architect"]`（已标 STALE）。但 staff 列表本就是 **kdev-team 的员工概念**，独立 kdev-memory 不该硬塞——**若 kdev-memory 配合 kdev-team scoped 布局使用**再按 kdev-team 实际员工对齐，否则维持 STALE 注释即可。低优先 |

---

## 6. kdev 反而领先 ieidev（别回退；可反向 forward-port 给 ieidev）

> ✅ 本节已逐条核实 ieidev 源码。**两条 subagent 误报已剔除**：`brief.verbosity` 三档 ieidev **也有**（session-start-brief.py 行 295/345/463 与 kdev 一致）；marker 前缀 ieidev lint 与模板**自洽**都用 `ieidev-team:`（之前报的 `kdev-team:` 是归一化 sed 的产物，非真差异）。真·领先项只剩一条：

| 项 | kdev 状态 | ieidev 状态（缺口已核实） |
|----|-----------|---------------------------|
| **Windows UTF-8 subprocess 修复** | [step_id.py:30](plugins/kdev-memory/hooks/lib/step_id.py#L30) `_git_query` + [kdev_sync.py:100](plugins/kdev-memory/hooks/lib/kdev_sync.py#L100) `_git` 的 `subprocess.run` 加 `encoding="utf-8", errors="replace"`（0.18.2，中文 Windows git 输出不崩） | `step_id.py:28-29`（`_git_query`）+ `ieidev_sync.py:139-140`（`_git`）的 `subprocess.run` 均无 `encoding/errors` → 中文 Windows 上 `_readerthread` GBK 解码崩溃。应反向回流给 ieidev |

> ⚠️ **预存隐患（与对比无关，记录待办）**：[test_step_id.py](plugins/kdev-memory/tests/test_step_id.py) 的 `test_dup_index_concurrent_no_collision` / `test_increment_concurrent_no_collision` 在本机间歇失败——20 线程并发只拿 11 个结果，`_dup_index`/`increment_counter` 文件锁竞争。建议另开任务诊断，与本 roadmap 正交但会影响 P2 JSONL 并发写正确性。

---

## 附录：建议落地顺序

1. **本周**：P0 时间戳双认（4 处 + TDD），bump patch 版。
2. **下一迭代**：P1 sync 三件套 + **P1b wrapper 加固（CRLF/.gitattributes/PYTHONUTF8/单行 exec backport）** + P2 配套的 checkpoint 指针格式（都独立于 JSONL，先收割低风险收益）；并行让用户在 Windows 跑 P1b 闪窗归属实验（pythonw 是否有救）。
3. **专题决策会**：拍 P2 JSONL 是否迁、怎么分阶段，连带处理 G-011 worktree ID 隐患；决策结果回写 [P-C2 spec](docs/superpowers/specs/2026-06-13-P-C2-JSONL操作层+token优化-design.md) 与 SKILL.md（spec→canonical 回写铁规）。

---

*对比证据链：本文每条 ieidev 领先点均来自 4 路并行只读 diff（归一化命名后），P0 四处漏点已逐一 `grep` 核实 kdev 源码行号。如需复核单条，对照表中文件链接即可。*
