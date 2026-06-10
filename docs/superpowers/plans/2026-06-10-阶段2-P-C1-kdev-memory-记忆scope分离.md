# 阶段2 P-C1 · kdev-memory 记忆 scope 分离 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 kdev-memory 成为 scope-aware（`shared/` 项目层 + `staff/<canonical-id>/` per-员工层），opt-in 向后兼容——无 staff 注册时路径+行为与现状完全一致，不砸现有用户。

**Architecture:** 引入单一真相源 `hooks/lib/scope.py`，核心不变量 `flat 模式下 shared_dir(root) == root`（字节级路径不变）。布局检测 = `root/shared/` 目录是否存在（迁移脚本创建它即开启 scoped）。分两层改造：Tier A（只读 shared 的 hook，内部用 `shared_dir` 解析 markdown、`state/` 与 `.last-*` 标记仍在 root）；Tier B（召回/brief/rollup 跨 scope 聚合，额外读 `staff/<id>/执行日志.md` 并标 scope）。per-scope Step counter 复用 `step_id.py` 现有 slug 机制（recorder 传 canonical id 即可），Step ID 保持 `Step <slug>-N` 形态以便 P-C1b 后续叠加独立 `transcript_range` 字段。迁移脚本独立、手动、幂等，不自动跑（保框架仓 flat 不变）。

**Tech Stack:** Python 3.7+ stdlib-only（无第三方依赖），pytest（`tests/`），Claude Code hooks（`hooks.json` 不改），markdown agent prompt（`agents/kdev-step-recorder.md`），SKILL.md 文档。

---

## 设计约束（实施期间反复对照，别违反）

1. **opt-in 向后兼容**：无 `staff/` 注册（即无 `shared/` 目录）= flat 默认 = 现状。`shared_dir(root) == root` 是所有 Tier A 改造的安全网。**每个被改 hook 的现有测试（flat 模式）必须继续绿**——它们就是回归护栏。
2. **框架仓 `.kdev` 保持 flat 不迁**：`migrate_scope.py` 绝不自动运行、绝不在 `kdev-agents` 框架仓上跑。只有多员工 dogfood 工作区手动跑。
3. **right-size**：只建 `shared/` + 2 员工（`dev-engineer` + `req-architect`）的最小机制。**不上 JSONL（P-C2 defer）、不上并发写锁（P-C3 defer）**。
4. **命名全用 canonical ASCII id**：`staff/<id>/` 与 staff Step slug 一律用 `dev-engineer` / `req-architect` 这类 ASCII id。中文 display 不进 P-C1（属 kdev-team `staff.yml`，P-0）。brief 显示 canonical id 即可。
5. **markers/plumbing 留 root**：`state/`、`checkpoints/`、`dataset/`、`config.yaml`、`strict`、`.last-*` 全部留在 `.kdev/memory/` root（机器本地/插件记账），**只有 markdown 内容文件（执行日志/决策/踩坑/skill-feedback/当前状态/改进建议/方法论铁规/每日汇总/归档）迁入 `shared/`**。
6. **P-C1b 扩展余地**（减痛轨 spec，未实现）：Step ID 形态保持 `Step <slug>-N`；transcript 溯源将来作为 Step 条目里**独立的字段行**（如 `transcript_range:`）由 recorder 追加，**不要把 scope/transcript 折进 ID 或 counter 文件名**。
7. **commit 身份**：AI commit 一律 `git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "..."`（key=value 不加引号，不加 Co-Authored-By）。不 push（用户确认后推）。

---

## File Structure

**新建：**
- `hooks/lib/scope.py` — scope 解析单一真相源（is_scoped / shared_dir / staff_root / staff_dir / list_staff / staff_log_files / state_dir / resolve_step_slug）。
- `hooks/lib/migrate_scope.py` — flat → scoped 一次性幂等迁移 CLI（手动调用，不自动跑）。
- `tests/test_scope.py` — scope.py 单测（含 flat 不变量）。
- `tests/test_migrate_scope.py` — 迁移脚本单测。
- `tests/test_scope_integration.py` — 跨 hook scoped 行为端到端（Task 11）。

**修改（Tier A — 内部用 shared_dir 解析 markdown）：**
- `hooks/lib/frontmatter.py`、`hooks/lib/missing_summaries.py`、`hooks/lib/archive_hint.py`、`hooks/lib/promote_scan.py`、`hooks/lib/distill_trigger.py`、`hooks/lib/milestone.py`
- `hooks/session-start-brief.py`、`hooks/stop-check.py`、`hooks/pre-compact-check.py`、`hooks/session-end-check.py`

**修改（Tier B — 跨 scope 聚合）：**
- `hooks/lib/trigger-match.py`（召回）、`hooks/lib/weekly.py`（rollup）、`hooks/lib/distill.py`（dataset 收集）、`hooks/session-start-brief.py`（员工 scope block）。

**修改（接口 / 文档 / 版本）：**
- `hooks/lib/step_id.py`（导出 public `sanitize_slug`）
- `agents/kdev-step-recorder.md`（YAML 加 `scope` 字段 + per-scope 落盘）
- `skills/kdev-memory/SKILL.md`（scoped 布局 + Step ID 泛化 + dispatch scope 字段 + P-C1b 扩展注记）
- `.claude-plugin/plugin.json`（0.13.0 → 0.14.0）
- `CHANGELOG.md`（0.14.0 条目）

> **不动**：`hooks.json`（hook 注册不变）、`CLAUDE.md`（框架仓 flat，`Step main-N` 仍准确）、`migrate.py`（旧 v0.3 迁移，与 scope 正交）、`kdev_sync.py`（gitignore 已 scope-ready，迁移脚本复用其 `_ensure_machine_local_gitignore`）。

---

## Task 1: scope.py — scope 解析单一真相源

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/scope.py`
- Test: `plugins/kdev-memory/tests/test_scope.py`

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_scope.py`:

```python
"""test scope.py: flat/scoped 布局解析 + flat 不变量 + per-scope slug。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from scope import (  # noqa: E402
    is_scoped, shared_dir, staff_root, staff_dir, list_staff,
    staff_log_files, state_dir, resolve_step_slug, SHARED_SCOPES,
)


def _flat(tmp_path):
    root = tmp_path / "memory"
    root.mkdir()
    return root


def _scoped(tmp_path, staff=("dev-engineer", "req-architect")):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    for s in staff:
        (root / "staff" / s).mkdir(parents=True)
    return root


# ── flat 不变量（向后兼容核心）────────────────────────────────
def test_flat_not_scoped(tmp_path):
    root = _flat(tmp_path)
    assert is_scoped(root) is False

def test_flat_shared_dir_is_root(tmp_path):
    """flat 模式 shared_dir(root) 必须 == root（字节级路径不变 = 现有 hook 行为不变）。"""
    root = _flat(tmp_path)
    assert shared_dir(root) == root

def test_flat_no_staff(tmp_path):
    root = _flat(tmp_path)
    assert list_staff(root) == []
    assert staff_log_files("执行日志.md", root) == []


# ── scoped 布局 ──────────────────────────────────────────────
def test_scoped_detected(tmp_path):
    root = _scoped(tmp_path)
    assert is_scoped(root) is True

def test_scoped_shared_dir(tmp_path):
    root = _scoped(tmp_path)
    assert shared_dir(root) == root / "shared"

def test_scoped_list_staff_sorted(tmp_path):
    root = _scoped(tmp_path, staff=("req-architect", "dev-engineer"))
    assert list_staff(root) == ["dev-engineer", "req-architect"]

def test_staff_dir(tmp_path):
    root = _scoped(tmp_path)
    assert staff_dir("dev-engineer", root) == root / "staff" / "dev-engineer"

def test_staff_log_files_only_existing(tmp_path):
    root = _scoped(tmp_path)
    (root / "staff" / "dev-engineer" / "执行日志.md").write_text("x", encoding="utf-8")
    # req-architect 没有 执行日志.md → 不出现
    got = staff_log_files("执行日志.md", root)
    assert got == [("dev-engineer", root / "staff" / "dev-engineer" / "执行日志.md")]


# ── state 永远在 root（counter/plumbing 不 scoped）────────────
def test_state_dir_always_root(tmp_path):
    flat = _flat(tmp_path)
    assert state_dir(flat) == flat / "state"
    scoped = _scoped(tmp_path / "x" if False else tmp_path)  # reuse tmp
    # 重新建一个 scoped root 避免冲突
    root2 = tmp_path / "memory2"
    (root2 / "shared").mkdir(parents=True)
    assert state_dir(root2) == root2 / "state"


# ── resolve_step_slug：scope → Step slug ─────────────────────
def test_resolve_slug_staff_is_canonical_id(tmp_path):
    root = _scoped(tmp_path)
    assert resolve_step_slug("dev-engineer", root) == "dev-engineer"
    assert resolve_step_slug("req-architect", root) == "req-architect"

def test_resolve_slug_shared_scopes_fall_back_to_branch(tmp_path, monkeypatch):
    """shared/default/None/空 → 分支 slug（复用 step_id.compute_branch_slug）。"""
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    for scope in (None, "", "shared", "default", "project"):
        assert resolve_step_slug(scope) == "main"

def test_resolve_slug_sanitizes_staff_id(tmp_path):
    root = _scoped(tmp_path)
    # 防御：万一传了带非法字符的 scope，也 sanitize（canonical id 本就 ASCII，无副作用）
    assert resolve_step_slug("dev engineer!", root) == "dev-engineer"

def test_shared_scopes_constant():
    assert "shared" in SHARED_SCOPES and "default" in SHARED_SCOPES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_scope.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scope'`

