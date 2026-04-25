"""test init-gitignore.py: 自动 append .kdev/ 到 .gitignore（v0.7 立场反转 / v0.8 转 Python）"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

HELPER = Path(__file__).parent.parent / "hooks" / "lib" / "init-gitignore.py"


def _run(project: Path, env_extra: Optional[dict] = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"}
    if env_extra is not None:
        env = {**env, **env_extra}
    # 二进制捕获 + UTF-8 解码（防 Windows 中文 GBK）
    result = subprocess.run(
        [sys.executable, str(HELPER)],
        cwd=str(project), capture_output=True, env=env,
    )
    result.stdout = result.stdout.decode("utf-8", errors="replace")
    result.stderr = result.stderr.decode("utf-8", errors="replace")
    return result


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
