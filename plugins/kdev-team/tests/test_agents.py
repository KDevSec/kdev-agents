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
