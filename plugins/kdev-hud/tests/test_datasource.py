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


def test_read_events_oldest_first(tmp_workspace, seed):
    slug = seed(tmp_workspace,
                transitions=[{"from": "a", "to": "b", "reflow": False, "forced_fail": False,
                              "reason": "r1", "entered_at": "2026-06-12T07:00:00+00:00"},
                             {"from": "b", "to": "c", "reflow": False, "forced_fail": False,
                              "reason": "r2", "entered_at": "2026-06-12T07:10:00+00:00"}])
    evs = ds.read_events(tmp_workspace, slug)
    assert [e["to"] for e in evs] == ["b", "c"]  # oldest first contract


def test_build_feature_view_completion(tmp_workspace, seed):
    slug = seed(tmp_workspace, display_name="用户管理模块",
                stories=[{"id": "s1", "title": "列表", "status": "done"},
                         {"id": "s2", "title": "新增", "status": "done"},
                         {"id": "s3", "title": "角色", "status": "in_progress"},
                         {"id": "s4", "title": "导入", "status": "pending"}])
    v = ds.build_feature_view(tmp_workspace, slug)
    assert v["display_name"] == "用户管理模块"
    assert v["stories_done"] == 2 and v["stories_total"] == 4
    assert v["completion_pct"] == 50
    assert v["active"]["current_node"] == "code-review"
    assert v["active"]["status"] == "in_progress"


def test_build_feature_view_gates_no_score(tmp_workspace, seed):
    slug = seed(tmp_workspace,
                gates=[{"gate": "g-cr", "kind": "review", "node": "code-review",
                        "verdict": "PASS", "iter": 1, "by": "ai",
                        "issues": [], "ts": "2026-06-12T08:00:00+00:00"},
                       {"gate": "g-cr", "kind": "review", "node": "code-review",
                        "verdict": "FAIL", "iter": 2, "by": "ai",
                        "issues": ["命名", "边界"], "ts": "2026-06-12T08:05:00+00:00"}])
    v = ds.build_feature_view(tmp_workspace, slug)
    assert len(v["gates"]) == 2
    g = v["gates"][1]
    assert g["verdict"] == "FAIL" and g["iter"] == 2 and g["issues_count"] == 2
    assert "score" not in g  # FF-3：无 score


def test_build_feature_view_alerts_blocked_and_fail(tmp_workspace, seed):
    slug = seed(tmp_workspace, run_status="blocked", blocked_reason="连续 FAIL 超上限",
                gates=[{"gate": "g", "kind": "review", "node": "n", "verdict": "FAIL",
                        "iter": 1, "by": "ai", "issues": ["x"],
                        "ts": "2026-06-12T08:00:00+00:00"}])
    v = ds.build_feature_view(tmp_workspace, slug)
    kinds = sorted(a["kind"] for a in v["alerts"])
    assert kinds == ["blocked", "gate_fail"]
    assert v["alert_count"] == 2


def test_build_feature_view_no_active(tmp_workspace, seed):
    slug = seed(tmp_workspace)
    from kdev_core import flow_state
    flow_state.complete_run(tmp_workspace, slug, status="completed", close_feature=True)
    v = ds.build_feature_view(tmp_workspace, slug)
    assert v["active"] is None
    assert v["feature_status"] == "completed"


def test_build_feature_view_missing_returns_none(tmp_workspace):
    assert ds.build_feature_view(tmp_workspace, "ghost") is None


def test_build_hud_model_multi_feature_and_primary(tmp_workspace, seed):
    # bbb 有在跑棒次 → 应被选为 primary（aaa 无 active）
    s_a = seed(tmp_workspace, slug="aaa")
    from kdev_core import flow_state
    flow_state.complete_run(tmp_workspace, s_a, status="completed", close_feature=True)
    seed(tmp_workspace, slug="bbb", display_name="在跑的")
    model = ds.build_hud_model(tmp_workspace)
    assert [f["slug"] for f in model["features"]] == ["aaa", "bbb"]
    assert model["primary"]["slug"] == "bbb"
    assert model["feature_count"] == 2


def test_build_hud_model_empty(tmp_workspace):
    model = ds.build_hud_model(tmp_workspace)
    assert model["features"] == [] and model["primary"] is None and model["feature_count"] == 0


def test_build_hud_model_primary_fallback_recent(tmp_workspace, seed):
    # 都无 active → primary 取 updated_at 最新
    s1 = seed(tmp_workspace, slug="aaa")
    s2 = seed(tmp_workspace, slug="bbb")
    from kdev_core import flow_state
    flow_state.complete_run(tmp_workspace, s1, status="completed", close_feature=True)
    flow_state.complete_run(tmp_workspace, s2, status="completed", close_feature=True)
    model = ds.build_hud_model(tmp_workspace)
    assert model["primary"] is not None  # 不报错、有兜底
