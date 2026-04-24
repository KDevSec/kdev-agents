"""test init-gitignore.sh: 自动 append .kdev/ 到 .gitignore（v0.7 立场反转）"""

import subprocess
from pathlib import Path

HELPER = Path(__file__).parent.parent / "hooks" / "lib" / "init-gitignore.sh"


def _run(project: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = None
    if env_extra is not None:
        import os
        env = {**os.environ, **env_extra}
    return subprocess.run(
        ["bash", str(HELPER)], cwd=project, capture_output=True, text=True, env=env
    )


def test_append_when_no_gitignore(tmp_path):
    """没有 .gitignore → 创建新文件，写入 .kdev/ 一行。"""
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" in content


def test_append_when_gitignore_missing_kdev(tmp_path):
    """.gitignore 存在但无 .kdev/ → 追加。"""
    (tmp_path / ".gitignore").write_text("node_modules/\n*.log\n", encoding="utf-8")
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" in content
    assert "node_modules/" in content  # 原有不丢


def test_idempotent_when_kdev_already_ignored(tmp_path):
    """.gitignore 已有 .kdev/ → 不重复追加。"""
    (tmp_path / ".gitignore").write_text(".kdev/\nnode_modules/\n", encoding="utf-8")
    _run(tmp_path)
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert content.count(".kdev/") == 1


def test_respects_kdev_track_env(tmp_path):
    """KDEV_GIT_TRACK=1 → 不写入 .gitignore（单人用户 opt-in 托管）。"""
    (tmp_path / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    _run(tmp_path, env_extra={"KDEV_GIT_TRACK": "1"})
    content = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".kdev/" not in content
