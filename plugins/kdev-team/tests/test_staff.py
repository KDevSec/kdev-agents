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


def test_kind_discriminator_on_all_employees():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emps = d["employees"]
    assert emps["dev-engineer"]["kind"] == "flow-owner"
    assert emps["req-architect"]["kind"] == "flow-owner"
    assert emps["reviewer"]["kind"] == "callee"
    assert emps["test-engineer"]["kind"] == "flow-owner"


def test_reviewer_callee_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["reviewer"]
    assert emp["display"] == "评审专家"
    assert emp["kind"] == "callee"
    assert emp["dispatch_table"] == "orchestration/reviewer.dispatch-table.yml"
    assert "node_table" not in emp, "callee 不应有 node_table（用 dispatch_table）"
    assert emp["flow_skill"] is None, "callee 无方法论 flow-skill"
    assert emp["standards_dir"] == "standards/reviewer/"
    assert len(emp["agents"]) == 7  # orchestrator + 6 cap
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"


def test_flow_owner_keeps_node_table_callee_has_none():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    for fid in ("dev-engineer", "req-architect"):
        assert "node_table" in d["employees"][fid]
        assert "dispatch_table" not in d["employees"][fid]


def test_test_engineer_entry():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))
    emp = d["employees"]["test-engineer"]
    assert emp["display"] == "测试工程师"
    assert emp["kind"] == "flow-owner"
    assert emp["flow_skill"] is None
    assert "node_table" not in emp, "多 flow flow-owner 用 node_tables（复数）"
    nt = emp["node_tables"]
    assert set(nt) == {"test-design-flow", "test-exec-flow"}
    assert emp["default_flow"] == "test-design-flow"
    KT = Path(__file__).resolve().parents[1]
    for path in nt.values():
        assert (KT / path).exists(), f"node_tables 路径不存在: {path}"
    assert len(emp["agents"]) == 4
    for a in emp["agents"]:
        assert (AGENTS / f"{a}.md").exists(), f"花名册引用的 agent 不存在: {a}"


def test_every_flow_owner_has_one_table_kind_callee_has_dispatch():
    d = yaml.safe_load(STAFF.read_text(encoding="utf-8"))["employees"]
    for fid, emp in d.items():
        if emp["kind"] == "flow-owner":
            has_single = "node_table" in emp
            has_multi = "node_tables" in emp
            assert has_single ^ has_multi, f"{fid}: flow-owner 须恰有 node_table 或 node_tables 之一"
            assert "dispatch_table" not in emp, f"{fid}: flow-owner 不应有 dispatch_table"
        elif emp["kind"] == "callee":
            assert "dispatch_table" in emp
            assert "node_table" not in emp and "node_tables" not in emp
