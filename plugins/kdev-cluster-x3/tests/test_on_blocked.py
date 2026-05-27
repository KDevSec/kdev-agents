from pathlib import Path
import json
import subprocess
import sys


HOOK = Path(__file__).parent.parent / "hooks" / "on-blocked.py"


def test_no_events_log_no_op(tmp_kdev):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=tmp_kdev.parent,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_last_line_not_blocked_no_op(tmp_kdev):
    (tmp_kdev / "events.log").write_text(
        "2026-05-27T16:00:00+00:00\t需求规格师\tstep_complete\tSR 完成\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_last_line_blocked_emits_dispatch_directive(tmp_kdev):
    (tmp_kdev / "events.log").write_text(
        "2026-05-27T16:00:00+00:00\tTDD实现员\tblocked\trepro 失败 3 次\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert proc.returncode == 0
    out = proc.stdout
    assert "开发组长" in out
    assert "TDD实现员" in out
    assert "repro 失败 3 次" in out


def test_double_fire_dedup(tmp_kdev):
    """连续两次触发，对同一 blocked 事件只输出一次 directive。"""
    events = tmp_kdev / "events.log"
    events.write_text(
        "2026-05-27T16:00:00+00:00\tTDD实现员\tblocked\thalt\n",
        encoding="utf-8",
    )
    p1 = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    p2 = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert p1.stdout != ""
    assert p2.stdout.strip() == ""  # second fire: nothing new
