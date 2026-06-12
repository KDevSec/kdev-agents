import json
from pathlib import Path

from kdev_hud import datasource as ds


def test_read_flow_state_missing_returns_none(tmp_workspace):
    assert ds.read_flow_state(tmp_workspace, "ghost") is None


def test_read_flow_state_parses(tmp_workspace, seed):
    slug = seed(tmp_workspace, stories=[{"id": "s1", "title": "x", "status": "done"}])
    doc = ds.read_flow_state(tmp_workspace, slug)
    assert doc["slug"] == slug and doc["active"]["current_node"] == "code-review"


def test_read_events_missing_returns_empty(tmp_workspace):
    assert ds.read_events(tmp_workspace, "ghost") == []


def test_read_events_skips_blank_and_corrupt(tmp_workspace, seed):
    slug = seed(tmp_workspace,
                gates=[{"gate": "g1", "kind": "review", "node": "n", "verdict": "PASS",
                        "iter": 1, "by": "ai", "issues": [], "ts": "2026-06-12T08:00:00+00:00"}])
    p = tmp_workspace / ".kdev" / "features" / slug / "events.jsonl"
    with p.open("a", encoding="utf-8") as f:
        f.write("\n{ not json\n")
    evs = ds.read_events(tmp_workspace, slug)
    assert len(evs) == 1 and evs[0]["verdict"] == "PASS"


def test_list_feature_slugs(tmp_workspace, seed):
    seed(tmp_workspace, slug="aaa")
    seed(tmp_workspace, slug="bbb")
    assert ds.list_feature_slugs(tmp_workspace) == ["aaa", "bbb"]


def test_list_feature_slugs_no_dir(tmp_workspace):
    assert ds.list_feature_slugs(tmp_workspace) == []


def test_seed_writes_real_format(tmp_workspace, seed):
    slug = seed(tmp_workspace,
                stories=[{"id": "s1", "title": "列表", "status": "done"},
                         {"id": "s2", "title": "新增", "status": "pending"}],
                gates=[{"gate": "g-code-review", "kind": "review", "node": "code-review",
                        "verdict": "PASS", "iter": 1, "by": "ai", "issues": [],
                        "ts": "2026-06-12T08:00:00+00:00"}])
    fs = tmp_workspace / ".kdev" / "features" / slug / "flow-state.json"
    ev = tmp_workspace / ".kdev" / "features" / slug / "events.jsonl"
    assert fs.exists() and ev.exists()
    doc = json.loads(fs.read_text(encoding="utf-8"))
    assert doc["slug"] == slug
    assert [s["status"] for s in doc["stories"]] == ["done", "pending"]
    line = json.loads(ev.read_text(encoding="utf-8").splitlines()[0])
    assert line["type"] == "gate" and line["verdict"] == "PASS" and "score" not in line
