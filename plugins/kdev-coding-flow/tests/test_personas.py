from pathlib import Path

PERSONA_DIR = (Path(__file__).resolve().parents[1]
               / "skills/kdev-coding-flow/personas")
REQUIRED = ["## Identity", "## Principles", "## Critical Actions", "## Capabilities"]
EXPECTED = ["开发工程师-编排", "环境准备", "实施计划",
            "前端实现", "E2E视觉验收", "部署上线", "安全扫描"]


def test_all_7_personas_exist():
    names = {p.stem for p in PERSONA_DIR.glob("*.md")}
    for e in EXPECTED:
        assert e in names, f"缺 persona: {e}"


def test_each_persona_has_required_sections():
    for p in PERSONA_DIR.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        for sec in REQUIRED:
            assert sec in text, f"{p.name} 缺段落 {sec}"


def test_orchestrator_critical_action_mentions_cli():
    text = (PERSONA_DIR / "开发工程师-编排.md").read_text(encoding="utf-8")
    # 编排纪律：每过节点/gate 必调 CLI（补 CLI 靠自觉短板）
    assert "kdev_core" in text and "record-gate" in text
