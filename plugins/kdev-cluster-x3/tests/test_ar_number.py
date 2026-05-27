import pytest
from kdev_cluster_x3.lib.ar_number import parse_ar, is_valid_ar, ArInvalid


@pytest.mark.parametrize("s", [
    "AR-AUTH-01.001.001",
    "AR-PROD_LINE-99.999.999",
    "AR-X-1.001.001",
])
def test_valid(s):
    assert is_valid_ar(s)
    p = parse_ar(s)
    assert p.major >= 1 and p.minor >= 1 and p.patch >= 1


@pytest.mark.parametrize("s,reason", [
    ("AR-auth-01.001.001", "domain lowercase"),
    ("AR-AUTH-1.1.1",      "minor/patch must be 3 digits"),
    ("AR-AUTH-01-001-001", "must use dot separator"),
    ("AUTH-01.001.001",    "missing AR- prefix"),
    ("AR--01.001.001",     "empty domain"),
    ("",                    "empty"),
])
def test_invalid(s, reason):
    assert not is_valid_ar(s), f"should fail because: {reason}"
    with pytest.raises(ArInvalid):
        parse_ar(s)


def test_parse_extracts_components():
    p = parse_ar("AR-PROD_LINE-12.345.067")
    assert p.domain == "PROD_LINE"
    assert (p.major, p.minor, p.patch) == (12, 345, 67)
    assert p.canonical == "AR-PROD_LINE-12.345.067"
