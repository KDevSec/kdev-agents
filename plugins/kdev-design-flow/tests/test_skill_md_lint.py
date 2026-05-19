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
    "stage3-prototype-prompt.md",
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


def test_stage3_extracts_constitution_ui_rules():
    """Per v0.2.0 fix: Stage 3 was diverging because frontend-design was getting a
    generic prompt — it didn't know about the project's constitution-level UI rules
    (UED spec, 8px grid, token colors, AAA contrast). The new Stage 3 MUST have a
    pre-step that reads .specify/memory/constitution.md and injects extracted UI
    constraints into the frontend-design prompt. Without this, prototypes drift."""
    _, body = _read_skill()
    stage3_idx = body.find("Stage 3: 原型设计")
    assert stage3_idx > 0, "Stage 3 section missing"
    # Find next Stage to bound the search
    stage4_idx = body.find("Stage 4:", stage3_idx)
    stage3_section = body[stage3_idx:stage4_idx if stage4_idx > 0 else None]
    # Must mention constitution file lookup
    assert ".specify/memory/constitution.md" in stage3_section, \
        "Stage 3 must explicitly read .specify/memory/constitution.md to extract UI rules"
    # Must mention the new template file
    assert "stage3-prototype-prompt.md" in stage3_section, \
        "Stage 3 must use the stage3-prototype-prompt.md template (not hard-coded prompt)"
    # Must mention design system reference detection
    assert "design" in stage3_section.lower() and "references" in stage3_section.lower(), \
        "Stage 3 must scan references/ for design system directories"


def test_gate2_has_constitution_compliance_criterion():
    """Per v0.2.0 fix: Gate 2 review criteria must include a C-2.6 that checks
    constitution UI compliance, otherwise reviews PASS divergent prototypes."""
    gate_md = REF_DIR / "review-gate-prompt.md"
    text = gate_md.read_text(encoding="utf-8")
    assert "C-2.6" in text, "Gate 2 must have a C-2.6 constitution-compliance criterion"
    # The criterion text must mention the constitution file path
    c26_idx = text.find("C-2.6")
    c26_section = text[c26_idx:c26_idx + 800]
    assert "constitution.md" in c26_section, \
        "C-2.6 must reference .specify/memory/constitution.md explicitly"
