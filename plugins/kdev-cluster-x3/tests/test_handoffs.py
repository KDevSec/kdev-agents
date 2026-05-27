import pytest
from datetime import datetime, timezone
from kdev_cluster_x3.lib.handoffs import (
    write_complete, read_complete, HandoffMissing, HandoffMalformed, GROUPS,
)


def test_write_complete_for_each_group(tmp_kdev):
    when = datetime(2026, 5, 27, tzinfo=timezone.utc)
    for g in GROUPS:
        kwargs = {"feature_slug": "demo"}
        if g == "reqs":   kwargs["ar_count"] = 12
        if g == "dev":    kwargs["commits_count"] = 7
        if g == "test":   kwargs.update(total_cases=20, passed_cases=20)
        if g == "review": kwargs["verdict"] = "pass"
        write_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md", group=g, completed_at=when, **kwargs)
    for g in GROUPS:
        meta = read_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md")
        assert meta["group"] == g
        assert meta["status"] == "complete"


def test_read_missing_raises(tmp_kdev):
    with pytest.raises(HandoffMissing):
        read_complete(tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md")


def test_read_malformed_raises(tmp_kdev):
    path = tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md"
    path.write_text("no frontmatter here\n", encoding="utf-8")
    with pytest.raises(HandoffMalformed):
        read_complete(path)


def test_write_unknown_group_raises(tmp_kdev):
    with pytest.raises(ValueError, match="unknown group"):
        write_complete(tmp_kdev / "x.md", group="bogus", completed_at=datetime.now(timezone.utc), feature_slug="x")
