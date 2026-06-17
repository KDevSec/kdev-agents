from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/kdev-team/SKILL.md"
CMD = ROOT / "commands/kdev-team.md"


def test_skill_and_command_files_exist():
    assert SKILL.exists()
    assert CMD.exists()


def test_skill_frontmatter_has_name_and_description():
    txt = SKILL.read_text(encoding="utf-8")
    assert txt.startswith("---")
    assert "name:" in txt.split("---", 2)[1]
    assert "description:" in txt.split("---", 2)[1]


def test_skill_documents_three_phase_loop_and_hard_constraint():
    txt = SKILL.read_text(encoding="utf-8")
    for kw in ("plan", "confirm", "drive"):
        assert kw in txt
    # 硬约束：子 agent 不能再开子 agent / flow-driver 跑主会话
    assert "子 agent" in txt and "主会话" in txt
    # 复用现有资产、不开 CEO subagent
    assert "kdev-flow-driver" in txt
    # 诚实债明示
    assert "review-mode" in txt or "评审开关" in txt
    assert "不可恢复" in txt or "断点续跑" in txt


def test_command_frontmatter_argument_hint():
    txt = CMD.read_text(encoding="utf-8")
    assert "argument-hint:" in txt
    assert "kdev-team" in txt or "kdev-ceo" in txt
