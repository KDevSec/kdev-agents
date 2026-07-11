# brief 三字段统一长度闸 — 设计

- **日期**：2026-07-10
- **状态**：待评审（design，brainstorming 产出）
- **类型**：kdev-memory 插件 bug-fix / 加固
- **根因来源**：[kdev-memory 上下文消耗诊断-2026-07-10](../../skills/kdev-memory/dev-notes/kdev-memory上下文消耗诊断-2026-07-10.md)（§7 源码复核勘误）
- **关联铁规**：R-009（spec→canonical 回写）、G-004（改 hook/agent 须 bump plugin version）

---

## 1. 背景与动机

诊断报告实测：SessionStart brief 把 `当前状态.md` frontmatter 的 `current_step` / `pending_decisions` / `unresolved_gotchas` 三字段 **verbatim 原样注入**，无截断 / 摘要 / 上限（`session-start-brief.py:483-489` 走 normal 档、`:447-448` 走 compact 档）。目标项目 `current_step` 膨胀到 100,151 字符 ≈ 25–33k token，占开局上下文 40–54%，且**无界增长**——里程碑越攒越多，每会话固定开销线性上涨。

**源码复核关键修正**：三字段**没有 Python 写入路径**，全由 step-recorder subagent / 主会话用 Edit 手写进 md。因此：

- 写入侧**没有确定性代码拦截点**（推翻 dev-note §7.4-2「写入侧闸位前移更根治」的判断——见 §9 回写清单）。
- **注入侧长度闸是唯一能在代码里确定生效的拦截点**。

## 2. 目标 / 非目标

**目标**：

1. 每会话开局这三字段的固定 token 成本被**确定性钳死**（不管字段在盘上多大）。
2. 字段膨胀对用户**可见**（催归档），而非静默恶化。
3. 健康项目**零行为变化**。

**非目标**：

- 不改 frontmatter 存储结构 / 不迁移字段。
- 不强制程序化改写用户手写的 frontmatter（无写入拦截点，不做）。
- 不引入 `yaml` 依赖（memory_config 仍 stdlib line-parser）。

## 3. 设计决策（brainstorming 拍定，2026-07-10）

| 决策 | 选定 | 理由 |
|---|---|---|
| scope | 三层：注入闸 + 写入 WARN + recorder 文档 | 注入闸确定生效（治本每会话 token）；WARN 推动归档；文档减缓源头 |
| 阈值 | 分字段 400 / 1200 / 800，config 可覆盖 | 贴合语义：current_step 短指针最严，pending/unresolved 清单宽 |
| 截断 | 头部保留 + 尾部指针 | 最简确定；current_step 当前状态在头部保住，旧里程碑（尾部 `\|【上一里程碑】`）被砍 |
| WARN 触发 | 原始长度 > `limit × 2` | clamp 静默压缩，只在明显失控才催、不吵；ratio=2 先硬编码 |
| verbose 档 | 也 clamp | clamp 治「无界撑爆」，与 verbose「显示全部半残清单」正交 |

## 4. 架构（四组件，各自独立可测）

### 4.1 组件 ① 注入闸 — 新模块 `hooks/lib/brief_clamp.py`

```python
def clamp_field(value: str, limit: int) -> str:
    """超 limit 则头部保留 + 尾部折叠指针。UTF-8 安全（str 按 code point 切，不裂多字节）。

    limit <= 0 视为不限（no-op），防误配 0 把字段全砍。
    """
    if limit <= 0 or len(value) <= limit:
        return value
    folded = len(value) - limit
    return value[:limit] + f"…⟨+{folded} 字符已折叠，完整见 .kdev/memory/当前状态.md⟩"


def format_bloat_hint(bloat: list) -> str:
    """bloat = [(field_name, orig_len, limit), ...]。空 → ""；否则一条 P1 hint 行。"""
    if not bloat:
        return ""
    items = "；".join(f"{n} 已 {L} 字符（超阈值 {lim} 的 {L // lim}×）" for n, L, lim in bloat)
    return (f"  - 📈 frontmatter 字段膨胀：{items} —— "
            f"建议把旧条目归档进 每日汇总/，current_step/pending 只留短指针"
            f"（详见 dev-note 上下文消耗诊断）")
```

**接入点**：`session-start-brief.py` `main()`，读三字段后（现 `:559-562` 之后）：

```python
limits = read_brief_field_limits(kdev_dir)
_triples = [("current_step", state_step, limits["current_step"]),
            ("pending_decisions", state_pending, limits["pending_decisions"]),
            ("unresolved_gotchas", state_unresolved, limits["unresolved_gotchas"])]
bloat = [(n, len(v), lim) for n, v, lim in _triples if lim > 0 and len(v) > lim * 2]  # 原始长度判 WARN；lim<=0（不限）不 WARN，兼防除零
field_bloat_hint = format_bloat_hint(bloat)
state_step = clamp_field(state_step, limits["current_step"])
state_pending = clamp_field(state_pending, limits["pending_decisions"])
state_unresolved = clamp_field(state_unresolved, limits["unresolved_gotchas"])
```

WARN 判定用**原始长度**（clamp 前），故顺序必须先判 bloat、再 clamp。normal / compact 两档随后拿到 clamped 值，**单点接入覆盖两档**。`read_state_field` 保持纯读不动。

### 4.2 组件 ② config — `hooks/lib/memory_config.py`

照 `read_distill_thresholds` 写，复用 `_read_int_default` + fail-open：

