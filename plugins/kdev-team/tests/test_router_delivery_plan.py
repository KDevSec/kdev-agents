from kdev_team import delivery_plan as dp

VALID = """
template_id: full-delivery
slug: user-auth
goal: "做用户认证"
confidence: 0.86
reasoning: "全新功能"
stages:
  - {emp: req-architect, flow: design-flow, on: true, handoff_from: null}
  - {emp: dev-engineer, flow: coding-flow, on: true, handoff_from: req-architect@n8-merge}
human_gates: [after-req]
"""


def test_parse_fills_defaults():
    plan = dp.parse(VALID)
    assert plan["review_overrides"] == {}        # 缺省补空
    assert plan["human_gates"] == ["after-req"]
    assert plan["slug"] == "user-auth"


def test_structural_errors_empty_for_valid():
    assert dp.structural_errors(dp.parse(VALID)) == []


def test_structural_errors_flag_missing_keys_and_bad_confidence():
    plan = dp.parse(VALID)
    del plan["goal"]
    plan["confidence"] = 1.5
    errs = dp.structural_errors(plan)
    assert any("goal" in e for e in errs)
    assert any("confidence" in e for e in errs)


def test_structural_errors_flag_stage_missing_fields():
    plan = dp.parse(VALID)
    plan["stages"] = [{"emp": "req-architect"}]   # 缺 flow/on
    errs = dp.structural_errors(plan)
    assert any("flow" in e for e in errs)


def test_write_read_roundtrip_creates_dir(tmp_path):
    plan = dp.parse(VALID)
    p = dp.write(str(tmp_path), plan)
    assert p.exists()
    assert p == dp.path(str(tmp_path), "user-auth")
    got = dp.read(str(tmp_path), "user-auth")
    assert got["slug"] == "user-auth"
    assert got["stages"][1]["handoff_from"] == "req-architect@n8-merge"


def test_read_missing_returns_none(tmp_path):
    assert dp.read(str(tmp_path), "nope") is None
