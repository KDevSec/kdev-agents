from kdev_team import confirm, delivery_plan as dp

# 内联合法 plan 文本（禁跨 test 文件导入，见 plan 测试基建约定）
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
runner_up: {template_id: design+build, why_not: "含'功能'隐含可交付"}
"""


def test_review_items_from_gate_specs_only_review_kind():
    items = confirm.review_items("dev-engineer", "coding-flow", {})
    gates = {it["gate"] for it in items}
    assert {"g-plan-review", "g-code-review", "g-sec-review"} <= gates
    assert "g-relevance" not in gates       # decision kind 不列
    assert "g-e2e" not in gates             # acceptance kind 不列


def test_review_items_reflect_override():
    items = confirm.review_items(
        "dev-engineer", "coding-flow", {"g-sec-review": "self"})
    sec = next(it for it in items if it["gate"] == "g-sec-review")
    assert sec["reviewer"] == "self" and sec["overridden"] is True


def test_render_screen_contains_key_sections():
    s = confirm.render_screen(dp.parse(GOOD))
    assert "user-auth" in s                 # slug
    assert "full-delivery" in s             # 归类
    assert "0.86" in s                      # confidence
    assert "需求架构师" in s and "开发工程师" in s and "测试工程师" in s
    assert "串行" in s                       # 非并发提示
    assert "after-req" in s                  # human gate
    assert "design+build" in s               # runner_up
    assert "req-architect@n8-merge" in s     # handoff 来源


def test_render_screen_low_confidence_forces_second_confirm():
    plan = dp.parse(GOOD)
    plan["confidence"] = 0.4
    plan["runner_up"] = {"template_id": "design+build", "why_not": "x"}
    s = confirm.render_screen(plan)
    assert "禁" in s or "二次确认" in s      # 禁一键 Enter 提示


import pytest


def test_drop_stage_sets_on_false():
    plan = dp.parse(GOOD)
    out = confirm.apply_edit(plan, "d 3")
    assert out["stages"][2]["on"] is False
    assert plan["stages"][2]["on"] is True      # 原 plan 不被改


def test_review_override_edit():
    out = confirm.apply_edit(dp.parse(GOOD), "r dev-engineer g-sec-review=self")
    assert out["review_overrides"]["dev-engineer"]["g-sec-review"] == "self"


def test_add_and_remove_human_gate():
    out = confirm.apply_edit(dp.parse(GOOD), "g +after-test")
    assert "after-test" in out["human_gates"]
    out2 = confirm.apply_edit(out, "g -after-req")
    assert "after-req" not in out2["human_gates"]


def test_swap_template_and_slug():
    out = confirm.apply_edit(dp.parse(GOOD), "t design+build")
    assert out["template_id"] == "design+build"
    out2 = confirm.apply_edit(out, "s my-feature")
    assert out2["slug"] == "my-feature"


def test_unknown_command_raises():
    with pytest.raises(confirm.EditError):
        confirm.apply_edit(dp.parse(GOOD), "frobnicate 7")
