import json
from pathlib import Path


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
