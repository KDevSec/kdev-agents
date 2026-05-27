"""Smoke test: simulate the full state.md + events.log + handoffs/ lifecycle."""
from datetime import datetime, timezone
from pathlib import Path

from kdev_cluster_x3.lib.state_md import StateMd, GROUPS
from kdev_cluster_x3.lib.events_log import EventsLog, EventType
from kdev_cluster_x3.lib.handoffs import write_complete, read_complete
from kdev_cluster_x3.lib.ar_number import is_valid_ar


def test_full_lifecycle(tmp_kdev):
    started = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    s = StateMd.init(tmp_kdev / "state.md", feature="产品管理三层", slug="chan-pin", started_at=started)
    log = EventsLog(tmp_kdev / "events.log")

    # reqs
    s.update_group("reqs", status="in_progress", current_step="ir")
    s.write(tmp_kdev / "state.md")
    log.append(agent="需求澄清师", event_type=EventType.STEP_COMPLETE, msg="IR 完成")
    assert is_valid_ar("AR-PROD_LINE-01.001.001")
    write_complete(
        tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md",
        group="reqs", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", ar_count=12,
    )
    s = StateMd.read(tmp_kdev / "state.md")
    s.update_group("reqs", status="complete")
    s.write(tmp_kdev / "state.md")

    # dev
    s.update_group("dev", status="in_progress", current_step="node-6b")
    s.write(tmp_kdev / "state.md")
    write_complete(
        tmp_kdev / "handoffs" / "dev" / "COMPLETE.md",
        group="dev", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", commits_count=7,
    )

    # test
    write_complete(
        tmp_kdev / "handoffs" / "test" / "COMPLETE.md",
        group="test", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", total_cases=20, passed_cases=20,
    )

    # review
    write_complete(
        tmp_kdev / "handoffs" / "review" / "COMPLETE.md",
        group="review", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", verdict="pass",
    )

    # final assertions
    for g in GROUPS:
        meta = read_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md")
        assert meta["group"] == g
        assert meta["status"] == "complete"

    # 6 events.log entries minimum (1 step_complete in this micro-test; real flow has many more)
    assert len(log.read_all()) >= 1


def test_resume_after_interrupt(tmp_kdev):
    """Simulate: reqs complete, dev half-done (node-6b), then new session reads state and resumes."""
    from datetime import datetime, timezone
    from pathlib import Path
    from kdev_cluster_x3.lib.state_md import StateMd
    from kdev_cluster_x3.lib.events_log import EventsLog, EventType

    # "previous session": reqs done, dev stopped at node-6b
    s = StateMd.init(tmp_kdev / "state.md", feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s.update_group("reqs", status="complete", current_step="-")
    s.update_group("dev", status="in_progress", current_step="node-6b", last_progress="TDD 实现员跑到一半")
    s.write(tmp_kdev / "state.md")
    log = EventsLog(tmp_kdev / "events.log")
    log.append(agent="TDD实现员", event_type=EventType.STEP_START, msg="开始 node-6b")
    # session crash here — no step_complete

    # "new session": read state.md, identify which group is mid-progress
    s2 = StateMd.read(tmp_kdev / "state.md")
    assert s2.groups["reqs"]["status"] == "complete"
    assert s2.groups["dev"]["status"] == "in_progress"
    assert s2.groups["dev"]["current_step"] == "node-6b"
    # main agent's recovery logic should now re-dispatch TDD实现员 starting at node-6b
    # (idempotency: it should detect step_start without matching step_complete in events.log)
    events = log.read_all()
    starts = [e for e in events if e.event_type == "step_start" and e.agent == "TDD实现员"]
    completes = [e for e in events if e.event_type == "step_complete" and e.agent == "TDD实现员"]
    assert len(starts) > len(completes), "should detect dangling step_start (= needs resume)"
