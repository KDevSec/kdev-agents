"""kdev-memory v0.11 Step ID 加分支前缀机制。

提供：
- compute_branch_slug(): git 当前分支名 → 可放在文件名/Step ID 里的 ASCII slug
- read_counter(slug, state_dir): 读取分支独立计数器
- increment_counter(slug, state_dir): flock 保护 atomic 递增，返回新值
- mint_next_step_id(state_dir, slug=None): 一站式 slug + 递增 → "Step <slug>-<N>"

被 SKILL.md 引用：模型在写 Step 条目前调用 mint_next_step_id() 拿 ID。
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional


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
    """非 [a-zA-Z0-9\\-_] 一律转 -，连续 - 合并，去首尾 -。空字符串 fallback 'unknown'。"""
    s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "unknown"


def sanitize_slug(s: str) -> str:
    """Public wrapper for slug sanitization (reused by scope.resolve_step_slug)."""
    return _sanitize_slug(s)


def compute_branch_slug() -> str:
    """当前 git 分支 → slug。

    无 commit 的新仓库（git init 后没 commit）`rev-parse --abbrev-ref HEAD` 退出码 128，
    fallback 到读 `.git/HEAD` 的 `ref: refs/heads/<name>` 行（即便没 commit 也存在）。
    见 R-003。
    """
    branch = _git_query("rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        branch = _branch_from_head_file()
        if branch is None:
            return "unknown"
    if branch == "HEAD":
        return "detached"
    for prefix in STRIPPED_PREFIXES:
        if branch.startswith(prefix):
            branch = branch[len(prefix):]
            break
    return _sanitize_slug(branch)


def _branch_from_head_file() -> Optional[str]:
    """R-003 兜底：读 .git/HEAD 的 `ref: refs/heads/<name>` 拿分支名。"""
    git_dir = _git_query("rev-parse", "--git-dir")
    if not git_dir:
        return None
    head_file = Path(git_dir) / "HEAD"
    if not head_file.is_file():
        return None
    try:
        content = head_file.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    prefix = "ref: refs/heads/"
    if content.startswith(prefix):
        return content[len(prefix):]
    return None


# ── Task 2: per-branch atomic counter ────────────────────────────────────────


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


# ── Task 3: mint_next_step_id one-stop interface ──────────────────────────────


def mint_next_step_id(state_dir: Path, slug: Optional[str] = None) -> str:
    """一站式：算 slug（如未传）→ atomic 递增 counter → 返回格式化的 Step ID。

    返回如 "Step main-9" / "Step cluster-x1-1"。
    """
    if slug is None:
        slug = compute_branch_slug()
    n = increment_counter(slug, state_dir)
    return f"Step {slug}-{n}"