- [ ] **Step 3: Write minimal implementation**

Create `plugins/kdev-memory/hooks/lib/scope.py`:

```python
"""kdev-memory v0.14 scope 解析单一真相源（P-C1 记忆 scope 分离）。

布局（opt-in 向后兼容）：
- flat（无 staff，= 现状）：`.kdev/memory/{执行日志.md, 决策日志.md, ...}`
- scoped（迁移后）：`.kdev/memory/{shared/<markdown>, staff/<canonical-id>/<markdown>}`

检测信号：`<root>/shared/` 目录是否存在（migrate_scope.py 创建它即开启 scoped）。

核心不变量：**flat 模式 `shared_dir(root) == root`**——所有 Tier A hook 把
`root / "执行日志.md"` 改成 `shared_dir(root) / "执行日志.md"` 后，flat 行为字节级不变。

machine-local plumbing（state/ checkpoints/ dataset/ .last-* config.yaml strict）
**永远在 root，不随 scope 迁移**。本模块只管 markdown 内容文件的 scope 解析。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Union

PathLike = Union[Path, str]

DEFAULT_ROOT = Path(".kdev/memory")

# 视同 shared 的 scope 名（Step slug 回退到分支 slug）
SHARED_SCOPES = frozenset({"", "shared", "default", "project"})


def is_scoped(root: PathLike = DEFAULT_ROOT) -> bool:
    """scoped 布局 iff `<root>/shared/` 是目录。"""
    return (Path(root) / "shared").is_dir()


def shared_dir(root: PathLike = DEFAULT_ROOT) -> Path:
    """项目层 markdown 落位。scoped → root/shared；flat → root（不变量）。"""
    root = Path(root)
    return root / "shared" if is_scoped(root) else root


def staff_root(root: PathLike = DEFAULT_ROOT) -> Path:
    return Path(root) / "staff"


def staff_dir(scope_id: str, root: PathLike = DEFAULT_ROOT) -> Path:
    return staff_root(root) / scope_id


def list_staff(root: PathLike = DEFAULT_ROOT) -> List[str]:
    """已注册员工 canonical id 列表（`staff/` 子目录名，排序）。无 staff → []。"""
    sr = staff_root(root)
    if not sr.is_dir():
        return []
    return sorted(d.name for d in sr.iterdir() if d.is_dir())


def staff_log_files(filename: str, root: PathLike = DEFAULT_ROOT) -> List[Tuple[str, Path]]:
    """返回每个 staff scope 下存在的 `<filename>`，形如 [(scope_id, path), ...]。"""
    out: List[Tuple[str, Path]] = []
    for sid in list_staff(root):
        p = staff_dir(sid, root) / filename
        if p.is_file():
            out.append((sid, p))
    return out


def state_dir(root: PathLike = DEFAULT_ROOT) -> Path:
    """hook plumbing（counter/dedup/pending）——永远在 root，不 scoped。"""
    return Path(root) / "state"


def resolve_step_slug(scope: Optional[str], root: PathLike = DEFAULT_ROOT) -> str:
    """scope → Step ID slug。

    - shared/default/project/None/空 → 分支 slug（复用 step_id.compute_branch_slug，
      保持 main 单轨现状 `Step main-N`）
    - 其它（员工 canonical id）→ sanitize 后的 id（`Step dev-engineer-N`）

    Step ID 形态恒为 `Step <slug>-N`；P-C1b 的 transcript 溯源是 Step 条目里
    独立字段，不折进 slug。
    """
    from step_id import compute_branch_slug, sanitize_slug
    if scope is None or scope.strip().lower() in SHARED_SCOPES:
        return compute_branch_slug()
    return sanitize_slug(scope.strip())
```

- [ ] **Step 4: Add public `sanitize_slug` to step_id.py**

In `plugins/kdev-memory/hooks/lib/step_id.py`, after the `_sanitize_slug` function (around line 41), add a public alias so `scope.py` doesn't import a private name:

```python
def sanitize_slug(s: str) -> str:
    """Public wrapper for slug sanitization (reused by scope.resolve_step_slug)."""
    return _sanitize_slug(s)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_scope.py tests/test_step_id.py -q`
Expected: PASS (all green; step_id existing tests unaffected)

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/scope.py plugins/kdev-memory/hooks/lib/step_id.py plugins/kdev-memory/tests/test_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 scope.py scope 解析单一真相源 + flat 不变量"
```

---

## Task 2: frontmatter.py — 当前状态.md 走 shared_dir

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/frontmatter.py:21-29`
- Test: `plugins/kdev-memory/tests/test_frontmatter_scope.py` (new)

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_frontmatter_scope.py`:

```python
"""test frontmatter.py scope 解析：scoped 时从 shared/ 读 当前状态.md。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import frontmatter  # noqa: E402

_FM = """---
phase: stage2
current_step: dev-engineer-3
---
body
"""


def test_flat_reads_root(tmp_path, monkeypatch):
    (tmp_path / ".kdev" / "memory").mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "当前状态.md").write_text(_FM, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert frontmatter.read_state_field("current_step") == "dev-engineer-3"


def test_scoped_reads_shared(tmp_path, monkeypatch):
    shared = tmp_path / ".kdev" / "memory" / "shared"
    shared.mkdir(parents=True)
    (tmp_path / ".kdev" / "memory" / "staff" / "dev-engineer").mkdir(parents=True)
    (shared / "当前状态.md").write_text(_FM, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert frontmatter.read_state_field("phase") == "stage2"
    assert frontmatter.has_state_frontmatter() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_frontmatter_scope.py -q`
Expected: FAIL on `test_scoped_reads_shared` (reads flat path, file not found → empty string)

- [ ] **Step 3: Write minimal implementation**

In `plugins/kdev-memory/hooks/lib/frontmatter.py`, add scope import at top (after existing imports, around line 15):

```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import shared_dir  # noqa: E402
```

Replace `_resolve_state_file` (lines 21-29) with:

```python
def _resolve_state_file() -> Optional[Path]:
    """scoped → shared/当前状态.md；flat → .kdev/memory/当前状态.md；再 fallback 0.2.0 遗留。"""
    scoped = shared_dir(Path(".kdev/memory")) / "当前状态.md"
    if scoped.is_file():
        return scoped
    flat = Path(".kdev/memory/当前状态.md")
    if flat.is_file():
        return flat
    legacy = Path(".kdev/当前状态.md")
    if legacy.is_file():
        return legacy
    return None
```

> 注：flat 模式 `shared_dir(root) == root`，故 `scoped` 与 `flat` 路径相同，行为不变；显式保留 `flat` 分支是冗余安全网（无害）。

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_frontmatter_scope.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/frontmatter.py plugins/kdev-memory/tests/test_frontmatter_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 frontmatter 当前状态.md 走 shared_dir 解析"
```

---

## Task 3: trigger-match.py — scoped 召回（shared + staff Step）

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/trigger-match.py`（`_iter_memory_files`、`scan_step_entries`、`format_recall`、`scan_g_entries`/`scan_tiegui_entries` 的 KDEV_DIR 引用）
- Test: `plugins/kdev-memory/tests/test_trigger_match_scope.py` (new)

> `trigger-match.py` 被 `user-prompt-trigger.py` 以 `subprocess.run([python, trigger-match.py], input=raw)` 跨进程调用，cwd = 项目根。模块级 `KDEV_DIR = Path(".kdev/memory")` 是 root；state 去重文件留 root（不动）。markdown 扫描改走 `shared_dir`，Step 召回额外扫 staff 日志并打 scope 标签。

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_trigger_match_scope.py`:

```python
"""test trigger-match.py scoped 召回：shared + staff Step 都能召回，staff 打 scope 标签。"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"


