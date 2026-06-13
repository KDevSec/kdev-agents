from pathlib import Path
import yaml
from kdev_core import node_machine

KT = Path(__file__).resolve().parents[1]
DESIGN_NT = KT / "orchestration/test-engineer.design.node-table.yml"
EXEC_NT = KT / "orchestration/test-engineer.exec.node-table.yml"
GATE_KINDS = {"review", "decision", "acceptance"}


def _load(p):
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_design_flow_loads_6_nodes():
    data, table = _load(DESIGN_NT)
    assert data["flow"] == "test-design-flow"
    assert len(table["nodes"]) == 6
    assert table["terminal_fail"] == "n-fail"


def test_exec_flow_loads_5_nodes():
    data, table = _load(EXEC_NT)
    assert data["flow"] == "test-exec-flow"
    assert len(table["nodes"]) == 5
    assert table["terminal_fail"] == "n-fail"


def test_design_review_gate_reviewer_expert():
    data, _ = _load(DESIGN_NT)
    spec = data["gate_specs"]["g-test-design-review"]
    assert spec["kind"] == "review"
    assert spec["reviewer"] == "reviewer-expert"
    assert spec["on_pass"] == "n3-merge"
    assert spec["on_reflow"] == "n0-points"


def test_coverage_review_gate_reviewer_expert():
    data, _ = _load(EXEC_NT)
    spec = data["gate_specs"]["g-test-coverage-review"]
    assert spec["kind"] == "review"
    assert spec["reviewer"] == "reviewer-expert"
    assert spec["on_pass"] == "n2-report"
    assert spec["on_reflow"] == "n0-ui-auto"


def test_every_gate_has_spec_and_valid_targets():
    for p in (DESIGN_NT, EXEC_NT):
        data, table = _load(p)
        specs = data["gate_specs"]
        nodes = set(table["nodes"])
        for nid, n in table["nodes"].items():
            if n["kind"] == "gate":
                assert n["gate"] in specs, f"{nid} gate 无 spec"
        for gid, spec in specs.items():
            assert spec["kind"] in GATE_KINDS
            targets = (list(spec.get("branches", {}).values())
                       + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
            for tgt in targets:
                assert tgt in nodes, f"{gid} -> 未知节点 {tgt}"
            assert spec["reviewer"] in {"self", "reviewer-expert"}
