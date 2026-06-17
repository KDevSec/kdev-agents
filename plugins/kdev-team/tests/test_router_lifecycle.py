# plugins/kdev-team/tests/test_router_lifecycle.py
import pytest
from kdev_team import lifecycle


def test_full_delivery_template_present():
    assert "full-delivery" in lifecycle.list_templates()


def test_load_full_delivery_has_three_stages():
    t = lifecycle.load_template("full-delivery")
    assert t["template_id"] == "full-delivery"
    emps = [s["emp"] for s in t["stages"]]
    assert emps == ["req-architect", "dev-engineer", "test-engineer"]
    flows = [s["flow"] for s in t["stages"]]
    assert flows == ["design-flow", "coding-flow", "test-design-flow"]
    assert t["stages"][1]["handoff_from"] == "req-architect@n8-merge"
    assert t["stages"][2]["handoff_from"] == "req-architect@n8-merge"
    assert t["human_gates_default"] == ["after-req"]


def test_unknown_template_raises():
    with pytest.raises(lifecycle.TemplateError):
        lifecycle.load_template("no-such-template")
