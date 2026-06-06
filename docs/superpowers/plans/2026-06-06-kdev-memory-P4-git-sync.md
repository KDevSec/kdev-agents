# kdev-memory P4 — git 托管自举 (Q-009) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Q-009's git hosting for engineering memory — `.kdev/` as an independent **nested repo** (its own remote), a tracked `kdev-sync.yml` recording that remote, and a **self-bootstrap** SessionStart hook (clone / pull / init / remind) + SessionEnd commit+push — so memory survives machine changes, syncs across worktrees/team, and never pollutes the code repo's history.

**Architecture:** A stdlib-only lib `plugins/kdev-memory/hooks/lib/kdev_sync.py` holds the logic: `read_sync_config` (parse `kdev-sync.yml`), `decide_action` (pure: pull/clone/init/remind), `bootstrap` (SessionStart orchestration over git), `sync_push` (SessionEnd commit+push), `reminder_text` (the 中文 托管提醒). Two thin hook scripts wire it: `kdev-sync-bootstrap.py` (SessionStart, **ordered before** the brief so `.kdev/` exists when the brief reads it) and a SessionEnd push (extend `session-end-check.py` or a new `kdev-sync-push.py`). The code repo keeps `.gitignore /.kdev/` and gains a tracked `kdev-sync.yml`.

**Tech Stack:** Python 3 stdlib only (`subprocess`, `pathlib`) — hooks MUST NOT fail on missing deps. pytest, following the existing `tests/test_worktree_link.py` pattern (import lib by path; drive git via `subprocess` against a temp bare repo; Windows-skip + manual-verify for platform bits).

**Source of truth:**
- Design: [记忆架构 §9 (Q-009)](../../framework/01-design/2026-06-05-02-数字员工记忆架构-分层+scope拓扑-v0.1.md) — three-piece (code repo / memory repo / bootstrap hook), nested-repo rationale, §9.4 reminder话术, §9.6 待实施 #1.
- Decision: [决策日志 Q-009](../../../.kdev/memory/决策日志.md).
- Test pattern analog: `plugins/kdev-memory/tests/test_worktree_link.py` (lib doing fs/git work via subprocess).
- Hook wiring: `plugins/kdev-memory/hooks/hooks.json` (SessionStart array — order matters; bootstrap before `session-start-brief.py`).

**Scope (P4 = §9.6 item #1 only):** self-bootstrap hook + `kdev-sync.yml` schema + §9.4 reminder. **Deferred** (other §9.6 items, not P4): scope/JSONL operational layer, rollup triggers, multi-employee write locks, Step-ID cross-machine collision, TODO persistence.

**Run-time note:** `python3` (no `python` on PATH). Commits use the AI-identity override (`git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit ...`, no quotes on `-c key=value`, no `Co-Authored-By`). NOTE: those are commits to the **code repo**; the `.kdev/` nested repo's own commits are made by the hook with whatever identity the hook sets — out of scope to override here.

---

## File Structure

| File | Responsibility |
|---|---|
| `plugins/kdev-memory/hooks/lib/kdev_sync.py` | `read_sync_config` / `decide_action` / `reminder_text` / `bootstrap` / `sync_push` + thin `_git` |
| `plugins/kdev-memory/tests/test_kdev_sync.py` | unit (config/decide/reminder, pure) + integration (clone/init/pull/push vs temp bare repo) |
| `plugins/kdev-memory/hooks/kdev-sync-bootstrap.py` | SessionStart hook: call `bootstrap`, print clone/pull result or the reminder |
| `plugins/kdev-memory/hooks/kdev-sync-push.py` | SessionEnd hook: call `sync_push` |
| `plugins/kdev-memory/hooks/hooks.json` | wire both (bootstrap ordered before brief in SessionStart) |
| `kdev-sync.yml.example` | tracked template documenting the schema |

Tests run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`.

---

## Task 1: `read_sync_config` + `reminder_text` (pure)

**Files:**
- Create: `plugins/kdev-memory/tests/test_kdev_sync.py`
- Create: `plugins/kdev-memory/hooks/lib/kdev_sync.py`

- [ ] **Step 1: Write the failing tests**

Create `plugins/kdev-memory/tests/test_kdev_sync.py`:

```python
"""Tests for hooks/lib/kdev_sync.py — Q-009 git 托管自举."""
import importlib.util
from pathlib import Path

import pytest

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "kdev_sync.py"
_spec = importlib.util.spec_from_file_location("kdev_sync", LIB)
kdev_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kdev_sync)


