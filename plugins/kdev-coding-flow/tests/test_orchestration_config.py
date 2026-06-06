from pathlib import Path

import yaml
from kdev_core import node_machine

NT = (Path(__file__).resolve().parents[1]
      / "skills/kdev-coding-flow/orchestration/node-table.yml")

GATE_KINDS = {"review", "decision", "acceptance"}


def _load():
    data = yaml.safe_load(NT.read_text(encoding="utf-8"))
    return data, node_machine.load_node_table(data)


def test_node_table_loads_and_has_16_nodes():
    data, table = _load()
    assert len(table["nodes"]) == 16
    assert table["terminal_fail"] == "n-fail"


def test_every_gate_node_has_a_gate_spec():
    data, table = _load()
    specs = data["gate_specs"]
    for nid, n in table["nodes"].items():
        if n["kind"] == "gate":
            assert n["gate"], f"gate node {nid} missing 'gate' id"
            assert n["gate"] in specs, f"gate {n['gate']} not in gate_specs"


def test_gate_specs_targets_are_valid_nodes():
    data, table = _load()
    nodes = set(table["nodes"])
    for gid, spec in data["gate_specs"].items():
        assert spec["kind"] in GATE_KINDS
        targets = (list(spec.get("branches", {}).values())
                   + [spec[k] for k in ("on_pass", "on_reflow") if k in spec])
        for tgt in targets:
            assert tgt in nodes, f"{gid} -> unknown node {tgt}"
        # reviewer 绑定必填：self（自评）或 reviewer-expert（第三方）
        assert spec["reviewer"] in {"self", "reviewer-expert"}


def test_third_party_review_gates_are_deferred_in_stage1():
    """第三方评审(reviewer-expert) 阶段1 必标 stage1: deferred。"""
    data, _ = _load()
    for gid, spec in data["gate_specs"].items():
        if spec["reviewer"] == "reviewer-expert":
            assert spec.get("stage1") == "deferred", f"{gid} 第三方评审须标 deferred"
