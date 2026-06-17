from kdev_team import drive, delivery_plan as dp

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
human_gates: [after-req]
"""


def test_sequence_length_and_order():
    seq = drive.build_sequence(dp.parse(GOOD))
    assert [s["emp"] for s in seq] == ["req-architect", "dev-engineer", "test-engineer"]
    assert [s["stage_index"] for s in seq] == [1, 2, 3]


def test_dispatch_ids_unique_and_formatted():
    seq = drive.build_sequence(dp.parse(GOOD))
    assert seq[0]["dispatch_id"] == "user-auth#1-req-architect"
    assert len({s["dispatch_id"] for s in seq}) == 3


def test_driver_cmd_carries_slug():
    seq = drive.build_sequence(dp.parse(GOOD))
    assert "--slug user-auth" in seq[1]["driver_cmd"]
    assert "dev-engineer" in seq[1]["driver_cmd"]


def test_human_gate_after_only_when_in_plan():
    seq = drive.build_sequence(dp.parse(GOOD))   # human_gates: [after-req]
    assert seq[0]["human_gate_after"] == "after-req"
    assert seq[1]["human_gate_after"] is None


def test_dropped_stage_excluded():
    plan = dp.parse(GOOD)
    plan["stages"][2]["on"] = False
    seq = drive.build_sequence(plan)
    assert [s["emp"] for s in seq] == ["req-architect", "dev-engineer"]


def test_dispatch_cmds_are_cli_argv_lists():
    seq = drive.build_sequence(dp.parse(GOOD))
    s0 = seq[0]
    assert s0["dispatch_start_cmd"][0] == "dispatch-start"
    assert "--dispatch-id" in s0["dispatch_start_cmd"]
    assert s0["dispatch_done_cmd"][0] == "dispatch-done"