def _load_tm():
    spec = importlib.util.spec_from_file_location("trigger_match", LIB_DIR / "trigger-match.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LIB_DIR))
    spec.loader.exec_module(mod)
    return mod


_STEP_BLOCK = """---

## {sid}: {title}
triggers: [{trig}]
日期：{date}
about: {about}

### 执行事实
- 工具调用次数：1
"""


def test_scoped_step_recall_shared_and_staff(tmp_path, monkeypatch):
    root = tmp_path / ".kdev" / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    today = "2026-06-10"
    (root / "shared" / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step main-9", title="CEO 主线", trig="ceo-mainline-kw", date=today, about="project"),
        encoding="utf-8")
    (root / "staff" / "dev-engineer" / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step dev-engineer-2", title="员工活", trig="dev-scope-kw", date=today, about="feature/x"),
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)

    tm = _load_tm()
    # reload module-level KDEV_DIR-derived state by re-exec already done; call scan
    entries = tm.scan_step_entries()
    ids = {e["id"] for e in entries}
    assert "Step main-9" in ids
    assert "Step dev-engineer-2" in ids
    # staff 条目带 scope 标签
    staff_entry = next(e for e in entries if e["id"] == "Step dev-engineer-2")
    assert staff_entry.get("scope") == "dev-engineer"


def test_flat_step_recall_unchanged(tmp_path, monkeypatch):
    """flat 模式：执行日志在 root，无 staff，行为与现状一致。"""
    root = tmp_path / ".kdev" / "memory"
    root.mkdir(parents=True)
    today = "2026-06-10"
    (root / "执行日志.md").write_text(
        _STEP_BLOCK.format(sid="Step main-9", title="活", trig="flat-kw", date=today, about="project"),
        encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)
    tm = _load_tm()
    ids = {e["id"] for e in tm.scan_step_entries()}
    assert ids == {"Step main-9"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_trigger_match_scope.py -q`
Expected: FAIL on `test_scoped_step_recall_shared_and_staff`（staff 日志不被扫到 / 无 scope 字段）

- [ ] **Step 3: Write minimal implementation**

In `plugins/kdev-memory/hooks/lib/trigger-match.py`:

(a) Add scope import after `KDEV_DIR` definition (around line 44):

```python
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import shared_dir, staff_log_files  # noqa: E402
```

(b) Replace `_iter_memory_files` (lines 214-227) to resolve via `shared_dir`:

```python
def _iter_memory_files(prefix: str) -> list[Path]:
    """主文件（shared 解析）+ 归档子目录下同前缀归档文件。"""
    base = shared_dir(KDEV_DIR)
    paths = []
    main = base / f"{prefix}.md"
    if main.is_file():
        paths.append(main)
    archive_dir = base / "归档"
    if archive_dir.is_dir():
        paths.extend(sorted(archive_dir.glob(f"{prefix}-*.md")))
    return paths
```

(c) In `scan_step_entries` (lines 250-282), after building `entries` from `_iter_memory_files("执行日志")`, also scan each staff Step log and tag scope. Replace the function body's tail (the `for path in _iter_memory_files("执行日志"):` loop region) so it appends staff entries:

```python
    entries = []
    heading_re = re.compile(r"^##\s+(Step\s+[\w.-]+)[：:]\s*(.+?)\s*$")
    # shared / flat 主线
    for path in _iter_memory_files("执行日志"):
        lines = _read_file(path)
        if lines is None:
            continue
        entries.extend(_extract_entries_with_triggers(
            lines, heading_re,
            lambda m, line: (m.group(1), m.group(2)),
            "Step", str(path), date_filter=date_ok,
        ))
    # per-员工 scope（scoped 布局才有；flat 下 staff_log_files 返回 []）
    for scope_id, path in staff_log_files("执行日志.md", KDEV_DIR):
        lines = _read_file(path)
        if lines is None:
            continue
        scoped = _extract_entries_with_triggers(
            lines, heading_re,
            lambda m, line: (m.group(1), m.group(2)),
            "Step", str(path), date_filter=date_ok,
        )
        for e in scoped:
            e["scope"] = scope_id
        entries.extend(scoped)
    return entries
```

(d) In `_extract_entries_with_triggers`, ensure the entry dict tolerates an optional `scope` key — it already builds a plain dict; no change needed (we set `scope` after). For shared/flat entries, add a default so `format_recall` can read it uniformly: in the `entries.append({...})` block (around line 200), the dict has no `scope` — that's fine; use `.get("scope")` downstream.

(e) In `format_recall` (lines 453-472), surface scope for Step entries. Replace the per-entry loop:

```python
    for entry in selected:
        source_label = {
            "G": "踩坑", "Step": "今日进度", "铁规": "铁规", "spec": "项目 spec",
        }.get(entry["source"], entry["source"])
        scope = entry.get("scope")
        scope_tag = f"·{scope}" if scope else ""
        lines.append(f"- **{entry['id']}**（{source_label}{scope_tag}）{entry['title']}")
        lines.append(f"  → `{entry['path']}`")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_trigger_match_scope.py tests/test_trigger_match.py -q`
Expected: PASS (new scoped tests + existing flat tests green)

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/trigger-match.py plugins/kdev-memory/tests/test_trigger_match_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 trigger-match scoped 召回（shared + staff Step 标 scope）"
```

---

## Task 4: session-start-brief.py — shared 解析 + 员工 scope 进度 block

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-start-brief.py`（`main()` 的 shared 读 + 新增 staff block helper + `_build_brief` 加参数）
- Test: `plugins/kdev-memory/tests/test_session_start_brief_scope.py` (new)

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_session_start_brief_scope.py`:

```python
"""test session-start-brief.py scoped：shared 读 + 员工 scope 进度 block。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HOOKS = Path(__file__).parent.parent / "hooks"


def _load_brief():
    spec = importlib.util.spec_from_file_location("ssb", HOOKS / "session-start-brief.py")
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOOKS / "lib"))
    spec.loader.exec_module(mod)
    return mod


def test_staff_scope_block(tmp_path):
    mod = _load_brief()
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "staff" / "req-architect").mkdir(parents=True)
    (de / "执行日志.md").write_text(
        "---\n\n## Step dev-engineer-1: 建模块\n日期：2026-06-10\n", encoding="utf-8")
    block = mod._staff_scope_block(root)
    assert "dev-engineer" in block
    assert "1 条" in block
    assert "req-architect" in block  # 0 条也列出


def test_staff_scope_block_empty_flat(tmp_path):
    mod = _load_brief()
    root = tmp_path / "memory"; root.mkdir()
    assert mod._staff_scope_block(root) == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_session_start_brief_scope.py -q`
Expected: FAIL with `AttributeError: module 'ssb' has no attribute '_staff_scope_block'`

- [ ] **Step 3: Write minimal implementation**

In `plugins/kdev-memory/hooks/session-start-brief.py`:

(a) Add import (after line 39 import block):

```python
from scope import shared_dir, list_staff, staff_dir, is_scoped  # noqa: E402
```

(b) Add the staff block helper (after `_last_heading`, around line 113):

```python
def _staff_scope_block(kdev_dir: Path) -> str:
    """scoped 布局：列每个员工 scope 的 Step 数 + 最新 Step。flat → 空字符串。"""
    staff = list_staff(kdev_dir)
    if not staff:
        return ""
    lines = ["", "👥 **员工 scope 进度**："]
    for sid in staff:
        log = staff_dir(sid, kdev_dir) / "执行日志.md"
        count = 0
        latest = ""
        if log.is_file():
            try:
                text = log.read_text(encoding="utf-8")
            except OSError:
                text = ""
            for line in text.splitlines():
                if line.startswith("## Step "):
                    count += 1
                    latest = line[len("## "):].strip()
        tail = f"（最新 {latest}）" if latest else ""
        lines.append(f"- {sid}: {count} 条 Step{tail}")
    return "\n".join(lines)
```

(c) In `main()` (lines 366-397), route shared-file reads through `shared_dir`. Replace:

```python
    kdev_dir = Path(".kdev/memory")
```
...keep that as ROOT, then derive shared right after the `if not kdev_dir.is_dir()` guard (line 370):

```python
    shared = shared_dir(kdev_dir)
```

Then change the shared-file reads (lines 379-397) from `kdev_dir / X` to `shared / X`:
- `log_file = shared / "执行日志.md"`
- `summary_today_status = "已生成" if (shared / "每日汇总" / f"{today}.md").is_file() else "未生成"`
- `missing_past = list_missing_past_summaries(str(shared), today)`
- `promote_hint = scan_promote_candidates(str(shared), today)`
- `recent_q = _last_heading(shared / "决策日志.md", "## Q-")`
- `recent_g = _last_heading(shared / "踩坑日志.md", "## G-")`

Keep ROOT for: `warn_files = _glob_warn_files(kdev_dir)` (WARN at root), `checkpoint_files = _glob_checkpoint_files(kdev_dir)` (checkpoints at root, machine-local), `distill_hint = _distill_hint(kdev_dir)` (dataset/markers at root), `pending_hint = pending_format_brief_hint(kdev_dir / "state", ...)`, `skill_detect_drift(..., kdev_dir / "state")`. `read_state_field(...)` already scope-aware via Task 2.

(d) Compute the staff block and pass to `_build_brief`. After the `recent_g` line, add:

```python
    staff_block = _staff_scope_block(kdev_dir)
```

Add `staff_block: str = ""` parameter to `_build_brief` signature (after `skill_drift_hint`), and in the `startup/clear/default` branch (after the `recent` block append, around line 349) add:

```python
        if staff_block:
            parts.append(staff_block)
```

Pass `staff_block=staff_block` in the `_build_brief(...)` call (line 416-440).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_session_start_brief_scope.py tests/test_session_start_brief_prefix.py -q`
Expected: PASS (new scoped tests + existing brief tests green)

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/session-start-brief.py plugins/kdev-memory/tests/test_session_start_brief_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 SessionStart brief shared 解析 + 员工 scope 进度 block"
```

---

## Task 5: weekly.py — rollup 聚合 staff Step + per-scope 盘点

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/weekly.py`（`render` 的 markdown 读走 shared + 聚合 staff Step）
- Test: `plugins/kdev-memory/tests/test_weekly_scope.py` (new)

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_weekly_scope.py`:

```python
"""test weekly.py scoped：聚合 shared + staff Step，过程资产含 per-scope 盘点。"""
from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import weekly  # noqa: E402

_STEP = "---\n\n## {sid}: {t}\n日期：{d}\n\n### 执行事实\n- 工具调用次数：1\n"


def _render(root):
    buf = io.StringIO()
    d = date(2026, 6, 10)
    with redirect_stdout(buf):
        weekly.render(root, d, d)
    return buf.getvalue()


def test_scoped_aggregates_staff_steps(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="CEO", d="2026-06-10"), encoding="utf-8")
    (de / "执行日志.md").write_text(_STEP.format(sid="Step dev-engineer-1", t="员工", d="2026-06-10"), encoding="utf-8")
    out = _render(root)
    # 两条都计入 Step 总数
    assert "**Step**：2 条" in out
    # per-scope 盘点出现
    assert "dev-engineer" in out


def test_flat_unchanged(tmp_path):
    root = tmp_path / "memory"; root.mkdir()
    (root / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="活", d="2026-06-10"), encoding="utf-8")
    out = _render(root)
    assert "**Step**：1 条" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_weekly_scope.py -q`
Expected: FAIL on `test_scoped_aggregates_staff_steps`（staff Step 未计入，Step 总数=1）

- [ ] **Step 3: Write minimal implementation**

In `plugins/kdev-memory/hooks/lib/weekly.py`:

(a) Add scope import (after line 30 `force_utf8_stdio()`):

```python
from scope import shared_dir, staff_log_files  # noqa: E402
```

(b) In `render` (lines 73-81), resolve markdown via `shared_dir` and aggregate staff Steps. Replace the four `parse_entries(kdev / ...)` lines:

```python
    base = shared_dir(kdev)
    steps = [s for s in parse_entries(base / "执行日志.md", r"^##\s+Step\s+\S+.*$") if in_range_fn(s["date"])]
    # per-员工 scope Step 也计入（flat 下 staff_log_files 返回 []）
    staff_step_counts: dict[str, int] = {}
    for scope_id, path in staff_log_files("执行日志.md", kdev):
        scoped = [s for s in parse_entries(path, r"^##\s+Step\s+\S+.*$") if in_range_fn(s["date"])]
        for s in scoped:
            s["scope"] = scope_id
        steps.extend(scoped)
        staff_step_counts[scope_id] = len(scoped)
    ques = [q for q in parse_entries(base / "决策日志.md", r"^##\s+Q-\d+.*$") if in_range_fn(q["date"])]
    gotchas = [g for g in parse_entries(base / "踩坑日志.md", r"^##\s+G-\d+.*$") if in_range_fn(g["date"])]
    rules = [r for r in parse_entries(base / "改进建议.md", r"^##\s+(?:R-\d+|建议\s*#?\s*\d+).*$") if in_range_fn(r["date"])]
```

(c) Change the remaining `kdev / X` reads in `render` to `base / X`:
- `daily = base / "每日汇总"` (line 89)
- `state = base / "当前状态.md"` (line 165)

(d) In the 过程资产 section (after line 109 `平均用户评分`), add per-scope breakdown when present:

```python
    if staff_step_counts:
        print("- **per-员工 scope Step**：" + "；".join(
            f"{sid} {n} 条" for sid, n in sorted(staff_step_counts.items())))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_weekly_scope.py tests/test_weekly_aggregate.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/weekly.py plugins/kdev-memory/tests/test_weekly_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 weekly rollup 聚合 staff Step + per-scope 盘点"
```

---

## Task 6: distill.py + distill_trigger.py — dataset 收集 / 触发走 shared + staff

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/distill.py`（`_iter_memory_files` + `collect_entries` 加 staff Step）
- Modify: `plugins/kdev-memory/hooks/lib/distill_trigger.py:195`（执行日志 走 shared）
- Test: `plugins/kdev-memory/tests/test_distill_scope.py` (new)

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_distill_scope.py`:

```python
"""test distill scope：collect_entries 收 shared + staff Step；trigger 走 shared。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import distill  # noqa: E402

_STEP = "---\n\n## {sid}: {t}\ntriggers: [a,b,c,d,e]\n日期：2026-06-10\nabout: project\n\n### 执行事实\n- 工具调用次数：1\n"


def test_collect_includes_staff_steps(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="CEO"), encoding="utf-8")
    (de / "执行日志.md").write_text(_STEP.format(sid="Step dev-engineer-1", t="员工"), encoding="utf-8")
    entries = distill.collect_entries(root)
    ids = {e.entry_id for e in entries}
    assert "Step main-9" in ids
    assert "Step dev-engineer-1" in ids


def test_collect_flat_unchanged(tmp_path):
    root = tmp_path / "memory"; root.mkdir()
    (root / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="活"), encoding="utf-8")
    ids = {e.entry_id for e in distill.collect_entries(root)}
    assert ids == {"Step main-9"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_distill_scope.py -q`
Expected: FAIL on `test_collect_includes_staff_steps`（staff Step 未收集）

- [ ] **Step 3: Write minimal implementation**

In `plugins/kdev-memory/hooks/lib/distill.py`:

(a) Add import near top (after existing imports):

```python
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import shared_dir, staff_log_files  # noqa: E402
```

(b) Replace `_iter_memory_files` (lines 158-165) to resolve via shared:

```python
def _iter_memory_files(kdev_dir: Path, prefix: str) -> Iterable[Path]:
    """主文件（shared 解析）+ 归档目录下同前缀 markdown。"""
    base = shared_dir(kdev_dir)
    main = base / f"{prefix}.md"
    if main.is_file():
        yield main
    archive = base / "归档"
    if archive.is_dir():
        yield from sorted(archive.glob(f"{prefix}-*.md"))
```

(c) In `collect_entries` (lines 168-179), after the existing loop, append staff Step entries (only 执行日志 has per-scope variants):

```python
def collect_entries(kdev_dir: Path) -> list[Entry]:
    """扫所有核心 markdown + 归档（shared 解析）+ per-员工 Step 日志。"""
    entries: list[Entry] = []
    for kind, (filename, head_re) in HEAD_PATTERNS.items():
        prefix = filename.removesuffix(".md")
        for path in _iter_memory_files(kdev_dir, prefix):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            entries.extend(_split_entries(text, head_re, path.name))
    # per-员工 scope Step（flat 下 staff_log_files 返回 []）
    step_head_re = HEAD_PATTERNS["Step"][1]
    for scope_id, path in staff_log_files("执行日志.md", kdev_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        entries.extend(_split_entries(text, step_head_re, path.name))
    return entries
```

(d) In `plugins/kdev-memory/hooks/lib/distill_trigger.py`, add scope import and route 执行日志 through shared. After the imports, add:

```python
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import shared_dir  # noqa: E402
```

In `check_distill_trigger` (line 195 region), change `kdev / "执行日志.md"` to `shared_dir(kdev) / "执行日志.md"`. Markers (`.last-distill`) stay at `kdev` root.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_distill_scope.py tests/test_distill.py tests/test_distill_trigger.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/distill.py plugins/kdev-memory/hooks/lib/distill_trigger.py plugins/kdev-memory/tests/test_distill_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 distill dataset 收 staff Step + trigger 走 shared"
```

---

## Task 7: 剩余 Tier A hook 走 shared_dir（missing_summaries/archive_hint/promote_scan/milestone + stop/pre-compact/session-end）

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/missing_summaries.py`、`archive_hint.py`、`promote_scan.py`、`milestone.py`
- Modify: `plugins/kdev-memory/hooks/stop-check.py`、`pre-compact-check.py`、`session-end-check.py`
- Test: `plugins/kdev-memory/tests/test_tier_a_scope.py` (new)

> 这些都是"读 shared markdown / 标记里程碑路径"的消费者。原则：markdown 走 `shared_dir`，markers/state 留 root。lib 函数签名不变（继续收 `kdev_dir`=root），内部解析 shared。

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_tier_a_scope.py`:

```python
"""test Tier A hook scoped 解析：missing_summaries / archive_hint / promote_scan / milestone。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import importlib.util
import missing_summaries  # noqa: E402
import archive_hint  # noqa: E402
import promote_scan  # noqa: E402


def _milestone():
    spec = importlib.util.spec_from_file_location("milestone", LIB_DIR / "milestone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_missing_summaries_scoped(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    (root / "shared" / "每日汇总").mkdir()
    # root 收 kdev_dir，内部解析 shared
    out = missing_summaries.list_missing_past_summaries(str(root), "2026-06-10")
    assert "2020-01-01" in out


def test_archive_hint_scoped(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    out = archive_hint.collect_archive_hints(str(root))
    assert "执行日志.md" in out


def test_promote_scan_scoped(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    imp = root / "shared" / "改进建议.md"
    imp.write_text("\n".join(f"## R-{i} x" for i in range(1, 5)), encoding="utf-8")
    out = promote_scan.scan_promote_candidates(str(root), "2026-06-10")
    assert "改进建议" in out  # 4 条 pending ≥ 3 触发


def test_milestone_matches_shared_rule_file():
    mod = _milestone()
    assert mod.is_milestone_path(".kdev/memory/方法论铁规.md") is True
    assert mod.is_milestone_path(".kdev/memory/shared/方法论铁规.md") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_tier_a_scope.py -q`
Expected: FAIL (scoped paths not resolved; shared rule file not matched)

- [ ] **Step 3: Write minimal implementation**

(a) `missing_summaries.py`: add import + resolve shared in `list_missing_past_summaries`. After imports add:

```python
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import shared_dir  # noqa: E402
```

In `list_missing_past_summaries`, change `kdev = Path(kdev_dir)` then operations to use shared. Specifically replace the body's `kdev = Path(kdev_dir)` with:

```python
    kdev = shared_dir(Path(kdev_dir))
```

(The `if not kdev.is_dir()` guard, source-file reads, and `每日汇总` lookup then all resolve against shared. flat → unchanged.)

(b) `archive_hint.py`: add same import block, and in `collect_archive_hints` change `kdev = Path(kdev_dir)` to `kdev = shared_dir(Path(kdev_dir))`.

(c) `promote_scan.py`: add same import block. In `scan_promote_candidates`, keep the `.last-promote` marker at ROOT but read markdown from shared. Replace:

```python
    kdev = Path(kdev_dir)
    if not kdev.is_dir():
        return ""
    flush = kdev / ".last-promote"
```
with:

```python
    root = Path(kdev_dir)
    if not root.is_dir():
        return ""
    base = shared_dir(root)
    flush = root / ".last-promote"   # marker 留 root（plumbing）
```
and change the three markdown reads:
```python
    improvements = base / "改进建议.md"
    rule_md = base / "conventions.md"
    gotchas = base / "踩坑日志.md"
```

(d) `milestone.py`: make `is_milestone_path` match both flat and `shared/` rule-file paths. Read current `_MILESTONE_PATHS` (line 29 references `.kdev/memory/方法论铁规.md`). Add the shared variant to the list/set:

```python
    ".kdev/memory/方法论铁规.md",
    ".kdev/memory/shared/方法论铁规.md",
```

(If matching is suffix/`in`-based rather than exact, instead ensure `方法论铁规.md` suffix matches — inspect the actual matcher and adjust minimally so both paths return True.)

(e) `stop-check.py`: in `main()` (lines 133-220), derive shared and route markdown reads. After `kdev_dir = Path(".kdev/memory")` + guard, add `shared = shared_dir(kdev_dir)`. Change:
- `summary_file = shared / "每日汇总" / f"{today}.md"` (line 138)
- the stale-source loop `src = shared / name` (line 158)
- `log_file = shared / "执行日志.md"` (line 174)
- `list_missing_past_summaries(str(shared), today)` (line 189) — but since Task 7(a) made the lib resolve shared internally, pass `str(kdev_dir)` is also fine; **pass `str(shared)` here is double-resolve-safe because `shared_dir(shared) == shared` when shared has no nested `shared/`**. To avoid ambiguity, pass `str(kdev_dir)` (lib resolves). Use `list_missing_past_summaries(str(kdev_dir), today)`.
- `collect_archive_hints(str(kdev_dir))` (line 200) — lib resolves; keep `kdev_dir`.
- `state_dir = kdev_dir / "state"` (line 214) — keep root.
- strict-mode `(kdev_dir / "strict")` (line 220) — keep root.
- `_step_completeness_scan(log_file, today)` uses the `shared` log_file. ✓

Add import after line 41:
```python
from scope import shared_dir  # noqa: E402
```

> ⚠️ **避免 double-resolve**：Task 7(a-c) 让 `list_missing_past_summaries`/`collect_archive_hints`/`scan_promote_candidates` 内部对传入参数调用 `shared_dir`。因此 stop-check / brief 调用它们时**传 `kdev_dir`(root)**，不传 `shared`，否则 scoped 下会 `shared/shared`。直接的 `kdev_dir / "执行日志.md"` 这类裸路径才改成 `shared / ...`。Task 4 的 brief 同理需复核：`list_missing_past_summaries`/`scan_promote_candidates` 传 `str(kdev_dir)`，裸路径传 `shared`。

(f) `pre-compact-check.py`: in `main()` (line 75 region), after `kdev_dir = Path(".kdev/memory")` add `shared = shared_dir(kdev_dir)`; change `log_file = shared / "执行日志.md"` (line 88) and the source-file loop (line 130) `for src_name in (...)` reads to `shared / src_name`. checkpoints output stays root. Add import.

(g) `session-end-check.py`: after `kdev_dir = Path(".kdev/memory")` (line 87) add `shared = shared_dir(kdev_dir)`; `log_file = shared / "执行日志.md"` (line 92). WARN write stays root, `.last-flush` mtime compare stays root. Add import.

- [ ] **Step 4: Fix Task 4 brief double-resolve (verify)**

Re-open `session-start-brief.py` and confirm: `list_missing_past_summaries(str(kdev_dir), today)` and `scan_promote_candidates(str(kdev_dir), today)` pass **root** (lib resolves internally), while bare reads (`log_file`, `每日汇总`, `决策日志`, `踩坑日志`) use `shared`. Adjust if Task 4 wrote `str(shared)` into those two lib calls.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_tier_a_scope.py tests/test_step_completeness.py tests/test_stop_check_pending.py tests/test_session_end_mtime.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/missing_summaries.py plugins/kdev-memory/hooks/lib/archive_hint.py plugins/kdev-memory/hooks/lib/promote_scan.py plugins/kdev-memory/hooks/lib/milestone.py plugins/kdev-memory/hooks/stop-check.py plugins/kdev-memory/hooks/pre-compact-check.py plugins/kdev-memory/hooks/session-end-check.py plugins/kdev-memory/hooks/session-start-brief.py plugins/kdev-memory/tests/test_tier_a_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 剩余 Tier A hook 走 shared_dir（markers/state 留 root）"
```

---

## Task 8: migrate_scope.py — flat → scoped 一次性幂等迁移 CLI

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/migrate_scope.py`
- Test: `plugins/kdev-memory/tests/test_migrate_scope.py`

> 手动调用、不自动跑、不在框架仓跑。把 markdown 内容迁入 `shared/`，建空 `staff/<id>/`，markers/state/checkpoints/dataset/config 留 root，复用 `kdev_sync._ensure_machine_local_gitignore` 写 `.kdev/.gitignore`，写 `MIGRATED-scope-<date>.md`。

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_migrate_scope.py`:

```python
"""test migrate_scope.py：flat → scoped，markdown 进 shared，state 留 root，幂等。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from migrate_scope import migrate_to_scoped  # noqa: E402


def _flat_repo(tmp_path):
    kdev = tmp_path / ".kdev"
    mem = kdev / "memory"
    mem.mkdir(parents=True)
    (mem / "执行日志.md").write_text("# log", encoding="utf-8")
    (mem / "决策日志.md").write_text("# q", encoding="utf-8")
    (mem / "踩坑日志.md").write_text("# g", encoding="utf-8")
    (mem / "skill-feedback.md").write_text("# f", encoding="utf-8")
    (mem / "当前状态.md").write_text("---\nphase: x\n---\n", encoding="utf-8")
    (mem / "改进建议.md").write_text("# r", encoding="utf-8")
    (mem / "每日汇总").mkdir()
    (mem / "每日汇总" / "2026-06-01.md").write_text("d", encoding="utf-8")
    (mem / "config.yaml").write_text("record_mode: hybrid\n", encoding="utf-8")
    (mem / "state").mkdir()
    (mem / "state" / "step-counter-main.txt").write_text("9\n", encoding="utf-8")
    (mem / ".last-flush").write_text("", encoding="utf-8")
    return mem


def test_migrate_moves_markdown_to_shared(tmp_path):
    mem = _flat_repo(tmp_path)
    result = migrate_to_scoped(mem, staff=["dev-engineer", "req-architect"], today="2026-06-10")
    assert result["migrated"] is True
    # markdown 进 shared
    assert (mem / "shared" / "执行日志.md").is_file()
    assert (mem / "shared" / "当前状态.md").is_file()
    assert (mem / "shared" / "每日汇总" / "2026-06-01.md").is_file()
    assert not (mem / "执行日志.md").exists()
    # staff 目录建好
    assert (mem / "staff" / "dev-engineer").is_dir()
    assert (mem / "staff" / "req-architect").is_dir()
    # plumbing 留 root
    assert (mem / "state" / "step-counter-main.txt").is_file()
    assert (mem / "config.yaml").is_file()
    assert (mem / ".last-flush").is_file()
    # notice 写好
    assert (mem / "MIGRATED-scope-2026-06-10.md").is_file()
    # gitignore 写好（在 .kdev/）
    gi = (mem.parent / ".gitignore").read_text(encoding="utf-8")
    assert "state/" in gi


def test_migrate_idempotent(tmp_path):
    mem = _flat_repo(tmp_path)
    migrate_to_scoped(mem, staff=["dev-engineer"], today="2026-06-10")
    # 第二次：已 scoped → no-op，但补建缺失 staff
    result = migrate_to_scoped(mem, staff=["dev-engineer", "test-engineer"], today="2026-06-10")
    assert result["migrated"] is False  # 没再搬 markdown
    assert (mem / "staff" / "test-engineer").is_dir()  # 新员工补建
    # shared 内容没被破坏
    assert (mem / "shared" / "执行日志.md").read_text(encoding="utf-8") == "# log"


def test_migrate_creates_shared_marker(tmp_path):
    """迁移后 is_scoped(mem) 必须为 True（shared/ 已建）。"""
    from scope import is_scoped
    mem = _flat_repo(tmp_path)
    migrate_to_scoped(mem, staff=["dev-engineer"], today="2026-06-10")
    assert is_scoped(mem) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_migrate_scope.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'migrate_scope'`

- [ ] **Step 3: Write minimal implementation**

Create `plugins/kdev-memory/hooks/lib/migrate_scope.py`:

```python
"""kdev-memory v0.14 P-C1 一次性迁移：flat `.kdev/memory/*` → scoped `shared/` + `staff/<id>/`。

⚠️ 手动调用，**不**自动跑（不像 migrate.py），**不**在 kdev-agents 框架仓上跑——
只有多员工 dogfood 工作区需要。幂等：已 scoped（`shared/` 存在）→ 不再搬 markdown，
仅补建缺失的 staff 目录。

只搬 markdown 内容文件；machine-local plumbing（state/ checkpoints/ dataset/ config.yaml
strict .last-*）留 root。复用 kdev_sync 写 `.kdev/.gitignore`。

CLI: python3 migrate_scope.py [--staff dev-engineer,req-architect] [--root .kdev/memory]
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import date as _date
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import is_scoped  # noqa: E402

# 迁入 shared/ 的 markdown 内容（文件 + 目录）
_SHARED_ITEMS = [
    "执行日志.md",
    "决策日志.md",
    "踩坑日志.md",
    "skill-feedback.md",
    "当前状态.md",
    "改进建议.md",
    "方法论铁规.md",
    "conventions.md",
    "每日汇总",
    "归档",
]

DEFAULT_STAFF = ["dev-engineer", "req-architect"]


def migrate_to_scoped(
    root: Path | str,
    staff: List[str] = DEFAULT_STAFF,
    today: str = "",
) -> Dict:
    """flat → scoped 迁移（幂等）。返回 {'migrated': bool, 'moved': [...], 'staff_created': [...]}。"""
    root = Path(root)
    if not today:
        today = _date.today().isoformat()
    result: Dict = {"migrated": False, "moved": [], "staff_created": []}

    if not root.is_dir():
        return result

    # staff 目录（无论是否已 scoped 都确保存在 → 幂等补建新员工）
    def _ensure_staff() -> None:
        for sid in staff:
            d = root / "staff" / sid
            if not d.is_dir():
                d.mkdir(parents=True, exist_ok=True)
                result["staff_created"].append(sid)

    # 已 scoped → 仅补建 staff，不再搬 markdown
    if is_scoped(root):
        _ensure_staff()
        return result

    # 建 shared/ 并搬 markdown
    shared = root / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    for item in _SHARED_ITEMS:
        src = root / item
        if not src.exists():
            continue
        try:
            shutil.move(str(src), str(shared / item))
            result["moved"].append(item)
        except OSError:
            pass
    result["migrated"] = True

    _ensure_staff()

    # .kdev/.gitignore（复用 kdev_sync；root.parent == .kdev）
    try:
        from kdev_sync import _ensure_machine_local_gitignore
        _ensure_machine_local_gitignore(root.parent)
    except Exception:
        pass

    # 迁移说明
    notice = root / f"MIGRATED-scope-{today}.md"
    lines = [
        f"# kdev-memory P-C1 scope 迁移：{today}",
        "",
        "flat 布局已迁为 scoped：markdown 内容进 `shared/`，新增 per-员工 `staff/<id>/`。",
        "",
        "## 已迁入 shared/",
        "",
    ]
    lines += [f"- `{m}`" for m in result["moved"]] or ["_（无）_"]
    lines += ["", "## 新建 staff scope", ""]
    lines += [f"- `staff/{s}/`" for s in staff]
    lines += [
        "",
        "## 留在 root（machine-local / 配置，未迁）",
        "",
        "- `state/` `checkpoints/` `dataset/` `config.yaml` `strict` `.last-*`",
        "",
        "---",
        "本文件由 migrate_scope.py 生成，处理完可删。",
    ]
    try:
        notice.write_text("\n".join(lines), encoding="utf-8")
    except OSError:
        pass

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="kdev-memory flat → scoped 迁移（一次性幂等）")
    parser.add_argument("--staff", default=",".join(DEFAULT_STAFF),
                        help="逗号分隔的员工 canonical id（默认 dev-engineer,req-architect）")
    parser.add_argument("--root", default=".kdev/memory", help=".kdev/memory 路径")
    args = parser.parse_args()
    staff = [s.strip() for s in args.staff.split(",") if s.strip()]
    result = migrate_to_scoped(Path(args.root), staff=staff)
    if result["migrated"]:
        print(f"[kdev-memory] 已迁为 scoped：搬入 shared/ {len(result['moved'])} 项；"
              f"建 staff {result['staff_created']}")
    else:
        print(f"[kdev-memory] 已是 scoped（或空），补建 staff {result['staff_created']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_migrate_scope.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/migrate_scope.py plugins/kdev-memory/tests/test_migrate_scope.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 migrate_scope.py flat→scoped 一次性幂等迁移 CLI"
```

---

## Task 9: kdev-step-recorder.md — scope 字段 + per-scope 落盘

**Files:**
- Modify: `plugins/kdev-memory/agents/kdev-step-recorder.md`
- Test: `plugins/kdev-memory/tests/test_recorder_scope_helpers.py` (new — 测 recorder 依赖的解析逻辑，agent prompt 本身不可单测)

> recorder 是 markdown prompt。可单测的是它调用的 python 接口：`resolve_step_slug` + 目标日志路径解析。新增一个 helper 函数 `recorder_target_log(scope, root)` 到 scope.py 并测它，recorder prompt 引用该 helper。

- [ ] **Step 1: Write the failing test**

Create `plugins/kdev-memory/tests/test_recorder_scope_helpers.py`:

```python
"""test recorder scope helpers：目标日志路径 + slug 解析（recorder prompt 据此落盘）。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from scope import recorder_target_log, resolve_step_slug  # noqa: E402


def test_shared_scope_target_is_shared_log(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    assert recorder_target_log("shared", root) == root / "shared" / "执行日志.md"
    assert recorder_target_log(None, root) == root / "shared" / "执行日志.md"


def test_staff_scope_target_is_staff_log(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    assert recorder_target_log("dev-engineer", root) == root / "staff" / "dev-engineer" / "执行日志.md"


def test_flat_target_is_root_log(tmp_path):
    """flat（无 shared/）：任何 scope 都落 root 执行日志（向后兼容）。"""
    root = tmp_path / "memory"; root.mkdir()
    assert recorder_target_log(None, root) == root / "执行日志.md"
    assert recorder_target_log("shared", root) == root / "执行日志.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_recorder_scope_helpers.py -q`
Expected: FAIL with `ImportError: cannot import name 'recorder_target_log'`

- [ ] **Step 3: Add helper to scope.py**

In `plugins/kdev-memory/hooks/lib/scope.py`, add:

```python
def recorder_target_log(scope: Optional[str], root: PathLike = DEFAULT_ROOT) -> Path:
    """kdev-step-recorder 写 Step 的目标 执行日志.md。

    - shared/default/None → shared_dir(root)/执行日志.md（flat 下即 root/执行日志.md）
    - 员工 canonical id → staff/<id>/执行日志.md（flat 兜底回 root/执行日志.md）
    """
    root = Path(root)
    if scope is None or scope.strip().lower() in SHARED_SCOPES:
        return shared_dir(root) / "执行日志.md"
    if is_scoped(root):
        return staff_dir(scope.strip(), root) / "执行日志.md"
    return shared_dir(root) / "执行日志.md"
```

- [ ] **Step 4: Update the recorder agent prompt**

In `plugins/kdev-memory/agents/kdev-step-recorder.md`:

(a) Add `scope` to the Input contract YAML block (after `commits_batch_id`):

```yaml
scope: shared | <canonical-employee-id>   # 落哪个 scope；缺省 shared（= 现状/主线）。
                                           # 员工活由主控 dispatch 时设为 canonical id（如 dev-engineer）。
```

(b) Add a note after the contract explaining scope (after the `commits_batch_id` paragraph):

> `scope` (v0.14 新增, optional, default `shared`): 决定 Step 落哪个记忆 scope。`shared`/缺省 = 项目主线（落 `shared/执行日志.md`，flat 下即 `执行日志.md`，slug = 分支 slug → `Step main-N`）。员工 canonical id（`dev-engineer` / `req-architect`）= 该员工 scope（落 `staff/<id>/执行日志.md`，slug = canonical id → `Step <id>-N`）。**flat 布局（无 `shared/`）下任何 scope 都落 root 执行日志**（向后兼容）。不参与 hard-gate 校验。

(c) Replace **Action sequence step 1 (Compute next ID)** python snippet with scope-aware version:

```bash
python3 -c "
import sys
sys.path.insert(0, 'plugins/kdev-memory/hooks/lib')
from scope import resolve_step_slug, recorder_target_log
from step_id import mint_next_step_id
from pathlib import Path
scope = '<scope from YAML, default shared>'
slug = resolve_step_slug(scope)
print('MINTED:', mint_next_step_id(Path('.kdev/memory/state'), slug=slug))
print('TARGET:', recorder_target_log(scope))
"
```

Capture `MINTED:` (e.g. `Step dev-engineer-3`) and `TARGET:` (the 执行日志 path).

(d) Replace **step 3 (Append)** to append to `TARGET` (not hardcoded `.kdev/memory/执行日志.md`):

```bash
cat >> <TARGET path from step 1> << 'EOF'

---

## Step <ID>: <title>
... (full 4-section block) ...
EOF
```

(e) Replace **step 4 (Update 当前状态.md frontmatter)** with scope-conditional rule:

> **仅当 `scope` = shared/缺省时**更新 `shared_dir`/当前状态.md frontmatter（`current_step` + `last_updated`）。**员工 scope（staff）跳过 frontmatter 更新**——当前状态.md 是项目主线 CEO 状态，员工 Step 不污染它。

(f) Update **hard-gate #8 (frontmatter-counter drift guard)**: add a leading clause:

> **仅对 shared/缺省 scope 执行本闸门**（员工 scope 无 shared frontmatter counter 对应关系，跳过）。其余逻辑不变：parse `当前状态.md` 的 `current_step` ...（注意 scoped 下 `当前状态.md` 在 `shared/`，用 `shared_dir` 解析）。

(g) Update **constraint** "Do NOT modify files outside `.kdev/memory/`" — still true (shared/ and staff/ are under it). Add a P-C1b note near the schema:

> **P-C1b 扩展余地**（未实现）：将来 transcript 溯源会作为 Step 条目里**独立字段行**（如 `transcript_range:`）追加，**不改 Step ID 形态**（恒 `Step <slug>-N`）。本 recorder 的 ID/路径解析已为此留好结构。

- [ ] **Step 5: Run test to verify it passes**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_recorder_scope_helpers.py tests/test_scope.py tests/test_step_recorder_e2e.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/hooks/lib/scope.py plugins/kdev-memory/agents/kdev-step-recorder.md plugins/kdev-memory/tests/test_recorder_scope_helpers.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P-C1 step-recorder scope 字段 + per-scope 落盘 + recorder_target_log helper"
```

---

## Task 10: SKILL.md — scoped 布局文档 + Step ID 泛化 + dispatch scope 字段

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`

- [ ] **Step 1: 泛化「多 worktree 并发场景」章节（line 347 区）**

将 §「多 worktree 并发场景：Step ID 加分支前缀（v0.11+）」升级为「Step ID 加 scope 前缀（v0.11 分支 / v0.14 员工 scope）」。要点改写：
- `Step <branch-slug>-N` 泛化为 `Step <scope-slug>-N`，其中 scope-slug = 分支 slug（shared/主线，单装/flat 默认）或员工 canonical id（scoped 布局 staff scope）。
- 例补充：`Step main-9`（主线）/ `Step dev-engineer-1`（开发工程师 scope）。
- 指明 slug 由 `scope.resolve_step_slug(scope)` 决定（shared→分支 slug；员工→canonical id），底层仍走 `step_id.mint_next_step_id(state_dir, slug=...)`，counter 文件 `step-counter-<slug>.txt` 天然按 slug namespace。

- [ ] **Step 2: 新增「记忆 scope 分离（v0.14, P-C1）」小节**

在 Step ID 章节后插入一节，说明：
- **opt-in 布局**：单装/flat（默认，无 staff）= `.kdev/memory/{执行日志.md, ...}`，行为与现状完全一致；scoped（迁移后）= `.kdev/memory/{shared/<markdown>, staff/<canonical-id>/<markdown>}`。
- **检测**：`shared/` 目录存在 = scoped。`migrate_scope.py`（手动、幂等）创建它。
- **shared**：决策/踩坑/skill-feedback/当前状态/执行日志(主线)/改进建议/方法论铁规/每日汇总（项目时间线）。
- **staff/<id>/**：per-员工执行 rollup（`Step <id>-N`）。
- **plumbing 留 root**：state/ checkpoints/ dataset/ config.yaml .last-*（机器本地，不 scoped）。
- **召回/brief/rollup**：自动跨 shared + staff 聚合并标 scope。
- **框架仓保持 flat**（主控单轨）；只有多员工 dogfood 用 scoped。

- [ ] **Step 3: dispatch YAML schema 加 scope（line 407 区「用 kdev-step-recorder dispatch 落 step」）**

在 dispatch 段的 YAML summary schema 描述里加 `scope` 字段：`scope: shared | <canonical-id>`（缺省 shared）。说明主控 dispatch 员工活时设为该员工 canonical id；主线活缺省/shared。

- [ ] **Step 4: 验证 SKILL.md 无断链 + 渲染正常**

Run: `cd plugins/kdev-memory && grep -n "Step <scope-slug>-N\|scope\|staff/" skills/kdev-memory/SKILL.md | head -30`
Expected: 新增内容出现，无遗留 `Step <branch-slug>-N` 作为唯一形态的旧表述（line 126/138 也同步泛化或加注）。

- [ ] **Step 5: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/skills/kdev-memory/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): P-C1 SKILL scoped 布局 + Step ID scope 泛化 + dispatch scope 字段"
```

---

## Task 11: 端到端 scoped 集成测试

**Files:**
- Create: `plugins/kdev-memory/tests/test_scope_integration.py`

> 在一个 tmp scoped 仓上贯通验证：迁移 → 双 scope 各 mint 独立 counter → trigger 召回 shared+staff 标 scope → weekly 聚合 → brief 出员工 block。这是 spec §7 验收点 2「scope 分离落对位置」的 hook 层证据。

- [ ] **Step 1: Write the integration test**

Create `plugins/kdev-memory/tests/test_scope_integration.py`:

```python
"""P-C1 端到端：迁移 → per-scope counter → 召回 → rollup → brief 贯通。"""
from __future__ import annotations

import importlib.util
import io
import subprocess
import sys
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
HOOKS = Path(__file__).parent.parent / "hooks"
sys.path.insert(0, str(LIB_DIR))


def _git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "--allow-empty", "-m", "init"], cwd=repo, check=True)
    return repo


def test_end_to_end_scoped(tmp_path, monkeypatch):
    repo = _git_repo(tmp_path)
    mem = repo / ".kdev" / "memory"
    mem.mkdir(parents=True)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    (mem / "当前状态.md").write_text("---\nphase: stage2\ncurrent_step: main-1\n---\n", encoding="utf-8")
    (mem / "state").mkdir()

    from migrate_scope import migrate_to_scoped
    from scope import is_scoped, resolve_step_slug
    from step_id import mint_next_step_id

    # 1) 迁移
    migrate_to_scoped(mem, staff=["dev-engineer", "req-architect"], today="2026-06-10")
    assert is_scoped(mem)

    monkeypatch.chdir(repo)

    # 2) per-scope counter 独立
    state = mem / "state"
    assert mint_next_step_id(state, slug=resolve_step_slug("shared")) == "Step main-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("dev-engineer")) == "Step dev-engineer-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("req-architect")) == "Step req-architect-1"
    assert mint_next_step_id(state, slug=resolve_step_slug("dev-engineer")) == "Step dev-engineer-2"
    assert mint_next_step_id(state, slug=resolve_step_slug("shared")) == "Step main-2"

    # 3) 写两 scope 的 Step → 召回
    today = "2026-06-10"
    block = "---\n\n## {sid}: {t}\ntriggers: [{kw}]\n日期：{d}\n\n### 执行事实\n- 工具调用次数：1\n"
    (mem / "shared" / "执行日志.md").write_text(block.format(sid="Step main-2", t="主线活", kw="sharedkw", d=today), encoding="utf-8")
    (mem / "staff" / "dev-engineer" / "执行日志.md").write_text(block.format(sid="Step dev-engineer-2", t="员工活", kw="devkw", d=today), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("trigger_match", LIB_DIR / "trigger-match.py")
    tm = importlib.util.module_from_spec(spec); spec.loader.exec_module(tm)
    monkeypatch.setenv("KDEV_TRIGGER_TODAY", today)
    entries = tm.scan_step_entries()
    by_id = {e["id"]: e for e in entries}
    assert "Step main-2" in by_id and "Step dev-engineer-2" in by_id
    assert by_id["Step dev-engineer-2"].get("scope") == "dev-engineer"

    # 4) weekly 聚合两 scope
    import weekly
    buf = io.StringIO()
    with redirect_stdout(buf):
        weekly.render(mem, date(2026, 6, 10), date(2026, 6, 10))
    out = buf.getvalue()
    assert "**Step**：2 条" in out
    assert "dev-engineer" in out

    # 5) brief 员工 scope block
    bspec = importlib.util.spec_from_file_location("ssb", HOOKS / "session-start-brief.py")
    ssb = importlib.util.module_from_spec(bspec); bspec.loader.exec_module(ssb)
    sblock = ssb._staff_scope_block(mem)
    assert "dev-engineer" in sblock and "req-architect" in sblock
```

- [ ] **Step 2: Run the integration test**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_scope_integration.py -q`
Expected: PASS (if any assertion fails, fix the responsible module from Tasks 1-9 before proceeding — this is the cross-cutting验收)

- [ ] **Step 3: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/tests/test_scope_integration.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-memory): P-C1 端到端 scoped 集成测试（迁移→counter→召回→rollup→brief）"
```

---

## Task 12: bump version + CHANGELOG + 全量测试绿 + 回写 roadmap

**Files:**
- Modify: `plugins/kdev-memory/.claude-plugin/plugin.json`
- Modify: `plugins/kdev-memory/CHANGELOG.md`
- Modify: `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md`（§1.5.1 + §1.5 阶段2 行状态）

- [ ] **Step 1: 全量测试绿（前置验证）**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/ -q`
Expected: PASS（全部，含所有现有测试 — flat 回归 + 新 scoped 测试）。如有 fail，回到对应 Task 修复。

- [ ] **Step 2: bump plugin.json version**

In `plugins/kdev-memory/.claude-plugin/plugin.json`, change `"version": "0.13.0"` → `"version": "0.14.0"`. （G-004：plugin cache 按 version 键控，不 bump 则 hook 改动静默 stale。）

- [ ] **Step 3: CHANGELOG 0.14.0 条目**

In `plugins/kdev-memory/CHANGELOG.md`, prepend after the title line:

```markdown
## [0.14.0] — 2026-06-10

**P-C1 记忆 scope 分离（数字员工集群 阶段2）：kdev-memory scope-aware，opt-in 向后兼容。**

### ✨ 新增

- **`hooks/lib/scope.py`** — scope 解析单一真相源：`is_scoped`（`shared/` 存在即 scoped）/ `shared_dir`（flat 下 == root，字节级不变量）/ `staff_root` / `list_staff` / `staff_log_files` / `state_dir`（永远 root）/ `resolve_step_slug`（shared→分支 slug，员工→canonical id）/ `recorder_target_log`。
- **`hooks/lib/migrate_scope.py`** — flat → scoped 一次性幂等迁移 CLI（手动调用，不自动跑、不在框架仓跑）：markdown 进 `shared/`，建 `staff/<canonical-id>/`，plumbing 留 root，复用 kdev_sync 写 `.kdev/.gitignore`。

### 🔄 变更

- **scope-aware 改造**（opt-in，flat 行为不变）：`trigger-match`（召回 shared + staff Step，标 scope）/ `session-start-brief`（shared 解析 + 👥 员工 scope 进度 block）/ `weekly`（rollup 聚合 staff Step + per-scope 盘点）/ `distill`+`distill_trigger`（dataset 收 staff Step）/ `frontmatter` `missing_summaries` `archive_hint` `promote_scan` `milestone` `stop-check` `pre-compact-check` `session-end-check`（markdown 走 `shared_dir`，markers/state 留 root）。
- **`step_id.py`** 导出 public `sanitize_slug`；per-scope Step counter 复用现有 slug 机制（`Step <scope-slug>-N`）。
- **`agents/kdev-step-recorder.md`** — dispatch YAML 加 `scope` 字段（缺省 shared）；员工 scope 落 `staff/<id>/执行日志.md` 用 canonical id slug，跳过 shared frontmatter 更新 + drift guard。
- **`skills/kdev-memory/SKILL.md`** — scoped 布局文档 + Step ID scope 泛化 + dispatch scope 字段 + P-C1b transcript 扩展注记。

### 🧱 向后兼容 / 约束

- **opt-in**：无 `shared/`（无 staff 注册）= flat 默认 = 现状，路径+行为完全不变；现有用户零影响。
- **框架仓 `.kdev` 保持 flat**（主控单轨），`migrate_scope.py` 不自动跑、不在框架仓跑。
- **right-size**：只建 shared + 2 员工最小机制；P-C2 JSONL 操作层 / P-C3 并发写锁 defer。
- **G-004 提醒**：本版 bump `0.13.0 → 0.14.0`，用户侧需刷 marketplace + 重启 session 才生效。
```

- [ ] **Step 4: 回写 roadmap §1.5.1 + §1.5 阶段2 行**

In `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md`：
- §1.5.1：把 P-C1 状态从「待实施 / 下一步」改为「✅ 已实施（plan: docs/superpowers/plans/2026-06-10-阶段2-P-C1-kdev-memory-记忆scope分离.md；kdev-memory v0.14.0）」，并标注 P-A 解除 geblock。
- §1.5 阶段2 行：勾掉 P-C1，更新整体进度叙述（P-0 后接 P-C1 完成，下一步 P-A 需求架构师接底座）。

> 具体行号 / 措辞实施时按文件现状定；保持与既有 roadmap 风格一致（勾选框 / 状态标记）。

- [ ] **Step 5: 最终全量验证**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/ -q && python3 -c "import json,sys; v=json.load(open('.claude-plugin/plugin.json'))['version']; print('version', v); sys.exit(0 if v=='0.14.0' else 1)"`
Expected: 全测试 PASS + 打印 `version 0.14.0`

- [ ] **Step 6: Commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git add plugins/kdev-memory/.claude-plugin/plugin.json plugins/kdev-memory/CHANGELOG.md "docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md"
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-memory): P-C1 bump 0.14.0 + CHANGELOG + 回写 roadmap 阶段2"
```

---

## Self-Review（写完计划后自查，已执行）

**1. Spec coverage（spec §4 七项 + 任务 §4 候选 hook 清单）：**
- ① 布局 `shared/` + `staff/<id>/` → Task 8（迁移建布局）+ Task 1（解析）✓
- ② scope 解析层默认 flat / 检测 staff 才 scoped → Task 1 `is_scoped`/`shared_dir` ✓
- ③ per-scope Step counter `Step <id>-N` → Task 1 `resolve_step_slug` + Task 9 recorder（复用 step_id slug）✓
- ④ scoped 召回/brief/rollup 按 scope 过滤 → Task 3（召回）/ Task 4（brief）/ Task 5+6（rollup）✓
- ⑤ 迁移脚本 flat→shared + 开 staff，一次性幂等 → Task 8 ✓
- ⑥ `.kdev/.gitignore` 随新布局更新 → Task 8 复用 `kdev_sync._ensure_machine_local_gitignore`（bare-name 模式已 scope-ready，shared/+staff/ 自动托管，state/ 等忽略）+ 测试断言 ✓
- ⑦ bump version + CHANGELOG + 测试 → Task 12 + 每 Task 配测 ✓
- 候选 hook 精确清单（plan 阶段定）：path 解析（scope.py）/ step_id（sanitize_slug 导出）/ trigger-match（T3）/ session-start-brief（T4）/ rollup weekly（T5）+distill（T6）/ frontmatter（T2）/ missing_summaries+step_completeness（T7，step_completeness 经 log_path 参数无需改）+ archive_hint/promote_scan/milestone/stop/pre-compact/session-end（T7）✓

**2. Placeholder scan：** 每个 code step 含完整可执行代码/命令 + 期望输出；无 TBD/“类似上文”。Task 7(d)/(e)(milestone matcher)、Task 10、Task 12 §4 含「按文件现状定行号」类指示——这是对**既有文件局部措辞/行号**的定位说明（实施者读现状即可），非代码占位；涉及的代码改动本身（import、`shared_dir` swap、字段增改）均已给出具体内容。

**3. Type consistency：** `shared_dir`/`staff_log_files`/`resolve_step_slug`/`recorder_target_log` 签名跨 Task 1/3/5/6/9 一致；`mint_next_step_id(state_dir, slug=...)` 沿用现有签名；entry dict 的 `scope` 键在 T3 设置、T3 `format_recall` + T5/T11 用 `.get("scope")` 读，一致；`migrate_to_scoped(root, staff, today)` 返回 dict 结构在 T8/T11 一致。

**4. 关键风险点已显式护栏：** double-resolve（lib 内部 `shared_dir` vs 调用方传 shared）在 Task 7 Step 4 专门复核；flat 回归由每 Task「跑现有测试」+ Task 12 全量保障；框架仓不迁由 migrate_scope「手动+幂等+不自动跑」三重保障。
