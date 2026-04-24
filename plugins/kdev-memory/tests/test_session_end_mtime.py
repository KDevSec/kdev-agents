"""test SessionEnd hook 的 mtime-based WARN 生成逻辑（v0.7）

v0.6: git status --porcelain 检测 .kdev/ dirty → 生成 WARN
v0.7: .last-flush mtime 比对 → 生成 WARN（立场反转后 .kdev/ 不 git tracked 也能工作）
"""

import os
import subprocess
import time
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-end-check.sh"


def _setup_kdev(tmp_path: Path) -> Path:
    """造一个最小 .kdev/memory/ 结构，返回 project root。"""
    project = tmp_path / "project"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    # init git so git-based fallback also usable if needed
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"],
        cwd=project,
        check=True,
    )
    return project


def test_warn_generated_when_kdev_modified_after_last_flush(tmp_path):
    """.last-flush 存在、有比它新的 .kdev/memory/ 文件 → 应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    flush = project / ".kdev" / "memory" / ".last-flush"
    flush.touch()
    # 让 .last-flush mtime 比 执行日志 更旧
    old_time = time.time() - 3600
    os.utime(flush, (old_time, old_time))
    # 碰一下执行日志模拟新修改（mtime 默认是当前时间）
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert warn.exists(), "SessionEnd 应生成 WARN（mtime 机制），但 WARN 文件不存在"


def test_no_warn_when_last_flush_newer(tmp_path):
    """.last-flush 最新（说明落盘都已刷新）→ 不应生成 WARN。"""
    project = _setup_kdev(tmp_path)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    # last-flush 在执行日志之后 touch
    time.sleep(0.1)
    (project / ".kdev" / "memory" / ".last-flush").touch()
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "last-flush 比 .kdev/ 都新 → 不应有 WARN"


def test_no_warn_when_no_last_flush_and_no_changes(tmp_path):
    """无 .last-flush 且 .kdev/memory/ 基本无变化（init 后刚 commit）→ 无 WARN。"""
    project = _setup_kdev(tmp_path)
    subprocess.run(["bash", str(HOOK)], cwd=project, check=True)
    from datetime import date
    warn = project / ".kdev" / "memory" / f"WARN-未记录-{date.today().isoformat()}.md"
    assert not warn.exists(), "初始化空项目不应有 WARN"


def test_works_without_git_repo(tmp_path):
    """立场反转后：非 git 项目也要能正常工作（不 crash、不误报）。"""
    project = tmp_path / "nogit"
    (project / ".kdev" / "memory").mkdir(parents=True)
    (project / ".kdev" / "memory" / "执行日志.md").write_text(
        "# 执行日志\n\n## Step 1\n", encoding="utf-8"
    )
    # 无 git init
    result = subprocess.run(
        ["bash", str(HOOK)], cwd=project, capture_output=True, text=True
    )
    assert result.returncode == 0, f"hook 异常退出: {result.stderr}"
