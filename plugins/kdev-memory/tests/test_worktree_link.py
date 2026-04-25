"""test worktree_link.py: secondary worktree 自动 symlink .kdev → 主 worktree（v0.7.1 / v0.8 转 Python）

平台覆盖：Linux / macOS。Windows (junction via cmd /c mklink /J) 因为 CI 环境难以可靠模拟，跳过——
通过 README + 人工验证保证。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"


skip_on_windows = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows junction 通过 cmd /c mklink /J 实现，需手动验证（README 说明手动方案）",
)


def _utf8_env() -> dict:
    return {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}


def _run_in(project: Path) -> subprocess.CompletedProcess:
    """子进程调 worktree_link.py 的 worktree_link_kdev()，cwd=project。"""
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(LIB_DIR)!r})\n"
        "from worktree_link import worktree_link_kdev\n"
        "worktree_link_kdev()\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(project), capture_output=True, env=_utf8_env(),
    )
    result.stdout = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else result.stdout
    result.stderr = result.stderr.decode("utf-8", errors="replace") if isinstance(result.stderr, bytes) else result.stderr
    return result


def _init_main(tmp_path: Path) -> Path:
    """造一个有 .kdev/memory/ 的主 worktree。"""
    main = tmp_path / "main"
    main.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=main, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                   "commit", "-q", "--allow-empty", "-m", "init"], cwd=main, check=True)
    (main / ".kdev" / "memory").mkdir(parents=True)
    (main / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    return main


def _add_secondary(main: Path, branch: str = "feature/x") -> Path:
    """在主 worktree 下挂一个 secondary worktree。"""
    secondary = main.parent / "secondary"
    subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(secondary)],
        cwd=main, check=True, capture_output=True,
    )
    return secondary


@skip_on_windows
def test_main_worktree_skipped(tmp_path):
    """主 worktree 调用时不创建 symlink（因为它自己就是真源）。"""
    main = _init_main(tmp_path)
    _run_in(main)
    # .kdev/ 仍是真目录而非 symlink
    assert (main / ".kdev").is_dir()
    assert not (main / ".kdev").is_symlink()


@skip_on_windows
def test_secondary_worktree_auto_symlink(tmp_path):
    """secondary worktree 启动时自动 symlink .kdev → 主 worktree 的 .kdev/。"""
    main = _init_main(tmp_path)
    secondary = _add_secondary(main)
    # 起始 secondary 没有 .kdev/
    assert not (secondary / ".kdev").exists()
    # 调 helper
    r = _run_in(secondary)
    assert r.returncode == 0, f"helper failed: {r.stderr}"
    # 现在 secondary 有 .kdev 且是 symlink
    assert (secondary / ".kdev").is_symlink(), "应自动建 symlink"
    # symlink 解出来等于主 worktree 的 .kdev/
    target = (secondary / ".kdev").resolve()
    expected = (main / ".kdev").resolve()
    assert target == expected, f"symlink 指向错：{target} vs {expected}"
    # 通过 symlink 能读到主 worktree 的内容
    assert (secondary / ".kdev" / "memory" / "执行日志.md").read_text(encoding="utf-8") == "# 执行日志\n"


@skip_on_windows
def test_secondary_worktree_idempotent(tmp_path):
    """重复调用不报错、不破坏已有 symlink。"""
    main = _init_main(tmp_path)
    secondary = _add_secondary(main)
    _run_in(secondary)
    first_target = (secondary / ".kdev").resolve()
    # 第二次调
    r = _run_in(secondary)
    assert r.returncode == 0
    second_target = (secondary / ".kdev").resolve()
    assert first_target == second_target


@skip_on_windows
def test_secondary_worktree_local_kdev_preserved(tmp_path):
    """secondary worktree 已有真 .kdev/（用户手动建的）→ 不覆盖。"""
    main = _init_main(tmp_path)
    secondary = _add_secondary(main)
    # 用户手动建了本地 .kdev/
    (secondary / ".kdev" / "memory").mkdir(parents=True)
    (secondary / ".kdev" / "memory" / "本地.md").write_text("local-only\n", encoding="utf-8")
    _run_in(secondary)
    # 仍是真目录，本地文件没被覆盖
    assert (secondary / ".kdev").is_dir()
    assert not (secondary / ".kdev").is_symlink()
    assert (secondary / ".kdev" / "memory" / "本地.md").exists()


@skip_on_windows
def test_secondary_worktree_skipped_when_main_has_no_kdev(tmp_path):
    """主 worktree 没 .kdev/ → 不强建 symlink。"""
    main = tmp_path / "main"
    main.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=main, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                   "commit", "-q", "--allow-empty", "-m", "init"], cwd=main, check=True)
    secondary = main.parent / "secondary"
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/y", str(secondary)],
        cwd=main, check=True, capture_output=True,
    )
    _run_in(secondary)
    assert not (secondary / ".kdev").exists()


@skip_on_windows
def test_outside_git_repo_skipped(tmp_path):
    """非 git 仓库调用 helper → 静默返回，不报错不创建。"""
    not_a_repo = tmp_path / "not-git"
    not_a_repo.mkdir()
    r = _run_in(not_a_repo)
    assert r.returncode == 0
    assert not (not_a_repo / ".kdev").exists()


@skip_on_windows
def test_git_track_opt_in_secondary_worktree_not_symlinked(tmp_path):
    """若用户选择 KDEV_GIT_TRACK=1 opt-in 托管 .kdev/（走 v0.6 遗留工作流），
    secondary worktree 的 .kdev/ 是 git checkout 出来的真目录，worktree-link
    应安全跳过（[ -e .kdev ] 守卫），不把真目录改成 symlink 破坏用户数据。"""
    main = _init_main(tmp_path)
    # 模拟用户 opt-in：把 .kdev/ commit 进 git
    subprocess.run(["git", "add", ".kdev"], cwd=main, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                   "commit", "-q", "-m", "track .kdev (KDEV_GIT_TRACK=1 opt-in)"],
                  cwd=main, check=True)

    # 造 secondary worktree，会自动 checkout 出 .kdev/（因为被 track）
    secondary = _add_secondary(main)
    assert (secondary / ".kdev").is_dir(), "secondary worktree 应有从 git checkout 的真 .kdev/"
    assert not (secondary / ".kdev").is_symlink()

    # 关键：worktree-link 不应该覆盖真目录
    r = _run_in(secondary)
    assert r.returncode == 0
    assert (secondary / ".kdev").is_dir(), "worktree-link 不应把真目录改成 symlink"
    assert not (secondary / ".kdev").is_symlink()
    # 原有文件保留
    assert (secondary / ".kdev" / "memory" / "执行日志.md").exists()
