"""Lint tests for SKILL.md — frontmatter validity + cross-references resolve."""
from pathlib import Path

import pytest
import yaml

PLUGIN = Path(__file__).resolve().parent.parent
SKILL_MD = PLUGIN / "skills" / "kdev-design-flow" / "SKILL.md"
REF_DIR = PLUGIN / "skills" / "kdev-design-flow" / "references"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md missing frontmatter delimiters")
    return yaml.safe_load(parts[1]), parts[2]


def _read_skill():
    return _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))


def test_frontmatter_has_required_fields():
    fm, _ = _read_skill()
    assert fm.get("name") == "kdev-design-flow"
    assert "description" in fm and len(fm["description"]) > 50


def test_description_mentions_skip_branches():
    """description must explicitly say what NOT to trigger on (per spec §3.2)."""
    fm, _ = _read_skill()
    assert "SKIP" in fm["description"] or "skip" in fm["description"].lower()


def test_description_mentions_three_review_modes():
    """description must mention the three review modes so callers know they exist."""
    fm, _ = _read_skill()
    desc = fm["description"]
    assert "ai" in desc.lower() and "both" in desc.lower() and "human" in desc.lower()


@pytest.mark.parametrize("ref_name", [
    "stage1-sr-prompt.md",
    "stage1-sr-template.md",
    "review-gate-prompt.md",
    "output-merge-rules.md",
])
def test_referenced_files_exist(ref_name):
    """All references/* files mentioned in SKILL.md must actually exist on disk."""
    _, body = _read_skill()
    assert ref_name in body, f"SKILL.md does not reference {ref_name}"
    assert (REF_DIR / ref_name).exists(), f"{ref_name} referenced but not on disk"


def test_skill_md_does_not_mention_codex():
    """v0.1 explicitly does not depend on codex (per spec patch from user feedback)."""
    fm, body = _read_skill()
    assert "codex" not in fm["description"].lower()
    assert "codex" not in body.lower()


def test_skill_md_mentions_all_three_stages():
    _, body = _read_skill()
    assert "Stage 1" in body
    assert "Stage 2" in body
    assert "Stage 3" in body
    assert "Stage 4" in body
    assert "Gate 1" in body
    assert "Gate 2" in body
    assert "Gate 3" in body


def test_resume_section_handles_missing_state():
    """Per v0.1.1 fix (B02 eval finding): the 恢复模式 section must explicitly
    handle the case where flow-state.json doesn't exist — i.e., must mention
    FlowStateError or the missing-slug user-facing error path. Otherwise users
    typing `--resume <wrong-slug>` will hit an uncaught traceback."""
    _, body = _read_skill()
    resume_idx = body.find("恢复模式")
    assert resume_idx > 0, "恢复模式 section missing from SKILL.md"
    resume_section = body[resume_idx:]
    # Must reference FlowStateError handling OR the user-facing 找不到 slug message
    assert ("FlowStateError" in resume_section) or (
        "找不到" in resume_section and "slug" in resume_section
    ), "恢复模式 section must explicitly handle missing flow-state.json (the B02 bug)"


def test_description_clarifies_resume_belongs_here():
    """Per v0.1.1 fix (T07 eval finding): the description must explicitly tell
    Claude that --resume belongs to this skill (not superpowers:executing-plans),
    otherwise resume queries get routed away."""
    fm, _ = _read_skill()
    desc = fm["description"]
    # Description must mention resume IS part of this skill, not just routed away
    assert "resume" in desc.lower() or "恢复" in desc or "继续" in desc, \
        "description must mention --resume / 恢复 / 继续 to capture that workflow"
