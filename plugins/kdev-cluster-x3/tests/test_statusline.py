import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parent.parent / "skills" / "kdev-statusline" / "kdev-statusline.sh"


def _run(cwd: Path) -> str:
    return subprocess.run(["bash", str(SCRIPT)], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_no_state_md_returns_idle(tmp_kdev):
    # remove state.md to test empty state
    (tmp_kdev / "state.md").unlink()
    out = _run(tmp_kdev.parent)
    assert "idle" in out.lower() or out == ""


def test_in_progress_state_renders(tmp_kdev):
    (tmp_kdev / "state.md").write_text(
        "# KDev State\n\nfeature: 产品管理\nfeature_slug: chan-pin\n"
        "feature_started_at: 2026-05-27T16:00:00+00:00\n"
        "current_active_group: dev\n\n"
        "## reqs\nstatus: complete\ncurrent_step: -\n"
        "started_at: 2026-05-27T16:00:00\ncompleted_at: 2026-05-27T17:00:00\n"
        "last_progress: 全部完成\n\n"
        "## dev\nstatus: in_progress\ncurrent_step: node-6b\n"
        "started_at: 2026-05-27T17:00:00\ncompleted_at: -\n"
        "last_progress: TDD 节点 6b\n\n"
        "## test\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## review\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n",
        encoding="utf-8",
    )
    out = _run(tmp_kdev.parent)
    assert "KDev" in out
    assert "✅" in out  # reqs complete
    assert "🟡" in out  # dev in_progress
    assert "chan-pin" in out
    assert len(out) <= 100  # safety margin (target ≤80)


def test_blocked_state_renders_red(tmp_kdev):
    (tmp_kdev / "state.md").write_text(
        "# KDev State\n\nfeature: x\nfeature_slug: x\n"
        "feature_started_at: 2026-05-27T16:00:00+00:00\n"
        "current_active_group: dev\n\n"
        "## reqs\nstatus: complete\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## dev\nstatus: blocked\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: TDD halt\n\n"
        "## test\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## review\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n",
        encoding="utf-8",
    )
    out = _run(tmp_kdev.parent)
    assert "🔴" in out
