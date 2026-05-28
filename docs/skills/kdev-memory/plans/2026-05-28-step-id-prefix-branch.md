# Step ID 加分支前缀（kdev-memory v0.11.0） Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** kdev-memory 在 secondary worktree symlink 共享 `.kdev/` 的架构下，Step ID 从全局递增 `Step N` 改为分支前缀 `Step <branch-slug>-N` + 每分支独立计数器，让并发会话不再产生 ID 冲突。

**Architecture:** 新增 `hooks/lib/step_id.py` 集中处理：(1) git 分支名 → slug 转换；(2) 每分支独立计数器文件 `.kdev/memory/state/step-counter-<slug>.txt` 用 flock 保护 atomic 递增；(3) 对外暴露 `mint_next_step_id(slug)` 给将来 SKILL.md 引用。SessionStart brief 探测当前分支并在 brief 里展示「本次 Step 前缀」。SKILL.md + 引用文档教模型新格式。历史 Step 1~8 保持无前缀格式不动（执行日志.md 加一行 `<!-- step_id_prefix_since: 2026-05-28 -->` 注释标识切换点）；`main` 分支计数器初始化为 8 以保持时间线连贯（下一条是 `Step main-9`）；新分支计数器从 0 起（下一条是 `Step <slug>-1`）。

**Tech Stack:** Python 3.7+（stdlib：`fcntl.flock` POSIX / `msvcrt.locking` Windows，`subprocess` for git），pytest（`threading` for concurrency test）。

