from pathlib import Path

SKILL = (Path(__file__).resolve().parents[2]
         / "kdev-coding-flow/skills/kdev-coding-flow/SKILL.md")
ORCH = Path(__file__).resolve().parents[1] / "agents/dev-engineer-orchestrator.md"


def test_skill_points_to_kdev_team_not_embeds_orchestration():
    text = SKILL.read_text(encoding="utf-8")
    # 方法论保留（13 节点仍在），但编排/persona 落点指向 kdev-team、不再自带 personas/orchestration 驱动块
    assert "kdev-team" in text                         # 指针存在
    assert "skills/kdev-coding-flow/personas" not in text  # 旧 persona 路径清除
    # 编排 CLI 驱动命令不再堆在 SKILL（归 orchestrator agent）
    assert "python -m kdev_core advance" not in text


def test_orchestrator_agent_owns_drive_commands():
    text = ORCH.read_text(encoding="utf-8")
    assert "python -m kdev_core" in text
    assert "dev-engineer.node-table.yml" in text
