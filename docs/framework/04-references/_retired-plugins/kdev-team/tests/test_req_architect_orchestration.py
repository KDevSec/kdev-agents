from pathlib import Path
import yaml
from kdev_core import node_machine

NT = Path(__file__).resolve().parents[1] / "orchestration/req-architect.node-table.yml"
GATE_KINDS = {"review", "decision", "acceptance"}


def _load():
    data = yaml.safe_load(NT.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_node_table_loads_and_has_11_nodes():
    data, table = _load()
    # 6 action(n0/n1/n3/n4/n6/n8) + 3 gate(n2/n5/n7) + 2 terminal(n9-done/n-fail)
    assert len(table["nodes"]) == 11
    assert table["flow"] == "design-flow"
    assert table["terminal_fail"] == "n-fail"


def test_sop_chain_ir_sr_ar_proto_design():
    """IR→SR→(SR评审)→AR→原型→(AR+原型评审)→方案→(方案评审)→聚合→done。"""
    data, table = _load()
    adj = table["adjacency"]
    assert adj["n0-clarify"] == ["n1-spec"]
    assert adj["n1-spec"] == ["n2-sr-review"]
    assert adj["n3-decompose"] == ["n4-prototype"]
    assert adj["n4-prototype"] == ["n5-ar-proto-review"]
    assert adj["n6-design"] == ["n7-design-review"]
    assert adj["n8-merge"] == ["n9-done"]


def test_three_review_gates_bound_to_reviewer_expert():
    """3 闸翻 reviewer-expert（兑现评审专家，Q-016/spec v0.2）；L1 可回退 self。"""
    data, table = _load()
    specs = data["gate_specs"]
    assert set(specs) == {"g-sr-review", "g-ar-proto-review", "g-design-review"}
    for gid, spec in specs.items():
        assert spec["kind"] == "review", f"{gid} 应是 review gate"
        assert spec["reviewer"] == "reviewer-expert", f"{gid} 应翻 reviewer-expert（兑现评审专家）"


def test_gate_pass_reflow_targets():
    data, table = _load()
    specs = data["gate_specs"]
    assert specs["g-sr-review"]["on_pass"] == "n3-decompose"
    assert specs["g-sr-review"]["on_reflow"] == "n1-spec"
    assert specs["g-ar-proto-review"]["on_pass"] == "n6-design"
    assert specs["g-ar-proto-review"]["on_reflow"] == "n4-prototype"
    assert specs["g-design-review"]["on_pass"] == "n8-merge"
    assert specs["g-design-review"]["on_reflow"] == "n6-design"


def test_every_gate_node_has_a_gate_spec():
    data, table = _load()
    specs = data["gate_specs"]
    for nid, n in table["nodes"].items():
        if n["kind"] == "gate":
            assert n["gate"] in specs, f"gate {n['gate']} not in gate_specs"


def test_gate_specs_targets_valid_and_reviewer_bound():
    data, table = _load()
    nodes = set(table["nodes"])
    for gid, spec in data["gate_specs"].items():
        assert spec["kind"] in GATE_KINDS
        targets = (list(spec.get("branches", {}).values())
                   + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
        for tgt in targets:
            assert tgt in nodes, f"{gid} -> unknown node {tgt}"
        assert spec["reviewer"] in {"self", "reviewer-expert"}


def test_req_review_gates_bound_to_reviewer_expert():
    import yaml
    from pathlib import Path
    nt = Path(__file__).resolve().parents[1] / "orchestration/req-architect.node-table.yml"
    specs = yaml.safe_load(nt.read_text(encoding="utf-8"))["gate_specs"]
    for g in ("g-sr-review", "g-ar-proto-review", "g-design-review"):
        assert specs[g]["reviewer"] == "reviewer-expert", f"{g} 应翻 reviewer-expert（兑现评审专家）"