def test_read_config_missing_file_defaults(tmp_path):
    cfg = kdev_sync.read_sync_config(tmp_path)
    assert cfg["memory_repo"] is None
    assert cfg["branch"] == "main"


def test_read_config_parses_repo_and_branch(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text(
        "# memory hosting\nmemory_repo: git@github.com:org/mem.git\nbranch: trunk\n",
        encoding="utf-8",
    )
    cfg = kdev_sync.read_sync_config(tmp_path)
    assert cfg["memory_repo"] == "git@github.com:org/mem.git"
    assert cfg["branch"] == "trunk"


def test_read_config_strips_quotes_and_inline_comments(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text(
        'memory_repo: "https://x/y.git"   # the remote\n', encoding="utf-8")
    assert kdev_sync.read_sync_config(tmp_path)["memory_repo"] == "https://x/y.git"


def test_read_config_blank_repo_is_none(tmp_path):
    (tmp_path / "kdev-sync.yml").write_text("memory_repo:\nbranch: main\n", encoding="utf-8")
    assert kdev_sync.read_sync_config(tmp_path)["memory_repo"] is None


def test_reminder_text_is_chinese_and_mentions_nested_repo():
    t = kdev_sync.reminder_text()
    assert "记忆仓" in t and "nested repo" in t
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: collection error — `kdev_sync.py` does not exist (spec_from_file_location → exec fails / FileNotFoundError).

- [ ] **Step 3: Write the implementation**

Create `plugins/kdev-memory/hooks/lib/kdev_sync.py`:

```python
"""kdev-memory git 托管自举 (Q-009): .kdev/ 独立 nested repo + kdev-sync.yml 自举.

代码仓 .gitignore 忽略 /.kdev/；tracked 的 kdev-sync.yml 记"记忆仓 remote"。
SessionStart 自举：
  - .kdev/.git 存在                  -> pull（永远拿最新，胜 submodule 钉死 SHA）
  - 无 .git，.kdev/ 空/缺，有 remote  -> clone（新机器零手动）
  - 无 .git，.kdev/ 有内容，有 remote -> init（把本机已有记忆转成 nested repo + 首推）
  - 无 remote                        -> 中文托管提醒（强烈建议、非强制）
SessionEnd/rollup -> commit + push。
全程 stdlib-only —— hook 不能因缺依赖而炸。
"""
import subprocess
from pathlib import Path

REMINDER = (
    "检测到工程记忆尚未 git 托管。强烈建议建立独立记忆仓（nested repo）并在 "
    "kdev-sync.yml 登记，以便跨机器 / 团队同步、换机不丢记忆。是否现在初始化？"
)


def read_sync_config(repo_root):
    """Parse the flat kdev-sync.yml -> {'memory_repo': url|None, 'branch': str}."""
    cfg = {"memory_repo": None, "branch": "main"}
    path = Path(repo_root) / "kdev-sync.yml"
    if not path.exists():
        return cfg
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key in cfg and val:
            cfg[key] = val
    return cfg


def reminder_text():
    """The 中文 托管提醒 (记忆架构 §9.4)."""
    return REMINDER
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/kdev_sync.py plugins/kdev-memory/tests/test_kdev_sync.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P4 kdev-sync config parse + 托管提醒 (Q-009)"
```

---

## Task 2: `decide_action` (pure bootstrap decision)

**Files:**
- Modify: `plugins/kdev-memory/tests/test_kdev_sync.py` (append)
- Modify: `plugins/kdev-memory/hooks/lib/kdev_sync.py` (append `decide_action`)

- [ ] **Step 1: Append the failing tests**

Append to `plugins/kdev-memory/tests/test_kdev_sync.py`:

```python
def test_decide_pull_when_has_git():
    # .kdev/.git present -> always pull (uses .kdev's own remote), regardless of yml remote.
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote=None) == "pull"
    assert kdev_sync.decide_action(has_git=True, kdev_nonempty=True, remote="r") == "pull"


def test_decide_clone_when_empty_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote="r") == "clone"


def test_decide_init_when_existing_content_and_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote="r") == "init"


def test_decide_remind_when_no_remote():
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=True, remote=None) == "remind"
    assert kdev_sync.decide_action(has_git=False, kdev_nonempty=False, remote=None) == "remind"
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: FAIL — `AttributeError: module 'kdev_sync' has no attribute 'decide_action'`.

- [ ] **Step 3: Append the implementation**

Append to `plugins/kdev-memory/hooks/lib/kdev_sync.py`:

```python
def decide_action(*, has_git, kdev_nonempty, remote):
    """Pure SessionStart bootstrap decision.

    Returns one of:
      'pull'   — .kdev/ is already a repo (fetch latest).
      'clone'  — no repo, .kdev/ empty/absent, a remote is configured (new machine).
      'init'   — no repo, .kdev/ already has local content, a remote is configured
                 (convert this machine's existing memory into the nested repo + first push).
      'remind' — no remote configured (emit the 中文 托管提醒; do nothing destructive).
    """
    if has_git:
        return "pull"
    if remote:
        return "init" if kdev_nonempty else "clone"
    return "remind"
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: 9 passed (5 + 4).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/kdev_sync.py plugins/kdev-memory/tests/test_kdev_sync.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P4 decide_action bootstrap decision — pull/clone/init/remind (Q-009)"
```

---

## Task 3: git wrappers — `bootstrap` + `sync_push` (integration)

**Files:**
- Modify: `plugins/kdev-memory/tests/test_kdev_sync.py` (append integration tests + a helper)
- Modify: `plugins/kdev-memory/hooks/lib/kdev_sync.py` (append `_git`, `bootstrap`, `sync_push`)

- [ ] **Step 1: Append the failing integration tests**

Append to `plugins/kdev-memory/tests/test_kdev_sync.py`:

```python
import subprocess as _sp


def _git(args, cwd):
    return _sp.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def _bare_remote(tmp_path):
    """Create a bare repo to act as the memory remote; return its path (as a file URL)."""
    bare = tmp_path / "mem-remote.git"
    _git(["init", "--bare", str(bare)], cwd=tmp_path)
    return bare


def _write_yml(repo_root, remote):
    (repo_root / "kdev-sync.yml").write_text(f"memory_repo: {remote}\nbranch: main\n", encoding="utf-8")


def test_remind_when_no_yml(tmp_path):
    (tmp_path / ".kdev").mkdir()
    (tmp_path / ".kdev" / "x.md").write_text("local", encoding="utf-8")
    res = kdev_sync.bootstrap(tmp_path)
    assert res["action"] == "remind"
    assert "记忆仓" in res["message"]


def test_init_existing_then_pull_roundtrip(tmp_path):
    # machine A: existing local .kdev content + remote configured -> init + first push.
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    res = kdev_sync.bootstrap(repo_a)
    assert res["action"] == "init" and res["ok"], res
    assert (repo_a / ".kdev" / ".git").exists()

    # machine B: fresh clone from the same remote (empty .kdev) -> clone.
    repo_b = tmp_path / "B"
    repo_b.mkdir()
    _write_yml(repo_b, str(bare))
    res_b = kdev_sync.bootstrap(repo_b)
    assert res_b["action"] == "clone" and res_b["ok"], res_b
    assert (repo_b / ".kdev" / "执行日志.md").read_text(encoding="utf-8") == "step 1\n"


def test_sync_push_then_pull_propagates(tmp_path):
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    kdev_sync.bootstrap(repo_a)                 # init + push "step 1"

    repo_b = tmp_path / "B"
    repo_b.mkdir()
    _write_yml(repo_b, str(bare))
    kdev_sync.bootstrap(repo_b)                 # clone

    # A appends + sync_push; B pulls and sees it.
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\nstep 2\n", encoding="utf-8")
    push = kdev_sync.sync_push(repo_a, message="sync step 2")
    assert push["ok"] and push["pushed"], push
    pull = kdev_sync.bootstrap(repo_b)          # has .git -> pull
    assert pull["action"] == "pull" and pull["ok"], pull
    assert "step 2" in (repo_b / ".kdev" / "执行日志.md").read_text(encoding="utf-8")


def test_sync_push_noop_when_no_changes(tmp_path):
    bare = _bare_remote(tmp_path)
    repo_a = tmp_path / "A"
    (repo_a / ".kdev").mkdir(parents=True)
    (repo_a / ".kdev" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo_a, str(bare))
    kdev_sync.bootstrap(repo_a)
    res = kdev_sync.sync_push(repo_a)
    assert res["ok"] and res["pushed"] is False  # nothing to commit


def test_sync_push_skips_when_untracked(tmp_path):
    (tmp_path / ".kdev").mkdir()
    res = kdev_sync.sync_push(tmp_path)
    assert res["ok"] and res["pushed"] is False  # no .kdev/.git -> skip


def test_init_writes_gitignore_and_excludes_machine_local(tmp_path):
    bare = _bare_remote(tmp_path)
    repo = tmp_path / "A"
    (repo / ".kdev" / "memory" / "state").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "state" / "counter.txt").write_text("7", encoding="utf-8")
    (repo / ".kdev" / "memory" / "执行日志.md").write_text("step 1\n", encoding="utf-8")
    _write_yml(repo, str(bare))
    assert kdev_sync.bootstrap(repo)["ok"]
    assert (repo / ".kdev" / ".gitignore").exists()
    tracked = _git(["ls-files"], cwd=repo / ".kdev").stdout
    assert "执行日志.md" in tracked
    assert "counter.txt" not in tracked   # machine-local state/ excluded from the hosted repo
```

> **Note for the implementer:** git needs a committer identity. In CI/sandboxes `user.name`/`user.email` may be unset. The `_git` wrapper in `kdev_sync.py` MUST pass `-c user.name=... -c user.email=...` (or `-c commit.gpgsign=false` + a default identity) on `init`/commit operations so these tests are hermetic. Use a fixed bootstrap identity like `kdev-memory <kdev@local>` for the nested repo's own commits.

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: FAIL — `AttributeError: module 'kdev_sync' has no attribute 'bootstrap'`.

- [ ] **Step 3: Append the implementation**

Append to `plugins/kdev-memory/hooks/lib/kdev_sync.py`:

```python
# Fixed identity for the nested memory repo's own commits (hermetic; the code repo's
# AI/human identity is separate and set elsewhere).
_GIT_ID = ["-c", "user.name=kdev-memory", "-c", "user.email=kdev@local", "-c", "commit.gpgsign=false"]

# Machine-local memory (NOT hosted to the shared memory repo) — kdev-memory §5.3 #13/#14/#15/#16.
# Bare names (no internal slash) match at any depth, covering both the flat layout
# (.kdev/memory/state/) and the scoped layout (.kdev/state/).
_MACHINE_LOCAL_GITIGNORE = """# kdev-memory nested repo — machine-local, not hosted (§5.3)
state/
checkpoints/
hud.md
dataset/
"""


def _ensure_machine_local_gitignore(kdev):
    """Write .kdev/.gitignore excluding machine-local dirs if absent (counters/checkpoints/hud/dataset)."""
    gi = Path(kdev) / ".gitignore"
    if not gi.exists():
        gi.write_text(_MACHINE_LOCAL_GITIGNORE, encoding="utf-8")


def _git(args, cwd, *, identity=False):
    pre = _GIT_ID if identity else []
    return subprocess.run(["git", *pre, *args], cwd=str(cwd),
                          capture_output=True, text=True)


def _kdev_dir(repo_root):
    return Path(repo_root) / ".kdev"


def bootstrap(repo_root):
    """SessionStart bootstrap. Returns {'action', 'ok', 'message'}. Never raises."""
    repo_root = Path(repo_root)
    kdev = _kdev_dir(repo_root)
    has_git = (kdev / ".git").exists()
    kdev_nonempty = kdev.exists() and any(kdev.iterdir())
    remote = read_sync_config(repo_root)["memory_repo"]
    branch = read_sync_config(repo_root)["branch"]
    action = decide_action(has_git=has_git, kdev_nonempty=kdev_nonempty, remote=remote)

    if action == "remind":
        return {"action": "remind", "ok": True, "message": reminder_text()}

    if action == "pull":
        r = _git(["pull", "--ff-only"], cwd=kdev)
        return {"action": "pull", "ok": r.returncode == 0,
                "message": (r.stderr or r.stdout).strip()}

    if action == "clone":
        kdev.parent.mkdir(parents=True, exist_ok=True)
        r = _git(["clone", remote, str(kdev)], cwd=repo_root, identity=True)
        return {"action": "clone", "ok": r.returncode == 0,
                "message": (r.stderr or r.stdout).strip()}

    # action == "init": convert existing local .kdev/ into the nested repo + first push
    _ensure_machine_local_gitignore(kdev)   # don't push machine-local counters/checkpoints (§5.3)
    msgs = []
    for args, ident, tolerate in [
        (["init", "-b", branch], True, False),
        (["remote", "add", "origin", remote], False, True),   # tolerate "already exists"
        (["add", "-A"], False, False),
        (["commit", "-m", "chore(kdev-memory): bootstrap nested memory repo"], True, False),
        (["push", "-u", "origin", branch], True, False),
    ]:
        r = _git(args, cwd=kdev, identity=ident)
        msgs.append(f"git {args[0]}: rc={r.returncode}")
        if r.returncode != 0 and not tolerate:
            return {"action": "init", "ok": False,
                    "message": "; ".join(msgs) + " :: " + (r.stderr or "").strip()}
    return {"action": "init", "ok": True, "message": "; ".join(msgs)}


def sync_push(repo_root, message="chore(kdev-memory): session sync"):
    """SessionEnd/rollup: commit + push .kdev/. Returns {'ok', 'pushed', 'message'}. Never raises."""
    kdev = _kdev_dir(repo_root)
    if not (kdev / ".git").exists():
        return {"ok": True, "pushed": False, "message": "no .kdev/.git; skip (untracked memory)"}
    _git(["add", "-A"], cwd=kdev)
    status = _git(["status", "--porcelain"], cwd=kdev)
    if not status.stdout.strip():
        return {"ok": True, "pushed": False, "message": "nothing to commit"}
    c = _git(["commit", "-m", message], cwd=kdev, identity=True)
    if c.returncode != 0:
        return {"ok": False, "pushed": False, "message": (c.stderr or c.stdout).strip()}
    p = _git(["push"], cwd=kdev)
    return {"ok": p.returncode == 0, "pushed": p.returncode == 0,
            "message": (p.stderr or p.stdout).strip()}
```

- [ ] **Step 4: Run to verify they pass**

Run: `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q`
Expected: 16 passed (9 + 7).

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/kdev_sync.py plugins/kdev-memory/tests/test_kdev_sync.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P4 bootstrap + sync_push git wrappers (clone/init/pull/push) (Q-009)"
```

---

## Task 4: hook wiring + `kdev-sync.yml.example` + manual verify

**Files:**
- Create: `plugins/kdev-memory/hooks/kdev-sync-bootstrap.py` (SessionStart)
- Create: `plugins/kdev-memory/hooks/kdev-sync-push.py` (SessionEnd)
- Modify: `plugins/kdev-memory/hooks/hooks.json` (wire both; bootstrap BEFORE brief)
- Create: `kdev-sync.yml.example` (repo root, tracked template)

- [ ] **Step 1: Create the SessionStart bootstrap hook**

Create `plugins/kdev-memory/hooks/kdev-sync-bootstrap.py`:

```python
#!/usr/bin/env python3
"""SessionStart: bootstrap the .kdev/ nested memory repo (Q-009). Best-effort, never blocks."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import kdev_sync  # noqa: E402


def main():
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        res = kdev_sync.bootstrap(repo_root)
    except Exception as exc:  # hooks must never crash the session
        print(f"[kdev-sync] bootstrap skipped: {exc}", file=sys.stderr)
        return
    if res["action"] == "remind":
        # surface the 中文 reminder to the session
        print(f"<kdev-sync-reminder>\n{res['message']}\n</kdev-sync-reminder>")
    elif not res["ok"]:
        print(f"[kdev-sync] {res['action']} failed: {res['message']}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create the SessionEnd push hook**

Create `plugins/kdev-memory/hooks/kdev-sync-push.py`:

```python
#!/usr/bin/env python3
"""SessionEnd: commit + push the .kdev/ nested memory repo (Q-009). Best-effort, never blocks."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))
import kdev_sync  # noqa: E402


def main():
    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        res = kdev_sync.sync_push(repo_root)
    except Exception as exc:
        print(f"[kdev-sync] push skipped: {exc}", file=sys.stderr)
        return
    if not res["ok"]:
        print(f"[kdev-sync] push failed: {res['message']}", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Wire both into `hooks.json`**

In `plugins/kdev-memory/hooks/hooks.json`, add `kdev-sync-bootstrap.py` as the **first** SessionStart hook (before `session-start-brief.py`, so `.kdev/` exists when the brief reads it), and add a SessionEnd entry for `kdev-sync-push.py`. The SessionStart block becomes:

```json
"SessionStart": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" kdev-sync-bootstrap.py",
        "timeout": 30
      },
      {
        "type": "command",
        "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" session-start-brief.py",
        "timeout": 5
      }
    ]
  }
],
```

And add (or extend) a SessionEnd block:

```json
"SessionEnd": [
  {
    "hooks": [
      {
        "type": "command",
        "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" session-end-check.py",
        "timeout": 5
      },
      {
        "type": "command",
        "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" kdev-sync-push.py",
        "timeout": 30
      }
    ]
  }
],
```

> If a `SessionEnd` block already exists in `hooks.json`, add the `kdev-sync-push.py` entry to its `hooks` array rather than duplicating the block. Keep `session-end-check.py` first. The bootstrap/push timeouts are 30s (git network ops can be slow); the others stay at their existing values.

- [ ] **Step 4: Create the tracked `kdev-sync.yml.example` template**

Create `kdev-sync.yml.example` (repo root):

```yaml
# kdev-memory git 托管配置 (Q-009)
# 把本文件复制为 kdev-sync.yml 并填入"记忆仓"地址（独立 nested repo 的 remote）。
# 代码仓 .gitignore 忽略 /.kdev/；本文件 tracked，随 clone 到任何机器，
# SessionStart hook 据此自动 clone/pull 记忆仓（换机不丢记忆）。
memory_repo:        # 例: git@github.com:KDevSec/kdev-agents-memory.git  （留空则只本地、SessionStart 会中文提醒）
branch: main
```

- [ ] **Step 5: Verify hooks.json is valid JSON + lib import path works**

Run: `python3 -c "import json; json.load(open('plugins/kdev-memory/hooks/hooks.json')); print('hooks.json OK')"`
Expected: `hooks.json OK`.

Run: `python3 -c "import sys; sys.path.insert(0,'plugins/kdev-memory/hooks/lib'); import kdev_sync; print('lib import OK')"`
Expected: `lib import OK`.

- [ ] **Step 6: Manual verify checklist (hooks run in Claude Code's env; record results)**

Document in the commit message body or a short note (hooks can't be fully unit-tested end-to-end — same as `worktree_link.py`):
- [ ] With **no** `kdev-sync.yml`: a fresh session prints the `<kdev-sync-reminder>` 中文提醒, and does NOT touch `.kdev/`.
- [ ] With `kdev-sync.yml` pointing at a real empty remote, on this machine (existing `.kdev/` content): bootstrap does `init` + first push; `.kdev/.git` now exists.
- [ ] After a session with memory changes: SessionEnd `sync_push` commits + pushes; the remote has the new commit.
- [ ] On a second clone of the **code** repo (with `kdev-sync.yml`): first SessionStart `clone`s the memory repo automatically.

- [ ] **Step 7: Commit**

```bash
git add plugins/kdev-memory/hooks/kdev-sync-bootstrap.py plugins/kdev-memory/hooks/kdev-sync-push.py plugins/kdev-memory/hooks/hooks.json kdev-sync.yml.example
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): P4 wire SessionStart bootstrap + SessionEnd push + kdev-sync.yml.example (Q-009)"
```

---

## Done criteria

- `python3 -m pytest plugins/kdev-memory/tests/test_kdev_sync.py -q` → 16 passed (config 5 + decide 4 + integration 7).
- `init` writes `.kdev/.gitignore` excluding machine-local (`state/`/`checkpoints/`/`hud.md`/`dataset/`) so counters are never pushed to the shared memory repo.
- `kdev_sync.py` exposes: `read_sync_config`, `decide_action`, `reminder_text`, `bootstrap`, `sync_push` (+ `_git` helper). Stdlib-only; `bootstrap`/`sync_push` never raise.
- `decide_action` matrix: has_git→pull; empty+remote→clone; content+remote→init; no remote→remind.
- Integration: init→push (machine A) → clone (machine B) → A sync_push → B pull propagates; sync_push is a no-op with no changes and skips when `.kdev/.git` absent.
- Hooks wired: bootstrap ordered before brief (SessionStart); push on SessionEnd; both best-effort (never crash the session). `hooks.json` is valid JSON.
- `kdev-sync.yml.example` tracked; real `kdev-sync.yml` stays untracked-by-intent until the user fills the remote (it IS committed to the code repo once filled — it's the tracked pointer; `.gitignore` ignores `/.kdev/`, NOT `kdev-sync.yml`).

## User-involved step (before/at execution)

Creating the actual **memory remote** (an empty GitHub repo, e.g. `KDevSec/kdev-agents-memory`) and putting its URL in `kdev-sync.yml` is a **user action** — the plan builds the machinery; you decide the remote + privacy (recall §9.5: memory holds verbatim user话; a team-shared remote exposes it — keep private or sanitize). Until then, the reminder path is what runs.

**Next:** 阶段0 fully done (R1+R2+R3 + git 托管) → 阶段1: coding-flow refit onto kdev-core + first dogfood (the UED benchmark, two-pass).
</content>
