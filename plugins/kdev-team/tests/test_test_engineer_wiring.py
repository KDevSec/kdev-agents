from pathlib import Path

KT = Path(__file__).resolve().parents[1]
REF = KT / "skills/kdev-flow-driver/references"
NAR = REF / "node-agent-routing.md"
GDL = REF / "gate-decision-logic.md"
SKILL = KT / "skills/kdev-flow-driver/SKILL.md"
ORCH = KT / "agents/reviewer-orchestrator.md"


def test_node_routing_has_test_engineer_section():
    t = NAR.read_text(encoding="utf-8")
    assert "test-engineer" in t
    assert "kdev-team:test-engineer-points" in t
    assert "黑盒" in t and ("禁读" in t or "不读" in t)


def test_node_routing_reviewer_dispatch_lists_test_caps():
    t = NAR.read_text(encoding="utf-8")
    assert "test-design" in t and "test-coverage" in t


def test_gate_logic_has_test_engineer_gates():
    t = GDL.read_text(encoding="utf-8")
    assert "g-test-design-review" in t and "g-test-coverage-review" in t
    assert "黑盒" in t


def test_skill_24ter_lists_test_engineer_producer():
    t = SKILL.read_text(encoding="utf-8")
    assert "test-engineer" in t and "黑盒" in t


def test_reviewer_orchestrator_routes_test_caps():
    t = ORCH.read_text(encoding="utf-8")
    assert "test-design" in t and "test-coverage" in t
    assert "test-engineer:g-test-design-review" in t
