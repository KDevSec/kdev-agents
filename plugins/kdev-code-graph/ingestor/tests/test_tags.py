import pytest

from kdev_ingestor.tags import (
    KDEV_PREFIX,
    KIND_SECURITY_RULE,
    KIND_VULNERABILITY,
    KIND_COMPLIANCE,
    make_tag,
    parse_tag,
    is_kdev_tag,
    has_kind,
    extract_kind,
    extract_value,
    InvalidTagError,
)


def test_prefix_constant():
    assert KDEV_PREFIX == "kdev:"


def test_make_tag_kind_only():
    assert make_tag(KIND_SECURITY_RULE) == "kdev:security_rule"


def test_make_tag_kind_with_value():
    assert make_tag("category", "input_validation") == "kdev:category:input_validation"


def test_make_tag_rejects_uppercase_value():
    with pytest.raises(InvalidTagError):
        make_tag("rule_id", "Foo.BAR")


def test_make_tag_rejects_empty_kind():
    with pytest.raises(InvalidTagError):
        make_tag("")


def test_make_tag_allows_dots_dashes_underscores():
    assert make_tag("rule_id", "3.1.1") == "kdev:rule_id:3.1.1"
    assert make_tag("source", "kdev-secure-coding") == "kdev:source:kdev-secure-coding"


def test_parse_tag_kind_only():
    assert parse_tag("kdev:security_rule") == ("security_rule", None)


def test_parse_tag_kind_value():
    assert parse_tag("kdev:rule_id:3.1.1") == ("rule_id", "3.1.1")


def test_parse_tag_rejects_non_kdev():
    with pytest.raises(InvalidTagError):
        parse_tag("foo:bar")


def test_parse_tag_rejects_value_with_extra_colon():
    # parse_tag must round-trip safely with make_tag — values that contain ':'
    # cannot be produced by make_tag, so parse_tag must reject them too.
    with pytest.raises(InvalidTagError):
        parse_tag("kdev:rule_id:3.1.1:extra")


def test_parse_tag_rejects_value_with_uppercase():
    with pytest.raises(InvalidTagError):
        parse_tag("kdev:rule_id:Foo.BAR")


def test_is_kdev_tag():
    assert is_kdev_tag("kdev:security_rule") is True
    assert is_kdev_tag("kdev:rule_id:3.1.1") is True
    assert is_kdev_tag("python") is False
    assert is_kdev_tag("") is False
    assert is_kdev_tag("kdev:") is False


def test_has_kind_finds_security_rule():
    tags = ["python", "kdev:security_rule", "kdev:rule_id:3.1.1"]
    assert has_kind(tags, KIND_SECURITY_RULE) is True
    assert has_kind(tags, KIND_VULNERABILITY) is False


def test_extract_kind_returns_first_kind_only_tag():
    tags = ["kdev:rule_id:3.1.1", "kdev:security_rule", "python"]
    assert extract_kind(tags) == "security_rule"


def test_extract_kind_returns_none_when_absent():
    assert extract_kind(["python", "flask"]) is None


def test_extract_value_first_match():
    tags = ["kdev:rule_id:3.1.1", "kdev:security_rule", "kdev:rule_id:3.1.2"]
    assert extract_value(tags, "rule_id") == "3.1.1"


def test_extract_value_returns_none_when_absent():
    assert extract_value(["kdev:security_rule"], "rule_id") is None


def test_kind_constants_are_exact_strings():
    assert KIND_SECURITY_RULE == "security_rule"
    assert KIND_VULNERABILITY == "vulnerability"
    assert KIND_COMPLIANCE == "compliance"
