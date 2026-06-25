"""Tests for kdev_sync._git() GCM three-switch non-interactive behavior.

Covers: env GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=Never, -c credential.interactive=false.
"""
import importlib.util
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

LIB = Path(__file__).parent.parent / "hooks" / "lib" / "kdev_sync.py"
_spec = importlib.util.spec_from_file_location("kdev_sync", LIB)
kdev_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kdev_sync)


def test_git_injects_noninteractive_conf_before_identity(tmp_path):
    """-c credential.interactive=false appears BEFORE _GIT_ID in argv (order-sensitive)."""
    with mock.patch("subprocess.run") as m_run:
        m_run.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="", stderr="")
        kdev_sync._git(["pull", "--ff-only"], cwd=tmp_path, identity=True)
        argv = m_run.call_args[0][0]
        git_idx = argv.index("git")
        ci_idx = argv.index("-c")
        assert argv[ci_idx + 1] == "credential.interactive=false"
        # noninteractive -c before _GIT_ID -c args
        id_idx = argv.index("user.name=kdev-memory")
        assert ci_idx < id_idx, "credential.interactive=false must come before _GIT_ID"
        assert git_idx < ci_idx


def test_git_passes_noninteractive_env(tmp_path):
    """env= dict contains GIT_TERMINAL_PROMPT=0 and GCM_INTERACTIVE=Never."""
    with mock.patch("subprocess.run") as m_run:
        m_run.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="", stderr="")
        kdev_sync._git(["pull", "--ff-only"], cwd=tmp_path)
        env = m_run.call_args[1]["env"]
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GCM_INTERACTIVE"] == "Never"


def test_git_env_preserves_os_environ(tmp_path):
    """Caller's os.environ (e.g. PATH) is retained in the merged env."""
    with mock.patch("subprocess.run") as m_run:
        m_run.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="", stderr="")
        kdev_sync._git(["pull", "--ffonly"], cwd=tmp_path)
        env = m_run.call_args[1]["env"]
        assert "PATH" in env


def test_git_identity_true_injects_git_id(tmp_path):
    """identity=True -> argv contains all three _GIT_ID -c pairs."""
    with mock.patch("subprocess.run") as m_run:
        m_run.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="", stderr="")
        kdev_sync._git(["push"], cwd=tmp_path, identity=True)
        argv = m_run.call_args[0][0]
        assert "user.name=kdev-memory" in argv
        assert "user.email=kdev@local" in argv
        assert "commit.gpgsign=false" in argv


def test_git_identity_false_excludes_git_id(tmp_path):
    """identity=False -> argv does NOT contain _GIT_ID content."""
    with mock.patch("subprocess.run") as m_run:
        m_run.return_value = subprocess.CompletedProcess(
            ["git"], 0, stdout="", stderr="")
        kdev_sync._git(["pull"], cwd=tmp_path, identity=False)
        argv = m_run.call_args[0][0]
        assert "user.name=kdev-memory" not in argv
        assert "user.email=kdev@local" not in argv
        assert "commit.gpgsign=false" not in argv


def test_git_noninteractive_conf_always_present(tmp_path):
    """-c credential.interactive=false is present regardless of identity flag."""
    for ident in [True, False]:
        with mock.patch("subprocess.run") as m_run:
            m_run.return_value = subprocess.CompletedProcess(
                ["git"], 0, stdout="", stderr="")
            kdev_sync._git(["pull"], cwd=tmp_path, identity=ident)
            argv = m_run.call_args[0][0]
            assert "credential.interactive=false" in argv
