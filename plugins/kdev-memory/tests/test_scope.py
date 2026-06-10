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
