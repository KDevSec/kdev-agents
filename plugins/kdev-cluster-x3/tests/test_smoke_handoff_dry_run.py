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
