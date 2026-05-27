import pytest
from pathlib import Path
from kdev_cluster_x3.lib.agent_lint import lint_agent_dir, LintError

ROOT = Path(__file__).parent.parent


def test_no_agents_yet_is_ok():
    # Sanity: before agents exist, the linter should not crash.
    issues = lint_agent_dir(ROOT / "agents")
    # 0 issues OK, just must not raise.
    assert isinstance(issues, list)


def test_lint_catches_missing_frontmatter(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("# 没有 frontmatter\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("frontmatter" in i.msg for i in issues)


def test_lint_catches_bad_model(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: bad\ndescription: x\ntools: Read\nmodel: gpt-4\n---\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("model" in i.msg for i in issues)


def test_lint_catches_name_mismatch(tmp_path):
    bad = tmp_path / "实际名.md"
    bad.write_text("---\nname: 错的\ndescription: x\ntools: Read\nmodel: opus\n---\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("filename" in i.msg or "name mismatch" in i.msg for i in issues)
