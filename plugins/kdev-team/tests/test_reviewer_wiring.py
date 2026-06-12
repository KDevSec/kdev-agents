from pathlib import Path

REF = Path(__file__).resolve().parents[1] / "skills/kdev-flow-driver/references"
GDL = REF / "gate-decision-logic.md"
NAR = REF / "node-agent-routing.md"


def test_gate_logic_dev_gates_no_longer_deferred():
    text = GDL.read_text(encoding="utf-8")
    # dev3 不再「全 deferred」；出现真发函语义
    assert "reviewer-orchestrator" in text
    assert "发函" in text or "dispatch" in text
    # 不再把 g-code-review 当 deferred PASS
    assert "deferred:阶段3-评审专家" not in text or "已兑现" in text


def test_node_routing_has_reviewer_dispatch_section():
    text = NAR.read_text(encoding="utf-8")
    assert "reviewer" in text.lower()
    assert "kdev-team:reviewer-orchestrator" in text
    assert "handoffs/reviewer/" in text
