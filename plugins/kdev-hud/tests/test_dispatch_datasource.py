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