```python
DEFAULT_BRIEF_LIMIT_CURRENT_STEP = 400
DEFAULT_BRIEF_LIMIT_PENDING = 1200
DEFAULT_BRIEF_LIMIT_UNRESOLVED = 800

def read_brief_field_limits(kdev_dir=".kdev/memory") -> dict:
    config = _read_config(kdev_dir)
    return {
        "current_step": _read_int_default(config,
            ("brief.limit_current_step", "brief_limit_current_step"),
            DEFAULT_BRIEF_LIMIT_CURRENT_STEP),
        "pending_decisions": _read_int_default(config,
            ("brief.limit_pending_decisions", "brief_limit_pending_decisions"),
            DEFAULT_BRIEF_LIMIT_PENDING),
        "unresolved_gotchas": _read_int_default(config,
            ("brief.limit_unresolved_gotchas", "brief_limit_unresolved_gotchas"),
            DEFAULT_BRIEF_LIMIT_UNRESOLVED),
    }
```

未配置 / 非法 → fail-open 到默认。docstring 字段表补这 3 个 key。

### 4.3 组件 ③ WARN 接线 — `_build_brief`

新增参数 `field_bloat_hint: str = ""`，`brief_kwargs` 传入。两处接：

- **P1 区**（`:393-406`，与 `missing_past` / `drift_hint` 并列）：`if field_bloat_hint: p1_lines.append(field_bloat_hint)` —— 自动覆盖 normal / resume / `source=compact`（压缩恢复）三分支。
- **verbosity==compact early-return 分支**（`:441-457`，自组装 `cparts` 后直接 return，不走 p1_lines）：单独 `if field_bloat_hint: cparts.append(field_bloat_hint)`。

### 4.4 组件 ④ 文档约束（减缓源头·靠 LLM 自律）

- `agents/kdev-step-recorder.md`：新增一条落盘规范——更新 `current_step` **只写最新 Step ID（+可选 ≤ 一句状态）**，严禁 `\|【上一里程碑】` 式拼接旧叙事。
- `skills/kdev-memory/SKILL.md:182`：补 `current_step` = **短指针**；`pending_decisions` / `unresolved_gotchas` 超阈值时把旧条目归档进 `每日汇总/`，frontmatter 不无界堆。

## 5. 数据流

```
SessionStart
  → read 三字段（原始值）
  → 以原始长度判 WARN（> limit×2）→ field_bloat_hint
  → 各自 clamp_field（> limit 头部保留 + 尾部指针）
  → 传入 _build_brief
  → normal/compact/resume 注入 clamped 值 + P1 bloat hint
```

## 6. 边界与兼容

- **健康项目零影响**：字段未超阈值 → clamp no-op（本仓 current_step 31 / unresolved 205 完全不变）。
- **fail-open**：config 缺失 / 非法 → 默认阈值；空字段 → no-op；`limit <= 0` → 不限（clamp 与 WARN 双双跳过——防误配 0 全砍 + 防 `format_bloat_hint` 除零）。
- **三档一致**：verbose 也 clamp。
- **向后兼容**：现有 5 个 brief 测试的 pending 值极短（`[开 P-X]`），不触发截断，全绿。

## 7. 测试计划

- **`test_brief_clamp.py`（新）**：
  - `clamp_field`：`len < / = / > limit`；空值；`limit=0` no-op；UTF-8（含中文 / emoji 时按 code point 计数与切片，返回合法 str、不抛异常）；指针文案含折叠字符数。
  - `format_bloat_hint`：空 / 单字段 / 多字段。
- **`test_memory_config`**：`read_brief_field_limits` 默认 / config 覆盖 / 非法值 fail-open。
- **`test_brief_verbosity` 扩展**：
  - 注入 1500 字符 pending（> 1200，< 2400）→ normal & compact 均见折叠指针，**无** WARN。
  - 注入 2500 字符 pending（> 2400）→ 折叠指针 **且** P1 bloat hint 出现。
- **回归**：现有 5 例保持绿。

## 8. 文件清单

**新增**：

- `plugins/kdev-memory/hooks/lib/brief_clamp.py`
- `plugins/kdev-memory/tests/test_brief_clamp.py`

**改动**：

- `plugins/kdev-memory/hooks/lib/memory_config.py`（+`read_brief_field_limits` +3 默认常量 + docstring 字段表）
- `plugins/kdev-memory/hooks/session-start-brief.py`（import + main clamp/WARN + `_build_brief` 加 `field_bloat_hint` 参数 + compact 分支）
- `plugins/kdev-memory/agents/kdev-step-recorder.md`（落盘规范一条）
- `plugins/kdev-memory/skills/kdev-memory/SKILL.md`（:182 短指针约束）
- `plugins/kdev-memory/tests/test_brief_verbosity.py`（断言扩展）
- **plugin version bump**（G-004）：改了 hook/agent，须 bump `plugin.json` version，否则 marketplace cache stale。

## 9. 影响的文档 / 回写清单（R-009）

实现收尾时逐项回写 canonical：

- [x] dev-note `kdev-memory上下文消耗诊断-2026-07-10.md` §7.4-2：「写入侧闸位前移更根治」→ 探索推翻（写入侧无 Python 拦截点，注入侧才是确定生效）。就地修正 + 加锚指向本 spec。
- [x] `SKILL.md:182`：current_step 短指针约束（组件 ④ 已含，实现即回写）。
- [x] `plugin.json` version bump（G-004）。

## 10. 未决 / 风险

- **ratio=2 硬编码**：未来若太吵 / 太松，升级为 config key `brief.field_warn_ratio`（YAGNI，暂不做）。
- **current_step=400 是否够放「Step ID + 一句话」**：Step ID ~30 字符，留 ~370 给一句话，够。
- **compact 档已有 pending 注入**：clamp 后 compact 更省，正向无冲突。
