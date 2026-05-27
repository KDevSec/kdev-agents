from pathlib import Path
import re

ROOT = Path(__file__).parent.parent


def test_all_skills_have_frontmatter():
    for skill_md in ROOT.glob("skills/*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        assert m, f"{skill_md} missing yaml frontmatter"
        fm = dict(line.partition(":")[::2] for line in m.group(1).splitlines() if ":" in line)
        assert "name" in {k.strip() for k in fm}, f"{skill_md} missing name field"
        assert "description" in {k.strip() for k in fm}, f"{skill_md} missing description field"


def test_all_commands_have_frontmatter():
    for cmd_md in ROOT.glob("commands/*.md"):
        text = cmd_md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{cmd_md} missing yaml frontmatter"
        assert "description:" in text.split("---", 2)[1], f"{cmd_md} frontmatter missing description"