**Spec source:** [.kdev/memory/决策日志.md#Q-003](../../../.kdev/memory/决策日志.md)

---

## 文件结构

| 文件 | 角色 | 改动类型 |
|------|------|----------|
| `plugins/kdev-memory/hooks/lib/step_id.py` | slug + counter + mint helper | 新增 |
| `plugins/kdev-memory/tests/test_step_id.py` | 单元 + 并发测试 | 新增 |
| `plugins/kdev-memory/hooks/session-start-brief.py` | 加 "本次 Step 前缀" 提示 | 修改 |
| `plugins/kdev-memory/tests/test_step_id_brief.py` | brief 集成测试 | 新增 |
| `plugins/kdev-memory/hooks/lib/step_completeness.py` | 验证 regex 兼容前缀 ID | 不改代码，补测 |
| `plugins/kdev-memory/tests/test_step_completeness.py` | 加 prefix-ID 用例 | 修改（若已存在）或新增 |
| `.kdev/memory/执行日志.md` | 加切换点注释 + counter 引导 | 修改（一次性） |
| `.kdev/memory/state/step-counter-main.txt` | main 分支计数器，初始值 8 | 新增 |
| `plugins/kdev-memory/skills/kdev-memory/SKILL.md` | 教模型新 ID 格式 | 修改 |
| `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md` | Step schema 文档 | 修改 |
| `plugins/kdev-memory/skills/kdev-memory/references/triggers-写法.md` | 示例 ID 格式 | 修改 |
| `CLAUDE.md`（kdev-agents 项目根） | 接口契约同步 | 修改 |
| `plugins/kdev-memory/CHANGELOG.md` | v0.11.0 条目 | 修改 |

---

## Task 1: `compute_branch_slug()` 把 git 分支名转 slug

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/step_id.py`
- Test: `plugins/kdev-memory/tests/test_step_id.py`

**Slug 规则**（先定死，再实现）：
- `main` → `main`
- `master` → `master`（不强行映射，尊重仓库习惯）
- `feature/cluster-x1` → `cluster-x1`（去 `feature/` 前缀）
- `bugfix/issue-42` → `bugfix-issue-42`（保留 `bugfix/`，`/` 转 `-`）
- `feat/foo/bar` → `foo-bar`（去 `feat/` 前缀，剩下的 `/` 转 `-`）
- 不在 git 仓库或 `git rev-parse --abbrev-ref HEAD` 失败 → 返回 `"unknown"`
- 分离 HEAD（detached HEAD）→ 返回 `"detached"`
- 含非 ASCII 或特殊字符 → 用 `re.sub(r"[^a-zA-Z0-9\-_]", "-", ...)` 兜底

- [ ] **Step 1: 写失败测试**

```python
# plugins/kdev-memory/tests/test_step_id.py
"""test step_id.py: branch slug 计算 + counter atomic 递增 + mint_next_step_id。"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from step_id import compute_branch_slug  # noqa: E402


def _git_init(tmp_path: Path, branch: str = "main") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    return repo


def _git_checkout(repo: Path, branch: str) -> None:
    subprocess.run(["git", "checkout", "-q", "-b", branch], cwd=repo, check=True)


def test_slug_main(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "main")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "main"


def test_slug_master(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "master")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "master"


def test_slug_feature_prefix_stripped(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "feature/cluster-x1")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "cluster-x1"


def test_slug_feat_prefix_stripped(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "feat/foo/bar")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "foo-bar"


def test_slug_bugfix_prefix_kept(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "bugfix/issue-42")
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "bugfix-issue-42"


def test_slug_detached_head(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    subprocess.run(["git", "checkout", "-q", sha], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "detached"


def test_slug_not_in_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert compute_branch_slug() == "unknown"


def test_slug_sanitize_unicode(tmp_path, monkeypatch):
    repo = _git_init(tmp_path)
    _git_checkout(repo, "实验/中文分支")
    monkeypatch.chdir(repo)
    slug = compute_branch_slug()
    assert "/" not in slug
    assert all(c.isascii() and (c.isalnum() or c in "-_") for c in slug)
```

- [ ] **Step 2: 运行确认失败**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py -v`
Expected: `ImportError: cannot import name 'compute_branch_slug' from 'step_id'` 或文件不存在

- [ ] **Step 3: 实现 step_id.py 的 compute_branch_slug**

```python
# plugins/kdev-memory/hooks/lib/step_id.py
"""kdev-memory v0.11 Step ID 加分支前缀机制。

提供：
- compute_branch_slug(): 把当前 git 分支名转成可放在文件名/Step ID 里的 slug
- read_counter(slug, state_dir): 读取分支独立计数器
- increment_counter(slug, state_dir): atomic 递增，返回新值（flock 保护）
- mint_next_step_id(state_dir): 一站式 = slug + atomic 递增 → "Step <slug>-<N>"

被 SKILL.md 引用：模型在写 Step 条目前调用 mint_next_step_id() 拿 ID。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional


# 这些前缀在 slug 里去掉（命名是冗余的）
STRIPPED_PREFIXES = ("feature/", "feat/")


def _git_query(*args: str) -> Optional[str]:
    try:
        r = subprocess.run(
            ["git", *args], capture_output=True, text=True, check=False,
        )
    except (OSError, FileNotFoundError):
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def _sanitize_slug(s: str) -> str:
    """把任意分支名转成 ASCII slug：非 [a-zA-Z0-9\\-_] 一律转 -，连续 - 合并，去首尾 -。"""
    s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unknown"


def compute_branch_slug() -> str:
    """当前 git 分支 → slug。

    - 不在 git 仓库 / git 缺失 → "unknown"
    - detached HEAD → "detached"
    - feature/X 或 feat/X → 去前缀
    - 含 / → 转 -
    - 含非 ASCII / 特殊字符 → sanitize
    """
    branch = _git_query("rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return "unknown"
    if branch == "HEAD":
        return "detached"
    for prefix in STRIPPED_PREFIXES:
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
            break
    return _sanitize_slug(branch)
```

- [ ] **Step 4: 运行测试，全 pass**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/step_id.py plugins/kdev-memory/tests/test_step_id.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): add compute_branch_slug for Step ID prefix (Q-003 task 1/12)"
```

---

## Task 2: 每分支独立计数器（flock atomic 递增）

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/step_id.py`
- Modify: `plugins/kdev-memory/tests/test_step_id.py`

**Counter 文件契约**：
- 路径：`<state_dir>/step-counter-<slug>.txt`
- 内容：纯整数 + trailing newline（`8\n`）
- 不存在 → 视为 0
- 用 POSIX `fcntl.flock(LOCK_EX)` 保护读改写；Windows 用 `msvcrt.locking` fallback
- 写入用 tmp + os.replace atomic rename，再用 flock 锁兜底并发

- [ ] **Step 1: 写失败测试（含并发）**

```python
# 追加到 plugins/kdev-memory/tests/test_step_id.py 末尾
import threading

from step_id import read_counter, increment_counter  # noqa: E402


def test_counter_missing_file_returns_zero(tmp_path):
    assert read_counter("main", tmp_path) == 0


def test_counter_existing_file(tmp_path):
    (tmp_path / "step-counter-main.txt").write_text("8\n", encoding="utf-8")
    assert read_counter("main", tmp_path) == 8


def test_increment_creates_file(tmp_path):
    n = increment_counter("cluster-x1", tmp_path)
    assert n == 1
    assert (tmp_path / "step-counter-cluster-x1.txt").read_text(encoding="utf-8").strip() == "1"


def test_increment_idempotent_growth(tmp_path):
    assert increment_counter("main", tmp_path) == 1
    assert increment_counter("main", tmp_path) == 2
    assert increment_counter("main", tmp_path) == 3


def test_increment_separate_slugs_independent(tmp_path):
    assert increment_counter("main", tmp_path) == 1
    assert increment_counter("cluster-x1", tmp_path) == 1   # 不互相影响
    assert increment_counter("main", tmp_path) == 2
    assert increment_counter("cluster-x1", tmp_path) == 2


def test_increment_concurrent_no_collision(tmp_path):
    """20 个线程并发 increment 同一 slug，结果必须是 {1, 2, ..., 20}（无重复、无丢失）。"""
    results: list[int] = []
    lock = threading.Lock()

    def worker():
        n = increment_counter("main", tmp_path)
        with lock:
            results.append(n)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == list(range(1, 21))


def test_increment_initial_value_seed(tmp_path):
    """预置 counter=8（模拟 main 分支历史 Step 1~8 切换），下一次应该返回 9。"""
    (tmp_path / "step-counter-main.txt").write_text("8\n", encoding="utf-8")
    assert increment_counter("main", tmp_path) == 9
```

- [ ] **Step 2: 运行确认失败**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py::test_counter_missing_file_returns_zero -v`
Expected: ImportError on `read_counter`

- [ ] **Step 3: 实现 read_counter + increment_counter**

```python
# 追加到 plugins/kdev-memory/hooks/lib/step_id.py
import os
import sys


def _counter_path(slug: str, state_dir: Path) -> Path:
    return state_dir / f"step-counter-{slug}.txt"


def read_counter(slug: str, state_dir: Path) -> int:
    """读 slug 的计数器值；不存在或损坏 → 0。"""
    p = _counter_path(slug, state_dir)
    if not p.is_file():
        return 0
    try:
        text = p.read_text(encoding="utf-8").strip()
        return int(text) if text else 0
    except (OSError, ValueError):
        return 0


def _flock_exclusive(fd: int) -> None:
    """跨平台 exclusive lock。POSIX: fcntl.flock；Windows: msvcrt.locking。"""
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX)


def _flock_release(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt
        try:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


def increment_counter(slug: str, state_dir: Path) -> int:
    """atomic 递增 slug 的计数器，返回新值。

    锁策略：在 counter 文件上做 LOCK_EX，临界区里 read-modify-write。
    并发安全：20 线程并发 increment 同一 slug 不丢失、不重复。
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _counter_path(slug, state_dir)
    # 用 "a+" 打开（不存在则创建），seek 到头读旧值，截断重写新值
    fd = os.open(str(p), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        _flock_exclusive(fd)
        os.lseek(fd, 0, os.SEEK_SET)
        raw = os.read(fd, 64).decode("utf-8", errors="replace").strip()
        try:
            cur = int(raw) if raw else 0
        except ValueError:
            cur = 0
        new = cur + 1
        os.lseek(fd, 0, os.SEEK_SET)
        os.ftruncate(fd, 0)
        os.write(fd, f"{new}\n".encode("utf-8"))
        os.fsync(fd)
        return new
    finally:
        _flock_release(fd)
        os.close(fd)
```

- [ ] **Step 4: 运行测试全 pass**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py -v`
Expected: 15 passed（8 slug + 7 counter）

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/step_id.py plugins/kdev-memory/tests/test_step_id.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): add per-branch atomic counter for Step ID (Q-003 task 2/12)"
```

---

## Task 3: `mint_next_step_id()` 一站式接口

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/step_id.py`
- Modify: `plugins/kdev-memory/tests/test_step_id.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 test_step_id.py
from step_id import mint_next_step_id  # noqa: E402


def test_mint_default_slug_from_git(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "main")
    state = repo / ".kdev" / "memory" / "state"
    monkeypatch.chdir(repo)
    assert mint_next_step_id(state) == "Step main-1"
    assert mint_next_step_id(state) == "Step main-2"


def test_mint_with_seeded_counter(tmp_path, monkeypatch):
    repo = _git_init(tmp_path, "main")
    state = repo / ".kdev" / "memory" / "state"
    state.mkdir(parents=True)
    (state / "step-counter-main.txt").write_text("8\n", encoding="utf-8")
    monkeypatch.chdir(repo)
    assert mint_next_step_id(state) == "Step main-9"


def test_mint_explicit_slug_overrides_git(tmp_path):
    state = tmp_path / "state"
    assert mint_next_step_id(state, slug="cluster-x1") == "Step cluster-x1-1"
    assert mint_next_step_id(state, slug="cluster-x1") == "Step cluster-x1-2"


def test_mint_concurrent_main_and_secondary_no_collision(tmp_path, monkeypatch):
    """模拟 main + secondary worktree 共享 state/，并发 mint 各自的 ID，无冲突。"""
    state = tmp_path / "state"
    main_ids: list[str] = []
    sec_ids: list[str] = []
    lock = threading.Lock()

    def main_worker():
        for _ in range(10):
            with lock:
                main_ids.append(mint_next_step_id(state, slug="main"))

    def sec_worker():
        for _ in range(10):
            with lock:
                sec_ids.append(mint_next_step_id(state, slug="cluster-x1"))

    t1 = threading.Thread(target=main_worker)
    t2 = threading.Thread(target=sec_worker)
    t1.start(); t2.start(); t1.join(); t2.join()
    assert main_ids == [f"Step main-{i}" for i in range(1, 11)]
    assert sec_ids == [f"Step cluster-x1-{i}" for i in range(1, 11)]
```

- [ ] **Step 2: 运行确认失败**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py::test_mint_default_slug_from_git -v`
Expected: ImportError on `mint_next_step_id`

- [ ] **Step 3: 实现 mint_next_step_id**

```python
# 追加到 plugins/kdev-memory/hooks/lib/step_id.py
def mint_next_step_id(state_dir: Path, slug: Optional[str] = None) -> str:
    """一站式：算 slug（如未传）→ atomic 递增 counter → 返回格式化的 Step ID。

    返回如 "Step main-9" / "Step cluster-x1-1"。
    """
    if slug is None:
        slug = compute_branch_slug()
    n = increment_counter(slug, state_dir)
    return f"Step {slug}-{n}"
```

- [ ] **Step 4: 运行测试全 pass**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_id.py -v`
Expected: 19 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/lib/step_id.py plugins/kdev-memory/tests/test_step_id.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): mint_next_step_id() one-stop interface (Q-003 task 3/12)"
```

---

## Task 4: 本地 main 计数器初始化 + 切换点注释

**目标**：让本仓库 `.kdev/memory/` 立即可用。一次性手动操作，不需要测试。

**Files:**
- Modify: `.kdev/memory/执行日志.md`（加切换点注释）
- Create: `.kdev/memory/state/step-counter-main.txt`（值=8）

- [ ] **Step 1: 在执行日志.md 第三段插入切换点注释**

定位：`.kdev/memory/执行日志.md` 第 1-9 行（header 段）。在 `---` 分隔线之前插入：

```markdown
<!-- step_id_prefix_since: 2026-05-28 — 从该日起新建 Step 用 `Step <branch-slug>-N` 格式（详见 Q-003）。
     历史 Step 1~8 保持无前缀格式不动以保护既有锚点链接。 -->
```

具体 Edit:
```
old_string: "格式参考：`plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md` §3\n\n---"
new_string: "格式参考：`plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md` §3\n\n<!-- step_id_prefix_since: 2026-05-28 — 从该日起新建 Step 用 `Step <branch-slug>-N` 格式（详见 [Q-003](决策日志.md#q-003-secondary-worktree-symlink-架构下-step-id-加分支前缀)）。\n     历史 Step 1~8 保持无前缀格式不动以保护既有锚点链接。\n     main 分支计数器初始化为 8，下一条新 Step = `Step main-9`。 -->\n\n---"
```

- [ ] **Step 2: 创建 main 分支计数器文件**

```bash
mkdir -p .kdev/memory/state
echo "8" > .kdev/memory/state/step-counter-main.txt
```

- [ ] **Step 3: 用 mint_next_step_id 验证下一个 ID = Step main-9**

```bash
python -c "
import sys
sys.path.insert(0, 'plugins/kdev-memory/hooks/lib')
from step_id import mint_next_step_id
from pathlib import Path
# DRY-RUN: 用临时 state 验证逻辑，不污染真实计数器
import tempfile, shutil
with tempfile.TemporaryDirectory() as td:
    shutil.copy('.kdev/memory/state/step-counter-main.txt', td)
    print(mint_next_step_id(Path(td), slug='main'))
"
```
Expected: `Step main-9`

- [ ] **Step 4: Commit**

```bash
git add .kdev/memory/执行日志.md .kdev/memory/state/step-counter-main.txt
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore(kdev-memory): seed main step counter at 8 + add prefix_since marker (Q-003 task 4/12)"
```

注：`.kdev/` 不在 git track 默认范围（[.gitignore](../../../.gitignore)），这次 commit 是 opt-in 性质——`.kdev/memory/state/step-counter-main.txt` 是新计数器源头，值得 track。如本仓库 `.kdev/` 完全不入库，则这一步只在本机生效，但 plugin 代码逻辑不依赖这次 commit。

**子决策（提交前确认）**：是否把 `.kdev/memory/state/step-counter-*.txt` 加进 `.gitignore` 让它纯本机？默认建议入库（多机/CI 同步友好；冲突手动 max() 即可），但用户可选。

---

## Task 5: SessionStart brief 展示「本次 Step 前缀」

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-start-brief.py`
- Create: `plugins/kdev-memory/tests/test_session_start_brief_prefix.py`

- [ ] **Step 1: 写失败测试**

```python
# plugins/kdev-memory/tests/test_session_start_brief_prefix.py
"""test session-start-brief 注入 Step ID 前缀提示。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-start-brief.py"


def _init_repo_with_kdev(tmp_path: Path, branch: str = "main") -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", branch], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    (repo / ".kdev" / "memory").mkdir(parents=True)
    (repo / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    return repo


def _run_hook(repo: Path, source: str = "startup") -> dict:
    payload = json.dumps({"source": source})
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo), input=payload, capture_output=True, text=True,
    )
    return json.loads(r.stdout) if r.stdout.strip() else {}


def test_brief_shows_main_prefix(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "本次 Step ID 前缀" in ctx
    assert "main-" in ctx


def test_brief_shows_feature_branch_prefix(tmp_path):
    repo = _init_repo_with_kdev(tmp_path, "main")
    subprocess.run(["git", "checkout", "-q", "-b", "feature/cluster-x1"], cwd=repo, check=True)
    out = _run_hook(repo)
    ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
    assert "cluster-x1-" in ctx
```

- [ ] **Step 2: 运行确认失败**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_session_start_brief_prefix.py -v`
Expected: AssertionError —— brief 当前不含 "Step ID 前缀" 字样

- [ ] **Step 3: 修改 session-start-brief.py**

```python
# session-start-brief.py 第 33 行附近 import 块（已有 from worktree_link import worktree_link_kdev）
# 追加:
from step_id import compute_branch_slug  # noqa: E402
```

```python
# session-start-brief.py 第 302-305 行附近 prog 构建（startup mode）
# old:
prog = ["📊 **今日进度**：", f"- 执行日志：{log_today}", f"- 每日汇总：{summary_today_status}"]
if git_branch:
    prog.append(f"- 当前分支：{git_branch}")
parts.append("\n".join(prog))

# new:
prog = ["📊 **今日进度**：", f"- 执行日志：{log_today}", f"- 每日汇总：{summary_today_status}"]
if git_branch:
    prog.append(f"- 当前分支：{git_branch}")
    try:
        slug = compute_branch_slug()
    except Exception:
        slug = "unknown"
    prog.append(f"- 本次 Step ID 前缀：`{slug}-`（下一个 Step 形如 `Step {slug}-N`）")
parts.append("\n".join(prog))
```

- [ ] **Step 4: 运行测试全 pass**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_session_start_brief_prefix.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-memory/hooks/session-start-brief.py plugins/kdev-memory/tests/test_session_start_brief_prefix.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): SessionStart brief shows Step ID prefix (Q-003 task 5/12)"
```

---

## Task 6: step_completeness.py regex 对前缀 ID 的兼容性验证

**Files:**
- Modify: `plugins/kdev-memory/tests/test_step_completeness.py`（若不存在则新建）

step_completeness.py 第 78-82 行的 regex `^##\s+(Step\s+[\w\-\.]+)(?:\s*[:：]\s*(.+)|\s+(.+))?$` 已经支持 `Step main-9` / `Step cluster-x1-1`（comment 已注明）。本 task 只补**显式回归测试**防止未来误改 regex 时破坏前缀解析。

- [ ] **Step 1: 检查是否已有 test_step_completeness.py**

Run: `ls plugins/kdev-memory/tests/test_step_completeness.py 2>/dev/null || echo "MISSING"`

- 若 `MISSING`：新建文件并写下面所有测试
- 若存在：仅追加下面的 prefix 兼容测试

- [ ] **Step 2: 写测试**

```python
# plugins/kdev-memory/tests/test_step_completeness.py 追加（或新建文件含 imports）
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from step_completeness import parse_steps  # noqa: E402


def test_parse_prefix_main_step():
    log = """# 执行日志
## Step main-9: 加分支前缀机制
日期：2026-05-28
"""
    steps = parse_steps(log)
    assert len(steps) == 1
    assert steps[0]["label"] == "Step main-9"
    assert steps[0]["title"] == "加分支前缀机制"
    assert steps[0]["date"] == "2026-05-28"


def test_parse_prefix_cluster_step():
    log = """# 执行日志
## Step cluster-x1-1: writing-plans 输出 X1 plan
日期：2026-05-27
"""
    steps = parse_steps(log)
    assert len(steps) == 1
    assert steps[0]["label"] == "Step cluster-x1-1"


def test_parse_mixed_legacy_and_prefix():
    """历史无前缀 + 新带前缀混合解析。"""
    log = """# 执行日志
## Step 1: 历史无前缀（2026-05-24）
日期：2026-05-24

## Step main-9: 新带前缀
日期：2026-05-28
"""
    steps = parse_steps(log)
    assert [s["label"] for s in steps] == ["Step 1", "Step main-9"]
```

- [ ] **Step 3: 运行确认 pass（regex 已支持，应直接绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_completeness.py -v -k "prefix or mixed"`
Expected: 3 passed

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-memory/tests/test_step_completeness.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "test(kdev-memory): regress-guard prefix Step ID parsing in step_completeness (Q-003 task 6/12)"
```

---

## Task 7: SKILL.md 教模型新 ID 格式

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`

- [ ] **Step 1: 读当前 SKILL.md 找需要改的位置**

Run: `grep -n "全局递增\|Step N\|## Step \|Q-001" plugins/kdev-memory/skills/kdev-memory/SKILL.md`

定位三处：
- (a) §"Step 编号策略" 段（约 line 122-126，提到 Q-001 全局递增）→ 加 v0.11 新格式说明
- (b) 表格里"Step N"列 → 改"Step <slug>-N"
- (c) 加新章节「§N. 多 worktree 并发场景：Step ID 加分支前缀（v0.11+）」

- [ ] **Step 2: Edit (a) — Q-001 段补 v0.11 升级说明**

找当前文本：
```
**初始化时必须问用户一个决策（走 Q-001）**：Step 编号用全局递增还是迭代内递增？默认倾向全局递增。
```

改为：
```
**初始化时必须问用户一个决策（走 Q-001）**：Step 编号用全局递增还是迭代内递增？默认倾向全局递增。

**v0.11+ 升级**：全局递增的基础上**加分支前缀**——`Step <branch-slug>-N` 格式。原因：多 worktree symlink 共享 `.kdev/` 架构下，两个 session 并发独立递增会产生 ID 冲突。新格式让每个分支有独立计数器，互不干扰。详见 §N「多 worktree 并发场景」。
```

- [ ] **Step 3: Edit (b) — 表格 "Step N" → "Step <slug>-N"**

找类似：`| 每步/每里程碑完成 | 执行日志.md（双评分） | Step N | §3 |`
改为：`| 每步/每里程碑完成 | 执行日志.md（双评分） | Step <slug>-N | §3 |`

- [ ] **Step 4: Edit (c) — 新增章节**

在 SKILL.md 末尾「§归档」之前（或最合适位置）插入：

```markdown
## §N. 多 worktree 并发场景：Step ID 加分支前缀（v0.11+）

### 何时触发

任何会让多个 Claude session 共享同一份 `.kdev/memory/` 的场景：
- secondary worktree（通过 [worktree_link.py](../../hooks/lib/worktree_link.py) 自动 symlink）
- 多终端开同一仓库
- 主仓库 + 镜像/挂载点同时 Claude 会话

### 新 ID 格式

`Step <branch-slug>-N`，例：
- `Step main-9`（主分支第 9 条）
- `Step cluster-x1-1`（feature/cluster-x1 分支第 1 条）
- `Step bugfix-issue-42-3`（bugfix/issue-42 分支第 3 条）

### Slug 规则（由 [step_id.compute_branch_slug()](../../hooks/lib/step_id.py) 实现，不手算）

- `main` / `master` → 原样
- `feature/X` / `feat/X` → 去前缀
- 其他 `A/B` → `A-B`
- 非 ASCII / 特殊字符 → sanitize 成 `[a-zA-Z0-9\-_]+`
- 不在 git → `unknown`
- detached HEAD → `detached`

### 智能体落 Step 时的标准流程

```python
import sys
sys.path.insert(0, "plugins/kdev-memory/hooks/lib")
from step_id import mint_next_step_id
from pathlib import Path
step_id = mint_next_step_id(Path(".kdev/memory/state"))
# step_id = "Step main-9"
```

然后用这个 ID 作为 Step 条目的标题：
```markdown
## Step main-9: 实现 step_id.py
triggers: [...]
日期：2026-05-28
...
```

智能体可以直接读 [step_id.py](../../hooks/lib/step_id.py) 实现细节；本节只规范"用哪个接口"。

### 历史兼容

`step_id_prefix_since: <date>` 是 `执行日志.md` 第二段后面的注释，标识切换时点。该日期之前的 Step 保持无前缀格式（`Step 1` ~ `Step 8` 等）；之后的全部带前缀。SessionStart brief 显示「本次 Step ID 前缀：`<slug>-`」帮助智能体确认。

### 子文件位置

- 计数器：`.kdev/memory/state/step-counter-<slug>.txt`，纯整数
- 切换点注释：在 `执行日志.md` header 段（搜索 `step_id_prefix_since`）

### main 分支特殊性

main 分支的计数器初始化为「历史 Step 1~8 的最大编号」（本仓库为 8），让 main 上下一条新 Step = `Step main-9`，保持时间线连贯。**新建分支的计数器从 0 起**，下一条 = `Step <slug>-1`。
```

- [ ] **Step 5: 跑 skill-creator 验证 SKILL.md 没破坏 YAML frontmatter**

Run: `python -c "
import yaml
with open('plugins/kdev-memory/skills/kdev-memory/SKILL.md') as f:
    raw = f.read()
fm = raw.split('---', 2)[1]
yaml.safe_load(fm)
print('OK')
"`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/SKILL.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): SKILL.md teaches Step ID branch prefix (Q-003 task 7/12)"
```

---

## Task 8: 六类记录-schema.md 更新 Step 示例

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`

- [ ] **Step 1: 定位需要改的 Step 示例**

Run: `grep -n "## Step [0-9]\|current_step" plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`

至少 line 104 `## Step 7: 实现 token 采集器核心循环` 和 line 401 `current_step` 字段说明。

- [ ] **Step 2: 把所有 `## Step N` 示例改成 `## Step <slug>-N` 形式（仅示例，不改字段定义）**

- 第 104 行 `## Step 7: 实现 token 采集器核心循环` → `## Step main-7: 实现 token 采集器核心循环`
- 第 198 行 §`Step 状态字段` 不动（讨论的是 status 字段，跟 ID 格式无关）
- 第 222 行 §`Step 粒度` 不动

- [ ] **Step 3: 在 §3 Step 段末加一段「v0.11+ ID 格式」说明**

```markdown
### v0.11+ ID 格式：`Step <branch-slug>-N`

为支持多 worktree 并发场景，Step ID 从 v0.11 起加分支前缀。详见 [SKILL.md §N 多 worktree 并发场景](../SKILL.md)。

历史 Step（v0.11 前）保留 `Step N` 无前缀格式，由 `执行日志.md` 顶部 `<!-- step_id_prefix_since: <date> -->` 注释标识切换时点。
```

- [ ] **Step 4: 更新 §`current_step` frontmatter 字段说明**

第 401 行附近：
```
| `current_step` | 整数 | 最近完成的 Step 编号（对齐执行日志.md 里的 `## Step N`） |
```
改为：
```
| `current_step` | 字符串 | 最近完成的 Step 标识（v0.11 前是整数 `8`；v0.11+ 是带前缀字符串如 `main-9` / `cluster-x1-1`） |
```

⚠️ **注意**：这是 schema 升级——之前是 `int`，现在是 `str`。检查 [frontmatter.py](../../hooks/lib/frontmatter.py) `read_state_field("current_step")` 调用方是否假设 int；不假设的话改 schema 即可。

- [ ] **Step 5: 验证 frontmatter.py 没把 current_step 当 int 用**

Run: `grep -n "current_step" plugins/kdev-memory/hooks/lib/*.py plugins/kdev-memory/hooks/*.py`
Expected: 全是 string 形式使用（如拼接到 brief 文本）；若发现 `int(state_step)` 之类需要单独修，但目前看 brief 是字符串拼接，应该不会有问题。

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): six-record schema doc updated for prefixed Step ID (Q-003 task 8/12)"
```

---

## Task 8.5: README.md 加「v0.11 分支前缀」一节

**Files:**
- Modify: `plugins/kdev-memory/README.md`

- [ ] **Step 1: 找到 README 的"Step 编号"或"使用"段**

Run: `grep -n "Step\|## " plugins/kdev-memory/README.md | head -30`

- [ ] **Step 2: 在合适位置加新段（推荐在"使用"主段下）**

```markdown
### v0.11+ 多 worktree 并发：Step ID 加分支前缀

为支持 secondary worktree 通过 symlink 共享 `.kdev/` 的并发场景，Step ID 从 v0.11 起加分支前缀：

```
## Step main-9: 主分支第 9 条
## Step cluster-x1-1: feature/cluster-x1 分支第 1 条
```

智能体落 Step 前调用：

```python
import sys; sys.path.insert(0, "plugins/kdev-memory/hooks/lib")
from step_id import mint_next_step_id
from pathlib import Path
print(mint_next_step_id(Path(".kdev/memory/state")))  # → "Step main-9"
```

历史 Step 不迁移，由 `执行日志.md` 头部 `<!-- step_id_prefix_since: <date> -->` 注释标识切换点。详见 [SKILL.md](skills/kdev-memory/SKILL.md) §「多 worktree 并发场景」和 [Q-003 决策](../../.kdev/memory/决策日志.md)。
```

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-memory/README.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): README adds v0.11 branch prefix section (Q-003 task 8.5/12)"
```

---

## Task 9: triggers-写法.md 示例对齐

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/triggers-写法.md`

- [ ] **Step 1: 改两处示例**

Run: `grep -n "## Step\|新 Step" plugins/kdev-memory/skills/kdev-memory/references/triggers-写法.md`

第 29 行：`| 新 Step（完成时顺手） | 在 \`## Step N: 标题\` 下一行加 \`triggers: [...]\` |`
→ `| 新 Step（完成时顺手） | 在 \`## Step <slug>-N: 标题\` 下一行加 \`triggers: [...]\` |`

第 44 行：`## Step 23: 实现采集器核心循环`
→ `## Step main-23: 实现采集器核心循环`

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-memory/skills/kdev-memory/references/triggers-写法.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): triggers-写法.md example uses prefixed Step ID (Q-003 task 9/12)"
```

---

## Task 10: kdev-agents 项目 CLAUDE.md 接口契约同步

**Files:**
- Modify: `CLAUDE.md`（仓库根）

CLAUDE.md 当前「智能体自动记录规则」段说接口在 skill 里、本段不复述。所以**无需大改**，只在「关键授权」段下方加一句新格式提醒。

- [ ] **Step 1: 定位「关键授权」段**

Run: `grep -n "关键授权\|current_step" CLAUDE.md`

- [ ] **Step 2: 在「关键授权」段末尾加一条**

找：
```
- 每完成 Step 要顺手更新 `.kdev/memory/当前状态.md` 的 frontmatter（`current_step` + `last_updated`），不要攒到每日汇总时才改
```

改为：
```
- 每完成 Step 要顺手更新 `.kdev/memory/当前状态.md` 的 frontmatter（`current_step` + `last_updated`），不要攒到每日汇总时才改
- **v0.11+ Step ID 加分支前缀**：新建 Step 用 `Step <branch-slug>-N` 格式（main 上是 `Step main-N`），通过 `step_id.mint_next_step_id()` 自动算。具体规则见 skill 里的「多 worktree 并发场景」段。
```

- [ ] **Step 3: 跑 CLAUDE.md drift 检查（kdev-memory 已有 hook）**

Run: `python plugins/kdev-memory/hooks/lib/claude_md_lint.py plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md CLAUDE.md`
Expected: 无 drift，或仅 INFO 级差异。

如果模板文件也需要更新以反映 v0.11 接口，编辑 `plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md` 加同样的一句。

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-agents): CLAUDE.md syncs kdev-memory v0.11 prefixed Step ID rule (Q-003 task 10/12)"
```

---

## Task 11: kdev-memory plugin 版本 bump + CHANGELOG

**Files:**
- Modify: `plugins/kdev-memory/CHANGELOG.md`

- [ ] **Step 1: 在 CHANGELOG 顶部加 0.11.0 条目**

找：
```markdown
# kdev-memory CHANGELOG

## [0.10.1] — 2026-05-27
```

在 `# kdev-memory CHANGELOG` 下一行 + `## [0.10.1]` 上一行 insert：

```markdown
## [0.11.0] — 2026-05-28

**Step ID 加分支前缀：解决 secondary worktree symlink 共享 `.kdev/` 架构下并发 ID 冲突。**

经 Q-003 决策（[决策日志.md](../../.kdev/memory/决策日志.md)）+ 12 任务 plan 实施。新增 `hooks/lib/step_id.py`（slug + counter + mint 一站式接口），SessionStart brief 展示当前分支前缀，SKILL.md / references 全面对齐。

### ✨ 新增功能

- **`hooks/lib/step_id.py`** — slug + counter + mint 一站式接口：
  - `compute_branch_slug()`：git rev-parse → 干净的 ASCII slug（`feature/X` / `feat/X` 去前缀；非法字符 sanitize；detached HEAD → `detached`；非 git → `unknown`）
  - `read_counter(slug, state_dir)` / `increment_counter(slug, state_dir)`：每分支独立计数器，flock 保护 atomic 递增（POSIX `fcntl` / Windows `msvcrt`），并发 20 线程零冲突
  - `mint_next_step_id(state_dir, slug=None)` → `"Step <slug>-<N>"`
- **`SessionStart brief`** 在「今日进度」段加 `- 本次 Step ID 前缀：\`<slug>-\``，让智能体新会话立刻知道用什么前缀
- **`step_completeness` regex 兼容性回归测试**：显式覆盖 `Step main-9` / `Step cluster-x1-1` / 历史无前缀混合解析

### 🔄 变更

- **Step ID 格式**：从 `Step N` 全局递增 → `Step <branch-slug>-N` 每分支独立递增
- **`当前状态.md` frontmatter `current_step` 字段类型**：int → string（如 `main-9`）。读取方都是字符串拼接，无 breaking change
- **SKILL.md / 六类记录-schema.md / triggers-写法.md** 全面更新示例 + 新增「多 worktree 并发场景」一节

### 🔧 兼容性

- **历史 Step 1~8 不迁移**：保持无前缀格式不动以保护既有锚点链接；`执行日志.md` 头部加 `<!-- step_id_prefix_since: <date> -->` 注释标识切换点
- **main 分支计数器初始化为 max(历史 Step 编号)**（本仓库为 8），下一条 = `Step main-9`，保持时间线连贯
- **新建分支** 计数器从 0 起，下一条 = `Step <slug>-1`

### 📋 升级指南

升级到 v0.11.0 的项目需要执行一次性初始化：
1. 在 `执行日志.md` header 段加 `<!-- step_id_prefix_since: YYYY-MM-DD -->`
2. 计算历史最大 Step 编号 N，创建 `.kdev/memory/state/step-counter-<main-slug>.txt` 内容为 `N`
3. CLAUDE.md 添加 v0.11 新格式提醒（见模板 [`初始化-claude-md-模板.md`](skills/kdev-memory/references/初始化-claude-md-模板.md)）

### ✅ 测试

- `tests/test_step_id.py`：19 用例（8 slug + 7 counter + 4 mint）
- `tests/test_session_start_brief_prefix.py`：2 用例
- `tests/test_step_completeness.py`：+3 prefix 兼容回归

---

```

- [ ] **Step 2: 跑完整测试套**

Run: `cd plugins/kdev-memory && python -m pytest tests/ -v`
Expected: 全 pass（含 test_worktree_link.py 既有 + 本 plan 新增的所有测试）

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-memory/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-memory): v0.11.0 — Step ID branch prefix (Q-003 task 11/12)"
```

---

## Task 12: e2e 烟测 + 落 Step 记录到本项目执行日志

**Files:**
- Modify: `.kdev/memory/执行日志.md`（写真实的 `Step main-9: Q-003 落地`）
- Modify: `.kdev/memory/当前状态.md`（更新 `current_step` 和 `last_updated`）

- [ ] **Step 1: e2e 烟测——本仓库当前实际跑一次 mint**

Run:
```bash
python -c "
import sys
sys.path.insert(0, 'plugins/kdev-memory/hooks/lib')
from step_id import mint_next_step_id
from pathlib import Path
print(mint_next_step_id(Path('.kdev/memory/state')))
"
```
Expected: `Step main-9`
副作用：`.kdev/memory/state/step-counter-main.txt` 从 `8` → `9`

- [ ] **Step 2: 用这个 ID 落一条 Step 到执行日志.md**

Edit 在 `## Step 8` 末尾后追加：

```markdown
## Step main-9: Q-003 落地 — Step ID 加分支前缀（kdev-memory v0.11.0）
triggers: ["Q-003", "Step ID 加前缀", "kdev-memory v0.11", "分支前缀", "worktree symlink ID 冲突"]
日期：2026-05-28
about: project

### 执行
- 实施 [docs/skills/kdev-memory/plans/2026-05-28-step-id-prefix-branch.md](../../docs/skills/kdev-memory/plans/2026-05-28-step-id-prefix-branch.md) 12 任务（slug + counter + mint + brief + SKILL.md/references + CLAUDE.md + CHANGELOG）
- 新增 `step_id.py` 库（slug + flock 保护 atomic counter + mint 一站式）
- 加 19 + 2 + 3 = 24 个测试用例（含 20 线程并发 mint 零冲突）
- 本仓库 main 计数器 seed 为 8，下一条新 Step = `Step main-9` = 本条
- kdev-memory 插件 bump 到 v0.11.0

### 模型自评
- 顺畅度：自评 4/5
- 本步最值得扣分项：（待 implementer 填写）

### 用户评分
- 完成时间：—
- 顺畅度：—/5
- 评分差异分析：—

> 半残销账：用户 2026-05-27 明确"后面我不再评分"（Q-002），不主动追问
```

- [ ] **Step 3: 更新当前状态.md frontmatter**

Edit `.kdev/memory/当前状态.md`：
```yaml
current_step: main-9     # 从 "Step 8" 改
last_updated: 2026-05-28
```

- [ ] **Step 4: 验证 SessionStart brief 能正确探测**

Run:
```bash
echo '{"source":"startup"}' | python plugins/kdev-memory/hooks/session-start-brief.py | python -m json.tool | head -40
```
Expected stdout 含：
- `- 当前分支：main`
- `- 本次 Step ID 前缀：\`main-\``
- `current_step: main-9`

- [ ] **Step 5: Commit**

```bash
git add .kdev/memory/执行日志.md .kdev/memory/当前状态.md .kdev/memory/state/step-counter-main.txt
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(.kdev): land Step main-9 (Q-003 task 12/12 e2e smoke)"
```

---

## 收尾验证清单

12 个 commit 全部上 main 后，跑下面 4 条快速验证（人工目测）：

```bash
# 1. 全测试套
cd plugins/kdev-memory && python -m pytest tests/ -v

# 2. mint 烟测
python -c "
import sys; sys.path.insert(0, 'plugins/kdev-memory/hooks/lib')
from step_id import compute_branch_slug, mint_next_step_id
from pathlib import Path
print('slug:', compute_branch_slug())
import tempfile
with tempfile.TemporaryDirectory() as td:
    print('mint:', mint_next_step_id(Path(td)))
"
# Expected: slug: main / mint: Step main-1

# 3. brief 烟测
echo '{"source":"startup"}' | python plugins/kdev-memory/hooks/session-start-brief.py | grep "Step ID 前缀"
# Expected: 一行含 "本次 Step ID 前缀：`main-`"

# 4. drift check
python plugins/kdev-memory/hooks/lib/claude_md_lint.py plugins/kdev-memory/skills/kdev-memory/references/初始化-claude-md-模板.md CLAUDE.md
# Expected: 无 drift
```

---

## 子决策需要在实施前向用户确认

Q-003 列了 3 个 plan 阶段待定，本 plan 给出推荐默认，**实施前请用户拍板**：

1. **计数器单文件 vs 每分支独立文件** → 推荐**每分支独立**（避免锁竞争），已在 plan 里采用
2. **main 分支 slug** → 推荐 **`main`**（不强制映射 master），已在 plan 里采用；如本仓库实际是 master，slug 也会自动是 `master`
3. **历史 Step 1~8 处理** → 推荐**新旧共存**（无前缀 1~8 + 带前缀 `main-9` 起步），已在 plan 里采用；如用户要求迁移补前缀，需新增 Task 13 写迁移脚本（建议不做）

另：
- 是否把 `.kdev/memory/state/step-counter-*.txt` 加进 git track（让多机/CI 共享计数器）？默认建议**入库**（冲突手动 max() 合并），但 `.kdev/` 当前不在 git track 范围，需要走 `KDEV_GIT_TRACK=1` opt-in 或单独 force-add。**用户拍板**。

---

## 风险登记

| 风险 | 概率 | 后果 | 缓解 |
|------|------|------|------|
| Windows flock fallback `msvcrt.locking` 在某些 NTFS 场景失败 | 中 | 计数器并发损坏 | 限制单文件 1 字节锁；CI 验证 |
| 智能体 forget 调 mint_next_step_id 仍手算 ID | 中 | 偶发 ID 冲突 / 格式不一致 | SKILL.md 反复强调；SessionStart brief 提醒；step_completeness 加 lint 检测格式偏移（未来加） |
| `step_id_prefix_since` 注释被误删导致历史定位丢失 | 低 | 仅影响文档可读性 | 注释里写明用途；CLAUDE.md 写明 |
| 模板 `初始化-claude-md-模板.md` 没同步导致 drift check 永远红 | 中 | brief 噪声 | Task 10 Step 3 要求同步更新模板 |

## 范围外（已知未解决问题）

**File-level write race**：两个 session 通过 Claude Edit 工具并发改 `执行日志.md` 时，后写的会覆盖先写的——Edit 是 read-whole-file → modify → write-whole-file，不是 append。本 plan 解决的是 **ID 冲突**（两 session 同时铸 `Step 7`），不解决 **file 内容互相覆盖**。

实际影响：两 session 同时落 Step 的概率本来就低（每条 Step 是一次性写入，模型完成 Step 总结后才动 Edit）；但若发生，**先写的 Step 条目会丢失**。

延迟到后续 R-NNN 解决，可选方向：
- 把 Step 落盘从「Edit 工具改 md」改成「shell append 命令」走 `O_APPEND`（POSIX 原子小于 PIPE_BUF=4KB 的 append）
- 或加 git pre-commit hook 检测 `执行日志.md` 冲突回滚到 working copy
- 或要求 secondary worktree 落 Step 必须先 fetch 主 worktree 当前 .kdev/ 状态（symlink 已经做到了，但 Edit 工具的 file-cache 可能跟 inode 实际状态不一致）

本 plan 不展开。
