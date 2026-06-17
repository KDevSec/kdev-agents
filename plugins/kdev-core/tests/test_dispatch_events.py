from kdev_core import events


def test_dispatch_start_event_shape():
    e = events.dispatch_event(
        phase="start", slug="user-auth", flow="design-flow",
        emp="req-architect", dispatch_id="user-auth#1-req-architect",
        stage_index=1, handoff_from=None)
    assert e["type"] == "dispatch"
    assert e["phase"] == "start"
    assert e["actor"] == "ceo"
    assert e["slug"] == "user-auth"
    assert e["flow"] == "design-flow"
    assert e["emp"] == "req-architect"
    assert e["dispatch_id"] == "user-auth#1-req-architect"
    assert e["stage_index"] == 1
    assert e["handoff_from"] is None
    assert "ts" in e


def test_dispatch_done_event_carries_optional_usage():
    e = events.dispatch_event(
        phase="done", slug="user-auth", flow="coding-flow",
        emp="dev-engineer", dispatch_id="user-auth#2-dev-engineer",
        status="done", subagent_tokens=12345, tool_uses=20, duration_s=88)
    assert e["phase"] == "done"
    assert e["status"] == "done"
    assert e["subagent_tokens"] == 12345
    assert e["tool_uses"] == 20
    assert e["duration_s"] == 88


def test_dispatch_done_usage_defaults_to_none():
    e = events.dispatch_event(
        phase="done", slug="s", flow="design-flow", emp="req-architect",
        dispatch_id="s#1-req-architect", status="done")
    assert e["subagent_tokens"] is None
    assert e["tool_uses"] is None
    assert e["duration_s"] is None


def test_dispatch_events_roundtrip_via_append_read(tmp_path):
    ws = str(tmp_path)
    start = events.dispatch_event(
        phase="start", slug="s", flow="design-flow", emp="req-architect",
        dispatch_id="s#1-req-architect", stage_index=1)
    done = events.dispatch_event(
        phase="done", slug="s", flow="design-flow", emp="req-architect",
        dispatch_id="s#1-req-architect", status="done")
    events.append_event(ws, "s", start)
    events.append_event(ws, "s", done)
    got = events.read_events(ws, "s")
    assert [g["phase"] for g in got] == ["start", "done"]
    assert all(g["type"] == "dispatch" for g in got)
    assert got[0]["dispatch_id"] == got[1]["dispatch_id"]
