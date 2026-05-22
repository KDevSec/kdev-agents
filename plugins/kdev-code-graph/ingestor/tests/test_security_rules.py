from pathlib import Path

import pytest

from kdev_ingestor.security_rules import (
    SecurityRule,
    parse_rule_file,
    parse_rules_dir,
    rule_to_node,
    RuleParseError,
)


def test_parse_rule_file_returns_rules(sample_rules_dir: Path):
    rules = parse_rule_file(sample_rules_dir / "01-input-validation.md")
    assert len(rules) == 2
    assert rules[0].rule_id == "3.1.1"
    assert rules[0].title == "命令操作安全"
    assert rules[1].rule_id == "3.1.2"


def test_parse_rule_file_extracts_first_bullet_as_summary(sample_rules_dir: Path):
    rules = parse_rule_file(sample_rules_dir / "01-input-validation.md")
    # Summary should be the first bullet of `### 规则`, not heading or H1.
    assert not rules[0].summary.startswith("#")
    assert "外部数据" in rules[0].summary
    assert "参数化查询" in rules[1].summary


def test_parse_rule_file_extracts_category(sample_rules_dir: Path):
    rules = parse_rule_file(sample_rules_dir / "01-input-validation.md")
    assert all(r.category == "input_validation" for r in rules)


def test_parse_rule_file_missing_raises(tmp_path: Path):
    with pytest.raises(RuleParseError, match="not found"):
        parse_rule_file(tmp_path / "nope.md")


def test_parse_rule_file_skips_when_no_rules_section(tmp_path: Path):
    bad = tmp_path / "02-empty.md"
    bad.write_text(
        "# 3.2 Stub\n\n## 3.2.1 No rules\n\nJust prose, no rules section.\n",
        encoding="utf-8",
    )
    rules = parse_rule_file(bad)
    assert rules == []


def test_parse_rules_dir_aggregates_files(sample_rules_dir: Path):
    rules = parse_rules_dir(sample_rules_dir)
    assert len(rules) == 2
    assert {r.rule_id for r in rules} == {"3.1.1", "3.1.2"}


def test_parse_rules_dir_handles_empty(tmp_path: Path):
    assert parse_rules_dir(tmp_path) == []


def test_rule_to_node_minimum_fields(sample_rules_dir: Path):
    rule = parse_rule_file(sample_rules_dir / "01-input-validation.md")[0]
    node = rule_to_node(rule)
    assert node["id"] == "kdev-sec:rule:3.1.1"
    assert node["type"] == "concept"
    assert node["name"] == "命令操作安全"
    assert "kdev:security_rule" in node["tags"]
    assert "kdev:rule_id:3.1.1" in node["tags"]
    assert "kdev:category:input_validation" in node["tags"]
    assert "kdev:source:kdev-secure-coding" in node["tags"]
    assert node["complexity"] in {"simple", "moderate", "complex"}


def test_rule_to_node_summary_non_empty(sample_rules_dir: Path):
    rule = parse_rule_file(sample_rules_dir / "01-input-validation.md")[0]
    node = rule_to_node(rule)
    assert len(node["summary"]) > 0


def test_security_rule_dataclass_fields():
    rule = SecurityRule(
        rule_id="3.1.1",
        title="x",
        summary="y",
        category="input_validation",
        source_file=Path("/tmp/x.md"),
    )
    assert rule.rule_id == "3.1.1"


def test_parse_rule_file_extracts_patterns(sample_rules_dir: Path):
    rules = parse_rule_file(sample_rules_dir / "01-input-validation.md")
    assert rules[0].patterns == ["flagged_call", "risky_run", "tainted_load"]
    # 3.1.2 没有"适用场景"段 → 空 patterns
    assert rules[1].patterns == []


def test_security_rule_patterns_default_empty():
    rule = SecurityRule(
        rule_id="3.1.1", title="x", summary="y",
        category="input_validation", source_file=Path("/tmp/x.md"),
    )
    assert rule.patterns == []
