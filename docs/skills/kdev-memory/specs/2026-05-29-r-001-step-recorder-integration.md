---
title: R-001 kdev-step-recorder 集成进 kdev-memory 主路径（v1.0）
date: 2026-05-29
status: draft（等用户 review）
related:
  - R-001 (改进建议.md) — 跨轮次长会话 Step 落盘 under-reporting
  - R-005 candidate (改进建议.md) — 长会话与 skill 升级 staleness
  - Q-003 (决策日志.md) — Step ID 加分支前缀（已实施，v0.11.0）
  - User 补充 #1 — SKILL.md § 下游 共标题 拆分（规则升级独立）
target_version: kdev-memory v0.12.0
brainstorming_session: 2026-05-29
---

# R-001 kdev-step-recorder 集成进 kdev-memory 主路径 — 设计 spec v1.0

## 背景

### R-001 原始痛点

5/27 main session 实测 **75% under-reporting**：用户做完一批 step-worthy 单元，主会话遗忘落 step，跨日汇报才发现。详见 [.kdev/memory/改进建议.md#R-001](.kdev/memory/改进建议.md)。

### Prototype 阶段已达 + 缺口

2026-05-28 完成 kdev-step-recorder v0.2 prototype（[plugins/kdev-memory/agents/kdev-step-recorder.md](plugins/kdev-memory/agents/kdev-step-recorder.md)，commit 07872d7）：
- ✅ Subagent 模板含 8 hard-gate 反偷懒校验 + 4 段 Step 输出 schema
- ✅ 3 轮 dogfood 验证机制走通（main-11 / main-15）
- ❌ **SKILL.md 没提**，**CLAUDE.md 没提**，**没 hook 触发** → 新会话不知道这个机制存在
- ❌ 这把扳手放在抽屉里没说明书

**今天会话本身就是证据**：主会话作为 step-worthy 单元高产源（Q-003 落地 + R-002 修 + R-003 修 + skill-creator eval + R-001 prototype），主动 dispatch 次数 = 0。落 step main-11 / main-15 都是被"测试 prototype"的名义被动触发的。**机制层面 0 进展**。

### R-005 候选（顺手）

Dogfood round-2 现场发现：另一并发会话不感知本会话升级了 SKILL.md，继续用旧路径手工 edit current_step + # 注释。Claude Code skill 是 SessionStart 时一次性快照加载，会话运行中升级不感知。详见 [改进建议.md#R-005](.kdev/memory/改进建议.md)。

### 用户补充 #1

SKILL.md 现状的 `## 下游：记录如何变成蒸馏原料 + 新 skill`（line 321）把两件事并入同一 section 标题：(a) R-NNN → 升铁规/宪章/ADR，(b) markdown 切片包蒸馏。用户希望拆分——规则升级独立成 §，蒸馏独立成 §。

## Goals

1. **新会话 / 重启会话** 启动后立刻知道"该用 dispatch + step-recorder"
2. **主会话遗忘** 时由 hook 软提醒兜底（70-80% 痛点封堵，接受偶发漏仔以保流畅）
3. **subagent-driven 高频 batch**（Q-003 那种 13 task）期间不被阈值提醒打断
4. **长会话感知 skill 升级**（R-005 顺手）
5. **§ 下游 拆分**（#1 顺手）让规则升级 first-class

## Non-Goals（v1 范围外）

1. **`.kdev/` 多机/多人 sync 策略**（用户补充 #2 + #3）—— 独立 brainstorm 轮，本 spec 不动
2. **framework design 无 commit 场景** —— 接受 `# main-N: ...` 注释行作为 escape hatch，v2 正规化
3. **YAML schema hard-gate 1（title generic）的更强判定**（如要求含 commit message 第一行）—— 留 v0.3 hardening
4. **R-001 100% 封堵**（接受 20-30% 漏仔率换主会话流畅）
5. **历史 backfill 工具**（如已 14 半残 Step 自动补齐）—— hook 上线后自然消化，不专门做工具

## Design

### Section 1：Architecture overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    主会话（Claude Code session）                  │
│                                                                  │
│  完成 step-worthy 单元 ──────dispatch──────▶                     │
│  写 ~30 行 YAML summary                                          │
│  Agent({subagent, model: sonnet, prompt: YAML + ref SKILL.md})  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
        ┌─────────────────────────────────────────┐
        │   kdev-step-recorder subagent (v0.2)    │
        │   - 验 8 hard-gates                      │
        │   - mint_next_step_id (lib)              │
        │   - 写 4 段 Step 条目（heredoc append）   │
        │   - 更新 当前状态.md frontmatter         │
        │   - 清空 pending-commits.json            │
        └─────────────────────────────────────────┘

[背后双轨：commit hook + Stop hook + SessionStart hook]

  git commit          ┌──────────────────────────────────┐
  PostToolUse hook ──▶│ commit-tracker (新)               │
                      │ - 读 commit message               │
                      │ - 若匹配 `task N/M` → suppress    │
                      │ - 否则 append commit info →       │
                      │   .kdev/memory/state/             │
                      │   pending-commits.json            │
                      └────────────┬─────────────────────┘
                                   ▼
  Stop hook ────read─▶ pending-commits.json
                      若 count ≥ 3 OR 最早 commit > 30min
                      → 软提醒 "⚠️ N commit 未落 step"

  SessionStart ───────▶ brief 注入 pending-commits 状态
                       + SKILL.md SHA check (R-005)
```

**双轨互补**：
- **主轨（dispatch）**：fire-and-forget，主会话 0 IO 成本
- **副轨（hook）**：主会话遗忘时由 hook 信号兜底

### Section 2：Components & Files Map

| Action | File | Purpose | LOC est. |
|---|---|---|---|
| 🆕 NEW | `plugins/kdev-memory/hooks/commit-tracker.py` | PostToolUse hook on Bash—detect git commit + 维护 pending-commits.json | ~80 |
| 🆕 NEW | `plugins/kdev-memory/hooks/lib/pending_commits.py` | CRUD for pending-commits.json + age / suppress 检测 | ~60 |
| 🆕 NEW | `plugins/kdev-memory/hooks/lib/skill_version.py` | R-005 SKILL.md SHA cache + drift check | ~50 |
| 🆕 NEW | `plugins/kdev-memory/tests/test_commit_tracker.py` | TDD: git commit detection + suppress + threshold | ~120 |
| 🆕 NEW | `plugins/kdev-memory/tests/test_pending_commits.py` | TDD: pending-commits CRUD + age + suppress | ~80 |
| 🆕 NEW | `plugins/kdev-memory/tests/test_skill_version.py` | TDD: SHA cache + drift detection | ~60 |
| 🆕 NEW | `plugins/kdev-memory/tests/test_step_recorder_e2e.py` | e2e dogfood: dispatch + verify step + cleared pending | ~80 |
| ✏️ MOD | `plugins/kdev-memory/hooks/hooks.json` | 注册 PostToolUse hook | +5 |
| ✏️ MOD | `plugins/kdev-memory/hooks/stop-check.py` | 加 pending-commits threshold check 注入 | +20 |
| ✏️ MOD | `plugins/kdev-memory/hooks/session-start-brief.py` | brief 注入 pending-commits + R-005 SHA hint | +25 |
| ✏️ MOD | `plugins/kdev-memory/skills/kdev-memory/SKILL.md` | inline ~30 行 step-recorder dispatch 契约 + §下游 拆分 | +60 / -20 |
| ✏️ MOD | `plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md` | 同步第 1 条铁规改写 | +5 |
| ✏️ MOD | `CLAUDE.md`（项目根） | 第 1 条铁规重写"实时 dispatch step-recorder 落盘" | ~10 |
| ✏️ MOD | `plugins/kdev-memory/agents/kdev-step-recorder.md` | YAML schema 加 `commits_batch_id` 选填字段 | +5 |
| ✏️ MOD | `plugins/kdev-memory/CHANGELOG.md` | bump v0.12.0 | +60 |

**总估**：7 个新文件 + 8 个修改 ≈ ~750 行（含测试）。

### Section 3：Hook 实现细节

#### commit-tracker.py（PostToolUse on Bash）

```python
def main():
    data = json.loads(sys.stdin.read())
    cmd = data.get("toolInput", {}).get("command", "")
    if not is_git_commit(cmd):
        return SUPPRESS  # 不是 git commit 就退出

    sha = git_log_latest_sha()
    msg = git_log_latest_message()

    # suppress 判定：commit message 含 `task N/M` 模式
    if re.search(r"\(.*?task\s+\d+/\d+.*?\)", msg, re.IGNORECASE):
        return SUPPRESS  # subagent-driven batch 高频 mode，不计入

    pending_commits.append(sha, msg.split('\n')[0], int(time.time()))
    return SUPPRESS  # hook 输出不污染主会话
```

#### pending_commits.json schema

```json
{
  "since_step_id": "main-15",
  "since_ts": 1716902400,
  "commits": [
    {
      "sha": "abc1234",
      "subject": "fix(kdev-memory): X",
      "ts": 1716903456
    }
  ]
}
```

字段语义：
- `since_step_id`: 最近一次落盘 step 的 ID
- `since_ts`: 从那个 step 开始计时的 epoch
- `commits`: 从那时起累积的 non-suppressed commits

#### stop-check.py 增量

```python
pc = read_pending_commits()
if len(pc.commits) >= 3 or (pc.commits and now - pc.commits[0].ts > 30*60):
    inject_warning(f"⚠️ {len(pc.commits)} commit 未落 step（最早 {age_str}）— "
                   f"完成单元后请 dispatch kdev-step-recorder。")
```

#### session-start-brief.py 增量

```python
# brief startup 段追加：
pc = read_pending_commits()
if pc.commits:
    prog.append(f"- 🔔 pending step-recorder dispatch: {len(pc.commits)} commit 累积"
                f"（最早 {age_str}，最近 {recent_sha}）")

# R-005 SHA drift check
current_sha = git_log_latest_sha("plugins/kdev-memory/skills/kdev-memory/SKILL.md")
cached_sha = skill_version.read_cache(session_id)
if cached_sha and cached_sha != current_sha:
    prog.append(f"- ⚠️ SKILL.md 在你会话启动后被升级（cached={cached_sha[:7]} → current={current_sha[:7]}）— "
                f"建议 /clear restart 加载新 skill")
skill_version.write_cache(session_id, current_sha)
```

#### step-recorder 完工清空 pending-commits

`agents/kdev-step-recorder.md` 已有 action step 5 清空逻辑。v1 明确：清空时把 `since_step_id` 更新为刚 mint 的 ID，`commits: []`。

### Section 4：YAML schema v0.3（只加 1 字段）

```yaml
# 既有 v0.2 字段不动（title / about / commit_shas / files_touched /
# key_decisions / key_facts / self_eval_score / self_eval_deduction /
# triggers / references）

# v0.3 新增（optional）
commits_batch_id: <str | null>   # subagent-driven batch 时设为 Q-NNN 或 plan slug
```

`commits_batch_id` 不加 gate（元数据非必填）。用途：将来从 step 反查 plan / Q-NNN。

### Section 5：SKILL.md inline 段（~30 行）

插入位置：现有 `## §多 worktree 并发场景：Step ID 加分支前缀（v0.11+）` 段（line 351-409）之后，作为下一个 `##` 章节。

```markdown
## §用 kdev-step-recorder dispatch 落 step（v0.12+）

### 何时 dispatch

每完成一个 step-worthy 工作单元（任务 / 决策 / 踩坑 / 用户评分），**主会话不要自己写 Step**——
dispatch [kdev-step-recorder](../../agents/kdev-step-recorder.md) subagent 负责。

判据（满足任一即 step-worthy）：
- 至少 1 个 commit + 完成了一个独立工作单元
- 或：一个 Q-NNN 决策推到拍板态
- 或：一个 G-NNN 踩坑被发现 / 解决
- 或：用户对一个工作单元给评分

**hook 兜底**：若主会话遗忘，commit hook 会累积 pending-commits.json；SessionStart / Stop brief 会显示
`🔔 pending step-recorder dispatch: N commit 累积`——看到提醒立刻 dispatch。

### Dispatch 标准格式

\```python
Agent({
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Record Step <slug>-<N>",
  prompt: """
You are kdev-step-recorder. Read plugins/kdev-memory/agents/kdev-step-recorder.md
for role + 8 hard-gates + action sequence. Work from <repo root>.

## Input (YAML)
\```yaml
title: <concrete verb + concrete object>
about: project | feature/<name> | bugfix/<name>
commit_shas: [...]
files_touched: [...]
key_decisions: [...]
key_facts:
  tools_invoked_count: <int>
  errors_hit: <int>
  detours: <int>
  token_feel: light | medium | heavy
self_eval_score: 1-5
self_eval_deduction: <substantive — empty REJECTED>
triggers: [...]   # ≥ 5
references: [...]
commits_batch_id: <Q-NNN or null>
\```
"""
})
\```

完整 schema、8 hard-gate 规则、反例对照、action sequence 详见
[agents/kdev-step-recorder.md](../../agents/kdev-step-recorder.md)。

### 为什么 dispatch 而不是主会话自己写

主会话被任务流吸住、自然停顿点被预期下一棒吞没——遗忘是常态（R-001 痛点：5/27 实测 75% under-reporting）。
dispatch fire-and-forget = 主会话只付出 ~30 行 YAML 写作 + 立即继续，subagent 干 Read/算/Write/Edit。
比"自己 Read 执行日志 + mint + Write 4 段 + Edit 当前状态" 轻 5-10x。
```

### Section 6：项目根 CLAUDE.md 第 1 条铁规改写

**当前**：

```
🔴 **实时落盘**：每做完一个有边界的步骤（任务 / 决策 / 踩坑 / 用户评分）→ **立刻**追加到 `.kdev/memory/` 对应文件。
不要攒到会话末尾或"总结一下"时才补录——回忆会失真，评分会褪色。
**不需要征求用户许可**即可写入 `.kdev/memory/` 下的任何文件。
```

**改成**：

```
🔴 **实时 dispatch step-recorder 落盘**：每做完一个 step-worthy 工作单元（任务 / 决策 / 踩坑 / 用户评分）→
主会话**不要自己 Read/Write 执行日志**，而是写一段 YAML summary（schema 见 SKILL.md §用 kdev-step-recorder
dispatch 落 step）+ dispatch kdev-step-recorder subagent（sonnet）。subagent 验 8 hard-gate + 写 4 段 Step
条目 + 更新 当前状态.md frontmatter + 清空 pending-commits.json。

dispatch 是 fire-and-forget——主会话写完 YAML、调用 Agent 后立刻继续下一棒工作，不等 subagent 返回。
**Q/G/R/F-NNN 决策类条目仍由主会话直接写**（Read + Edit 决策日志.md / 踩坑日志.md / 改进建议.md /
skill-feedback.md）——只有 Step 走 dispatch。

**不需要征求用户许可**即可 dispatch + 让 subagent 写入 `.kdev/memory/`。
```

### Section 7：Testing strategy

| 测试目标 | 文件 | 用例数 | 关键断言 |
|---|---|---|---|
| commit-tracker 检测 git commit | `test_commit_tracker.py` | 4 | 普通 git commit → append；非 git command → skip；`task N/M` → suppress；`Q-XXX task` → suppress |
| pending-commits CRUD + age | `test_pending_commits.py` | 4 | empty → no-op；append 累积；clear after step；age 算 epoch 差 |
| skill_version SHA drift | `test_skill_version.py` | 3 | 首次 cache write；SHA 不变 → 静默；SHA 变 → 返回 drift signal |
| stop-check brief inject | extend `test_step_completeness.py` 或新 file | 2 | pending ≥ 3 → warning string；pending = 0 → silent |
| session-start-brief 集成 | extend `test_session_start_brief_prefix.py` | 2 | pending-commits 非空 → brief 含 🔔；SKILL.md SHA drift → brief 含 ⚠️ |
| e2e dogfood | `test_step_recorder_e2e.py`（新） | 1 | dispatch + verify step main-N 落盘 + counter 推 + pending cleared |

**总测试数**：~16 unit + 1 e2e。覆盖率目标：新 lib 函数 100% + hook flow 主路径 + 1 个 happy-path e2e。

### Section 8：SKILL.md § 下游 拆分（#1 顺手）

**当前状态**（line 321）：

```
## 下游：记录如何变成蒸馏原料 + 新 skill
- R-NNN：项目内方法论反思 → 升铁规 / 升宪章 / 立 ADR
- markdown 切片包 → 知识蒸馏 / skill 自主优化（通过 /kdev-memory-distill ...）
```

**v1 改成两个独立 §**：

第一个：**升级规则升级流程 §（line 191 原有）**——把 R-NNN → 升铁规 那段并入：

```
## 规则升级流程

改进建议 / 方法论铁规积累到一定程度可升级为项目级硬规则。升级不自动执行。
（既有内容不动）

### 原料来源（v0.12+ 显式标注）

R-NNN（项目内方法论反思）→ 累积 ≥ 2 次同主题 或 用户明确"升铁规" → 走升级流程
（必问三件事见 `references/规则升级流程.md`）→ 落到 方法论铁规.md / 项目宪章 / ADR

见 `references/规则升级流程.md` 完整流程。
```

第二个：**蒸馏 §（line 321 重命名 + 限定）**：

```
## 下游：知识蒸馏（markdown 切片包）

通过 `/kdev-memory-distill` 命令按蒸馏目标 filter + sanitize 原 markdown 条目，
产出三个独立 markdown 切片包：
- `dataset-full/` — 全量记录（含 Step / G / Q / R / F），适合通用蒸馏
- `dataset-misalignment/` — 评分差值 ≥ 2 的样本，适合 RLHF
- `dataset-skill-feedback-by-subject/` — F-NNN 按 subject 路由

**架构决策**：markdown 主存 + markdown 切片包导出，不引入 JSONL——
现代蒸馏管道直接吃 markdown，多一层中间格式徒增维护、丢失叙事。

完整阈值检测、自动触发、Popen detach 流程见 `references/蒸馏触发机制.md`。
```

## Migration / Rollout

- **不需要数据迁移**：现有 14 半残 Step / 4 pending 沉淀候选 不影响新机制；新机制上线后逐步消化（pending-commits 从 0 计起）
- **不需要用户行动**：除了**重启所有运行中的 Claude Code 会话**让新 SKILL.md / CLAUDE.md 生效（R-005 hint 会提示）
- **不需要 `.gitignore` 改动**：`.kdev/memory/state/pending-commits.json` 跟现有 state/ 共生共死
- **CHANGELOG bump**：v0.11.0 → v0.12.0；语义版本 minor bump（添加 feature 向后兼容）

## Risks

| 风险 | 概率 | 后果 | 缓解 |
|---|---|---|---|
| 主会话仍遗忘 dispatch（即便 hook 提醒在） | 高 | R-001 痛点封堵率 < 70% | CLAUDE.md 铁规重写 + SKILL.md inline + hook 提醒三重叠加；接受 20-30% 漏仔率 |
| commit hook 误判 `task N/M` 模式（如手动 commit msg 含此字面） | 低 | 漏一两条 commit 不计入 pending | regex 加 `(...task X/Y...)` 圆括号限定 vs 裸字面；测试覆盖 |
| Stop hook 阈值噪声（主会话每次结束都看到 ⚠️） | 中 | 用户疲劳 / 忽略提醒 | 阈值保守（≥3 OR >30min）+ 用户可改 config.yaml |
| pending-commits.json 状态损坏 | 低 | hook 报错 / brief 出问题 | pending_commits.py 加 try/except + fallback to empty |
| R-005 SHA cache 漏写 / 多 session 同名干扰 | 中 | drift 检测假阴 / 假阳 | cache 用 session_id key + filesystem mtime fallback |
| 14 半残 Step 持续作为 brief 噪声 | 低-中 | brief 显示长，用户疲劳 | brief 已有 lookback 限制 + 用户可手动销账标 voided-faded |

## 已识别 limitations（已知不解决）

1. **多并发会话**：本 spec 只解决"主会话漏 dispatch"，不解决"多并发会话各自漏 dispatch 互相不知道"——sync 策略问题，留 #2+#3 brainstorm 轮
2. **framework design 纯讨论场景**：v1 不强制 dispatch，接受 `# main-N: ...` 注释行 escape hatch；v2 再正规化
3. **YAML schema hard-gate 1（title generic）主观判定**：v1 保持 v0.2 现状，未引入更强结构化判据（如要求含 commit message 第一行）；留 v0.3
4. **历史 14 半残 Step 不主动补齐**：等用户/新机制自然消化
5. **commit-tracker 不识别 git amend / git rebase**：只支持新建 commit；amend 在 PostToolUse 也触发但累计可能不准
6. **Subagent token 成本**：每次 dispatch ~2-5k token；高频场景累计可观，但 fire-and-forget 不阻塞主会话流畅度

## Open questions / Backlog

| 编号 | 项目 | 状态 |
|---|---|---|
| #2 + #3 | `.kdev/` 多机/多人 sync 策略 | 独立 brainstorm 轮；触发词：用户提到"另一台机器拿不到记忆"/"同事改记忆冲突" |
| v0.3 | hard-gate 1（title generic）更强结构化判定 | 等 v1 上线后看实际漂移频率决定 |
| v2 | framework design 纯讨论场景的 lightweight 替代 | 等用户/那个并发会话场景累积更多样本 |
| 长期 | 跨 plan 反向溯源（commits_batch_id → Q-NNN → plan.md） | 蒸馏管道可消费，但工具化需求未定 |

## 接下来的步骤

1. **本 spec 用户 review** → 修订或批准
2. **批准后调 `superpowers:writing-plans`** → 出 task-by-task 实施 plan（保守估 12-15 task，参考 Q-003 plan 结构）
3. **plan 用户 review** → 修订或批准
4. **批准后调 `superpowers:subagent-driven-development`** → 按 Q-003 同样 sonnet implementer + opus spec reviewer + code quality reviewer 三段流水线执行
5. **完成后** → 升 kdev-memory v0.12.0 + 重启所有运行会话拿新 skill
