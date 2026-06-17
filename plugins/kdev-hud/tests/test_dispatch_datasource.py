# plugins/kdev-hud/tests/test_dispatch_datasource.py
from kdev_hud import datasource


def _ev(**kw):
    base = {"type": "dispatch", "slug": "s", "flow": "design-flow",
            "emp": "req-architect", "dispatch_id": "s#1-req-architect"}
    base.update(kw)
    return base


def test_dispatch_views_pairs_start_and_done():
    evs = [
        _ev(phase="start", stage_index=1, ts="2026-01-01T00:00:00+00:00"),
        _ev(phase="done", status="done", subagent_tokens=500,
            ts="2026-01-01T00:05:00+00:00"),
    ]
    views = datasource._dispatch_views(evs)
    assert len(views) == 1
    v = views[0]
    assert v["status"] == "done" and v["running"] is False
    assert v["subagent_tokens"] == 500
    assert v["started_at"] == "2026-01-01T00:00:00+00:00"
    assert v["done_at"] == "2026-01-01T00:05:00+00:00"


def test_dispatch_view_running_when_no_done():
    views = datasource._dispatch_views([_ev(phase="start", stage_index=1)])
    assert views[0]["running"] is True
    assert views[0]["status"] == "running"


def test_dispatch_views_ignores_non_dispatch():
    evs = [{"type": "gate", "verdict": "PASS"}, _ev(phase="start", stage_index=1)]
    assert len(datasource._dispatch_views(evs)) == 1


def test_read_delivery_plan_missing_returns_none(tmp_path):
    assert datasource.read_delivery_plan(str(tmp_path), "nope") is None


def test_read_delivery_plan_parses(tmp_path):
    d = tmp_path / ".kdev" / "features" / "s"
    d.mkdir(parents=True)
    (d / "delivery-plan.yml").write_text(
        "template_id: full-delivery\nslug: s\nstages:\n"
        "  - {emp: req-architect, flow: design-flow, on: true}\n",
        encoding="utf-8")
    plan = datasource.read_delivery_plan(str(tmp_path), "s")
    assert plan["template_id"] == "full-delivery"
    assert plan["stages"][0]["emp"] == "req-architect"


def test_read_delivery_plan_normalizes_bare_on_key(tmp_path):
    """YAML 1.1 裸 on: 键 → 布尔 True；read_delivery_plan 须归一回字符串 "on"。"""
    d = tmp_path / ".kdev" / "features" / "s"
    d.mkdir(parents=True)
    (d / "delivery-plan.yml").write_text(
        "template_id: full-delivery\nslug: s\nstages:\n"
        "  - {emp: req-architect, flow: design-flow, on: true}\n",
        encoding="utf-8")
    plan = datasource.read_delivery_plan(str(tmp_path), "s")
    assert plan["stages"][0].get("on") is True   # 归一后 stage.get("on") 稳定
    assert True not in plan["stages"][0]          # 布尔 True 键已被搬走


import json


def _seed(tmp_path, plan_yaml, events):
    d = tmp_path / ".kdev" / "features" / "auth"
    d.mkdir(parents=True)
    (d / "flow-state.json").write_text(json.dumps({"slug": "auth", "stories": []}),
                                       encoding="utf-8")
    (d / "delivery-plan.yml").write_text(plan_yaml, encoding="utf-8")
    with (d / "events.jsonl").open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")
    return str(tmp_path)


PLAN = ("template_id: full-delivery\nslug: auth\ngoal: g\nstages:\n"
        "  - {emp: req-architect, flow: design-flow, on: true, handoff_from: null}\n"
        "  - {emp: dev-engineer, flow: coding-flow, on: true, handoff_from: req-architect@n8-merge}\n"
        "  - {emp: test-engineer, flow: test-design-flow, on: true, handoff_from: req-architect@n8-merge}\n")


def test_feature_view_has_delivery_progress(tmp_path):
    ws = _seed(tmp_path, PLAN, [
        _ev(phase="start", emp="req-architect", dispatch_id="auth#1-req-architect", stage_index=1, slug="auth"),
        _ev(phase="done", status="done", emp="req-architect", dispatch_id="auth#1-req-architect", slug="auth"),
        _ev(phase="start", emp="dev-engineer", flow="coding-flow", dispatch_id="auth#2-dev-engineer", stage_index=2, slug="auth"),
    ])
    v = datasource.build_feature_view(ws, "auth")
    assert v["delivery"]["total_on"] == 3
    assert v["delivery"]["done_count"] == 1
    assert v["delivery"]["progress_label"] == "链进度 1/3"
    assert len(v["dispatches"]) == 2


def test_employee_activity_marks_running_busy(tmp_path):
    ws = _seed(tmp_path, PLAN, [
        _ev(phase="start", emp="dev-engineer", flow="coding-flow", dispatch_id="auth#2-dev-engineer", stage_index=2, slug="auth"),
    ])
    v = datasource.build_feature_view(ws, "auth")
    busy = {a["emp"]: a["busy"] for a in v["employee_activity"]}
    assert busy.get("dev-engineer") is True


def test_feature_view_no_delivery_plan_is_none(tmp_path):
    d = tmp_path / ".kdev" / "features" / "bare"
    d.mkdir(parents=True)
    (d / "flow-state.json").write_text(json.dumps({"slug": "bare", "stories": []}),
                                       encoding="utf-8")
    v = datasource.build_feature_view(str(tmp_path), "bare")
    assert v["delivery"] is None
    assert v["dispatches"] == []
