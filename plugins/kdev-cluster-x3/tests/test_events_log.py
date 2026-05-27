from datetime import datetime, timezone
from kdev_cluster_x3.lib.events_log import EventsLog, EventType


def test_append_writes_iso_ts_tab_separated(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    log.append(agent="reqs-tl", event_type=EventType.STEP_COMPLETE, msg="IR 完成")
    line = path.read_text(encoding="utf-8").strip()
    parts = line.split("\t")
    assert len(parts) == 4
    assert parts[1] == "reqs-tl"
    assert parts[2] == "step_complete"
    assert parts[3] == "IR 完成"
    # ts is ISO-8601 with tz
    datetime.fromisoformat(parts[0])


def test_append_fixed_ts(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    when = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    log.append(agent="dev-tl", event_type=EventType.BLOCKED, msg="repro fail x3", ts=when)
    assert "2026-05-27T16:00:00+00:00" in path.read_text(encoding="utf-8")


def test_tail_returns_last_n(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    for i in range(10):
        log.append(agent=f"a{i}", event_type=EventType.NOTE, msg=f"msg-{i}")
    tail = log.tail(3)
    assert len(tail) == 3
    assert tail[-1].msg == "msg-9"


def test_filter_by_event_type(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    log.append(agent="a", event_type=EventType.STEP_COMPLETE, msg="x")
    log.append(agent="a", event_type=EventType.BLOCKED, msg="halt")
    log.append(agent="b", event_type=EventType.BLOCKED, msg="halt2")
    blocked = log.filter(event_type=EventType.BLOCKED)
    assert [e.msg for e in blocked] == ["halt", "halt2"]


def test_blocked_agent_to_group_routing(tmp_kdev):
    from kdev_cluster_x3.lib.events_log import agent_to_group
    assert agent_to_group("需求澄清师") == "reqs"
    assert agent_to_group("TDD实现员") == "dev"
    assert agent_to_group("UI自动化工程师") == "test"
    assert agent_to_group("代码评审员") == "review"
    assert agent_to_group("主控员") == "orchestrator"
