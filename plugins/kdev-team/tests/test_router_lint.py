# plugins/kdev-team/tests/test_router_lint.py
import pytest
from kdev_team import roster


def test_flow_owner_vs_callee():
    assert roster.is_flow_owner("req-architect") is True
    assert roster.is_flow_owner("dev-engineer") is True
    assert roster.is_flow_owner("reviewer") is False    # callee
    assert roster.is_flow_owner("no-such-emp") is False


def test_flows_for_single_and_multi_flow_owner():
    assert roster.flows_for("req-architect") == ["design-flow"]
    assert roster.flows_for("dev-engineer") == ["coding-flow"]
    assert set(roster.flows_for("test-engineer")) == {"test-design-flow", "test-exec-flow"}


def test_gate_specs_and_delivery_node_resolved_from_node_table():
    gs = roster.gate_specs("req-architect", "design-flow")
    assert gs["g-sr-review"]["reviewer"] == "reviewer-expert"
    assert roster.delivery_node("req-architect", "design-flow") == "n8-merge"
    assert roster.delivery_node("test-engineer", "test-design-flow") == "n3-merge"


def test_unknown_flow_for_employee_raises():
    with pytest.raises(roster.RosterError):
        roster.node_table_data("req-architect", "coding-flow")


# ── lint 语义校验器测试 ──────────────────────────────────────────────────────
from kdev_team import lint, delivery_plan as dp

GOOD = """
template_id: full-delivery
slug: user-auth
goal: "做用户认证"
confidence: 0.86
reasoning: r
stages:
  - {emp: req-architect, flow: design-flow, on: true, handoff_from: null}
  - {emp: dev-engineer, flow: coding-flow, on: true, handoff_from: req-architect@n8-merge}
  - {emp: test-engineer, flow: test-design-flow, on: true, handoff_from: req-architect@n8-merge}
review_overrides:
  dev-engineer: {g-sec-review: reviewer-expert}
human_gates: [after-req]
"""


def _plan(**over):
    plan = dp.parse(GOOD)
    plan.update(over)
    return plan


def test_valid_plan_passes_lint():
    assert lint.validate(dp.parse(GOOD)) == []


def test_unknown_template_rejected():
    errs = lint.validate(_plan(template_id="bogus"))
    assert any("template" in e for e in errs)


def test_callee_employee_rejected():
    plan = _plan()
    plan["stages"][0]["emp"] = "reviewer"     # callee, 非 flow-owner
    errs = lint.validate(plan)
    assert any("reviewer" in e and "flow-owner" in e for e in errs)


def test_bad_flow_for_employee_rejected():
    plan = _plan()
    plan["stages"][1]["flow"] = "design-flow"   # dev-engineer 没有 design-flow
    assert any("flow" in e for e in lint.validate(plan))


def test_handoff_from_bad_node_rejected():
    plan = _plan()
    plan["stages"][1]["handoff_from"] = "req-architect@n99-bogus"
    errs = lint.validate(plan)
    assert any("handoff_from" in e and "n99-bogus" in e for e in errs)


def test_handoff_from_forward_reference_rejected():
    plan = _plan()
    # dev 引用 test（更晚的 stage）作上游 → 非法
    plan["stages"][1]["handoff_from"] = "test-engineer@n3-merge"
    errs = lint.validate(plan)
    assert any("handoff_from" in e and "earlier" in e for e in errs)


def test_review_override_unknown_gate_rejected():
    plan = _plan()
    plan["review_overrides"] = {"dev-engineer": {"g-nope": "reviewer-expert"}}
    assert any("g-nope" in e for e in lint.validate(plan))


def test_review_override_bad_value_rejected():
    plan = _plan()
    plan["review_overrides"] = {"dev-engineer": {"g-sec-review": "intern"}}
    assert any("intern" in e for e in lint.validate(plan))


def test_unknown_human_gate_rejected():
    assert any("human_gate" in e.lower() for e in lint.validate(_plan(human_gates=["after-lunch"])))


def test_low_confidence_requires_runner_up():
    plan = _plan(confidence=0.4)
    plan.pop("runner_up", None)
    assert any("runner_up" in e for e in lint.validate(plan))
    plan["runner_up"] = {"template_id": "design+build", "why_not": "x"}
    assert lint.validate(plan) == []
