from pathlib import Path
import yaml

STAFF = Path(__file__).resolve().parents[1] / "staff.yml"
AGENTS = Path(__file__).resolve().parents[1] / "agents"


def test_dev_engineer_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["dev-engineer"]
    assert emp["display"] == "开发工程师"
    assert emp["flow_skill"] == "kdev-coding-flow"
    assert emp["node_table"] == "orchestration/dev-engineer.node-table.yml"
    # 花名册列的每个 agent 文件都在
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"


def test_req_architect_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["req-architect"]
    assert emp["display"] == "需求架构师"
    assert emp["flow_skill"] == "kdev-design-flow"
    assert emp["node_table"] == "orchestration/req-architect.node-table.yml"
    assert len(emp["agents"]) == 6
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"
