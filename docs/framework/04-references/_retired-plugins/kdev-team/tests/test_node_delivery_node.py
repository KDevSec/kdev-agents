# plugins/kdev-team/tests/test_node_delivery_node.py
from pathlib import Path
import yaml

ORCH = Path(__file__).resolve().parents[1] / "orchestration"

EXPECTED = {
    "req-architect.node-table.yml": "n8-merge",
    "dev-engineer.node-table.yml": "n11-merge",
    "test-engineer.design.node-table.yml": "n3-merge",
    "test-engineer.exec.node-table.yml": "n2-report",
}


def test_kdev_team_package_importable():
    import kdev_team  # noqa: F401


def test_each_node_table_declares_delivery_node():
    for fname, expected in EXPECTED.items():
        data = yaml.safe_load((ORCH / fname).read_text(encoding="utf-8"))
        assert data.get("delivery_node") == expected, fname
        # delivery_node 必须是表里真实存在的节点 id
        ids = {n["id"] for n in data["nodes"]}
        assert expected in ids, f"{fname}: {expected} not a real node"
