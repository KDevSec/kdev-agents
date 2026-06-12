from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
DT = ROOT / "orchestration/reviewer.dispatch-table.yml"
AGENTS = ROOT / "agents"
DEV_NT = ROOT / "orchestration/dev-engineer.node-table.yml"
REQ_NT = ROOT / "orchestration/req-architect.node-table.yml"

EXPECTED_CAPS = {"sr", "story", "prototype", "design", "code", "security"}


def _dt():
    return yaml.safe_load(DT.read_text(encoding="utf-8"))


def test_dispatch_table_has_6_caps_with_schema():
    caps = _dt()["capabilities"]
    assert {c["cap"] for c in caps} == EXPECTED_CAPS
    for c in caps:
        for key in ("cap", "agent", "standards", "threshold", "target", "caller_gate"):
            assert key in c, f"{c.get('cap')} 缺字段 {key}"
        assert isinstance(c["threshold"], int) and 0 < c["threshold"] <= 100
        assert isinstance(c["caller_gate"], list) and c["caller_gate"]


def test_each_cap_agent_file_exists():
    for c in _dt()["capabilities"]:
        assert (AGENTS / f"{c['agent']}.md").exists(), f"agent 不存在: {c['agent']}"


def test_each_cap_standards_file_exists():
    for c in _dt()["capabilities"]:
        assert (ROOT / c["standards"]).exists(), f"standards 不存在: {c['standards']}"


def test_caller_gate_refs_real_gates():
    """dispatch-table 声明的 caller_gate 必须是真实存在的 gate（dev/req node-table 的 gate_specs）。"""
    dev = yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"]
    req = yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"]
    known = {f"dev-engineer:{g}" for g in dev} | {f"req-architect:{g}" for g in req}
    for c in _dt()["capabilities"]:
        for cg in c["caller_gate"]:
            assert cg in known, f"{c['cap']} 引用了不存在的 caller_gate: {cg}"


def test_review_gates_covered_by_some_cap():
    """dev/req 的每个 review-kind gate 都至少被一个 cap 认领（无悬空 reviewer-expert gate）。

    仅统计**委派 reviewer-expert** 的 review gate（reviewer != self）：`g-verify`
    是 kind=review 但 reviewer=self 的自验证 gate（TDD 真过/完成验证由被评审员工自检），
    本就不该被评审专家 cap 认领（spec §4.1 只列 6 个第三方评审 gate）。
    """
    dev = yaml.safe_load(DEV_NT.read_text(encoding="utf-8"))["gate_specs"]
    req = yaml.safe_load(REQ_NT.read_text(encoding="utf-8"))["gate_specs"]
    review_gates = {
        f"dev-engineer:{g}" for g, s in dev.items()
        if s["kind"] == "review" and s.get("reviewer") != "self"
    }
    review_gates |= {
        f"req-architect:{g}" for g, s in req.items()
        if s["kind"] == "review" and s.get("reviewer") != "self"
    }
    claimed = set()
    for c in _dt()["capabilities"]:
        claimed |= set(c["caller_gate"])
    missing = review_gates - claimed
    assert not missing, f"这些 review gate 没有 cap 认领: {missing}"
