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


def test_slug_no_commit_repo(tmp_path, monkeypatch):
    """R-003: git init -b main 但无 commit 时，rev-parse 失败，
    应读 .git/HEAD 兜底拿到 main 而非 fallback unknown。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "main"


def test_slug_no_commit_repo_feature_branch(tmp_path, monkeypatch):
    """R-003: 无 commit 仓库 + 非 main 默认分支名，HEAD ref 解析应正确去 feature/ 前缀。"""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feature/draft"], cwd=repo, check=True)
    monkeypatch.chdir(repo)
    assert compute_branch_slug() == "draft"


# ── Task 2: per-branch atomic counter ────────────────────────────────────────
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
    assert increment_counter("cluster-x1", tmp_path) == 1
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


# ── Task 3: mint_next_step_id one-stop interface ──────────────────────────────

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


# ── P-C2 Group A: timestamp-based record ID primitive ─────────────────────────

import datetime

from step_id import _now_stamp, _who_suffix  # noqa: E402


def test_now_stamp_format():
    assert _now_stamp(when=datetime.datetime(2026, 6, 13, 10, 14, 32)) == "20260613-101432"


def test_who_suffix_from_email(monkeypatch):
    monkeypatch.setattr("step_id._git_query", lambda *a: "ly1989abc@126.com")
    assert _who_suffix() == "ly1989abc"


def test_who_suffix_no_git_returns_empty(monkeypatch):
    monkeypatch.setattr("step_id._git_query", lambda *a: None)
    assert _who_suffix() == ""   # NEVER 'None'


def test_who_suffix_sanitizes(monkeypatch):
    monkeypatch.setattr("step_id._git_query", lambda *a: "Ly.Dev+test@x.com")
    assert _who_suffix() == "Ly-Dev-test"


# ── _dup_index ────────────────────────────────────────────────────────────────

from step_id import _dup_index  # noqa: E402


def test_dup_index_first_is_zero(tmp_path):
    assert _dup_index("Step", "20260613-101432-ly", tmp_path) == 0


def test_dup_index_increments_on_same_base(tmp_path):
    assert _dup_index("Step", "20260613-101432-ly", tmp_path) == 0
    assert _dup_index("Step", "20260613-101432-ly", tmp_path) == 1
    assert _dup_index("Step", "20260613-101432-ly", tmp_path) == 2


def test_dup_index_independent_per_base(tmp_path):
    assert _dup_index("Step", "20260613-101432-ly", tmp_path) == 0
    assert _dup_index("Step", "20260613-101433-ly", tmp_path) == 0


def test_dup_index_concurrent_no_collision(tmp_path):
    import threading
    out = []
    def worker(): out.append(_dup_index("Step", "20260613-101432-ly", tmp_path))
    ts = [threading.Thread(target=worker) for _ in range(20)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert sorted(out) == list(range(20))


# ── mint_record_id ────────────────────────────────────────────────────────────

from step_id import mint_record_id  # noqa: E402


def test_mint_step_with_who(tmp_path, monkeypatch):
    monkeypatch.setattr("step_id._who_suffix", lambda: "ly1989abc")
    assert mint_record_id("Step", tmp_path, when=datetime.datetime(2026,6,13,10,14,32)) == "Step 20260613-101432-ly1989abc"


def test_mint_q_same_grammar(tmp_path, monkeypatch):
    monkeypatch.setattr("step_id._who_suffix", lambda: "ly1989abc")
    assert mint_record_id("Q", tmp_path, when=datetime.datetime(2026,6,13,10,14,32)) == "Q 20260613-101432-ly1989abc"


def test_mint_no_git_omits_suffix(tmp_path, monkeypatch):
    monkeypatch.setattr("step_id._who_suffix", lambda: "")
    assert mint_record_id("Step", tmp_path, when=datetime.datetime(2026,6,13,10,14,32)) == "Step 20260613-101432"


def test_mint_same_second_appends_dup(tmp_path, monkeypatch):
    monkeypatch.setattr("step_id._who_suffix", lambda: "ly")
    w = datetime.datetime(2026,6,13,10,14,32)
    assert mint_record_id("Step", tmp_path, when=w) == "Step 20260613-101432-ly"
    assert mint_record_id("Step", tmp_path, when=w) == "Step 20260613-101432-ly.1"


def test_mint_unknown_type_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        mint_record_id("X", tmp_path)


# ── parse_record_id ────────────────────────────────────────────────────────────

from step_id import parse_record_id  # noqa: E402


def test_parse_old_step_slug_n():
    assert parse_record_id("Step main-87") == {"type": "Step", "id": "main-87", "scheme": "legacy"}


def test_parse_old_q_n():
    assert parse_record_id("Q-018") == {"type": "Q", "id": "018", "scheme": "legacy"}


def test_parse_new_timestamp_with_who():
    assert parse_record_id("Step 20260613-101432-ly1989abc") == {"type": "Step", "id": "20260613-101432-ly1989abc", "scheme": "timestamp"}


def test_parse_new_timestamp_dup():
    assert parse_record_id("Q 20260613-101432-ly.2") == {"type": "Q", "id": "20260613-101432-ly.2", "scheme": "timestamp"}


def test_parse_new_no_who():
    assert parse_record_id("Step 20260613-101432") == {"type": "Step", "id": "20260613-101432", "scheme": "timestamp"}


def test_parse_non_id_returns_none():
    assert parse_record_id("随便一行标题") is None


def test_parse_new_no_who_with_dup_roundtrips():
    assert parse_record_id("Step 20260613-101432.1") == {"type": "Step", "id": "20260613-101432.1", "scheme": "timestamp"}


def test_mint_no_who_same_second_is_parseable(tmp_path, monkeypatch):
    monkeypatch.setattr("step_id._who_suffix", lambda: "")
    w = datetime.datetime(2026, 6, 13, 10, 14, 32)
    r1 = mint_record_id("Step", tmp_path, when=w)   # "Step 20260613-101432"
    r2 = mint_record_id("Step", tmp_path, when=w)   # "Step 20260613-101432.1"
    assert parse_record_id(r1) is not None
    assert parse_record_id(r2) is not None
    assert parse_record_id(r2)["id"] == "20260613-101432.1"


def test_parse_who_and_dup_roundtrips():
    assert parse_record_id("Q 20260613-101432-ly.2") == {"type": "Q", "id": "20260613-101432-ly.2", "scheme": "timestamp"}
