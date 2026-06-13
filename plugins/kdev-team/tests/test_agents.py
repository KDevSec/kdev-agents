import re
from pathlib import Path

AGENTS = Path(__file__).resolve().parents[1] / "agents"
DEV_AGENTS = [
    "dev-engineer-orchestrator", "dev-engineer-env", "dev-engineer-plan",
    "dev-engineer-frontend", "dev-engineer-e2e", "dev-engineer-deploy", "dev-engineer-sec",
]
SECTIONS = ["## Identity", "## Principles", "## Critical Actions", "## Capabilities"]


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    return m.group(1) if m else None


def test_all_7_dev_agents_exist():
    names = {p.stem for p in AGENTS.glob("dev-engineer-*.md")}
    for a in DEV_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_agent_has_frontmatter_and_sections():
    for a in DEV_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_orchestrator_drives_via_cli_and_node_table():
    text = (AGENTS / "dev-engineer-orchestrator.md").read_text(encoding="utf-8")
    # 编排=按 node-table 调度 + CLI 驱动（守 §2.4）
    assert "node-table" in text
    assert "kdev_core" in text and "record-gate" in text


REQ_AGENTS = [
    "req-architect-orchestrator", "req-architect-clarify", "req-architect-spec",
    "req-architect-decompose", "req-architect-prototype", "req-architect-design",
]


def test_all_6_req_agents_exist():
    names = {p.stem for p in AGENTS.glob("req-architect-*.md")}
    for a in REQ_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_req_agent_has_frontmatter_and_sections():
    for a in REQ_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_req_orchestrator_drives_via_cli_and_node_table():
    text = (AGENTS / "req-architect-orchestrator.md").read_text(encoding="utf-8")
    assert "node-table" in text
    assert "kdev_core" in text and "record-gate" in text


REVIEWER_AGENTS = [
    "reviewer-orchestrator", "reviewer-sr", "reviewer-story",
    "reviewer-prototype", "reviewer-design", "reviewer-code", "reviewer-security",
]


def test_all_7_reviewer_agents_exist():
    names = {p.stem for p in AGENTS.glob("reviewer-*.md")}
    for a in REVIEWER_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_reviewer_agent_has_frontmatter_and_sections():
    for a in REVIEWER_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_reviewer_orchestrator_callee_shape():
    text = (AGENTS / "reviewer-orchestrator.md").read_text(encoding="utf-8")
    # callee：读 dispatch-table、fan-out、仲裁、双重通过条件、record-gate --by reviewer-expert
    assert "dispatch-table" in text or "dispatch_table" in text
    assert "fan-out" in text or "fanout" in text or "并行" in text
    assert "仲裁" in text
    assert "双重" in text and "reviewer-expert" in text
    # callee 明确不复用 kdev-flow-driver（无自有 flow）
    assert "callee" in text


def test_cap_reviewers_are_read_only():
    for a in ["reviewer-sr", "reviewer-story", "reviewer-prototype",
              "reviewer-design", "reviewer-code", "reviewer-security"]:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        assert "只读" in text or "不改产物" in text or "不修改产物" in text, \
            f"{a} 须声明只读（守生产者隔离）"


TEST_AGENTS = [
    "test-engineer-orchestrator", "test-engineer-points",
    "test-engineer-cases", "test-engineer-ui",
]


def test_all_4_test_engineer_agents_exist():
    names = {p.stem for p in AGENTS.glob("test-engineer-*.md")}
    for a in TEST_AGENTS:
        assert a in names, f"缺 agent: {a}"


def test_each_test_engineer_agent_has_frontmatter_and_sections():
    for a in TEST_AGENTS:
        text = (AGENTS / f"{a}.md").read_text(encoding="utf-8")
        fm = _frontmatter(text)
        assert fm, f"{a} 缺 YAML frontmatter"
        assert f"name: {a}" in fm, f"{a} frontmatter name 不匹配文件名"
        assert "description:" in fm and "model:" in fm, f"{a} frontmatter 缺 description/model"
        for sec in SECTIONS:
            assert sec in text, f"{a} 缺段落 {sec}"


def test_test_engineer_orchestrator_drives_dual_flow_via_cli():
    text = (AGENTS / "test-engineer-orchestrator.md").read_text(encoding="utf-8")
    assert "node-table" in text
    assert "kdev_core" in text and "record-gate" in text
    assert "test-design-flow" in text and "test-exec-flow" in text


def test_points_agent_enforces_blackbox_independence():
    text = (AGENTS / "test-engineer-points.md").read_text(encoding="utf-8")
    assert "黑盒" in text
    assert "需求" in text and "原型" in text
    assert "禁读" in text or "不读" in text  # 禁读 src
    assert "kdev-test-points" in text


def test_business_agents_reference_capability_skills():
    assert "kdev-test-cases" in (AGENTS / "test-engineer-cases.md").read_text(encoding="utf-8")
    assert "kdev-ui-autotest" in (AGENTS / "test-engineer-ui.md").read_text(encoding="utf-8")
