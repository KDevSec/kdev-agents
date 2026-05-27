import pytest
from datetime import datetime, timezone
from kdev_cluster_x3.lib.state_md import StateMd, GROUPS


def test_init_writes_template(tmp_kdev):
    path = tmp_kdev / "state.md"
    started = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    s = StateMd.init(path, feature="产品管理三层", slug="chan-pin-guan-li-san-ceng", started_at=started)
    text = path.read_text(encoding="utf-8")
    assert "feature: 产品管理三层" in text
    assert "feature_slug: chan-pin-guan-li-san-ceng" in text
    assert "feature_started_at: 2026-05-27T16:00:00+00:00" in text
    for g in GROUPS:
        assert f"## {g}" in text
        assert "status: pending" in text


def test_update_group_changes_status_and_step(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    s.update_group("reqs", status="in_progress", current_step="ir", last_progress="开始 IR 澄清")
    s.write(path)
    again = StateMd.read(path)
    assert again.groups["reqs"]["status"] == "in_progress"
    assert again.groups["reqs"]["current_step"] == "ir"
    assert again.groups["reqs"]["last_progress"] == "开始 IR 澄清"


def test_update_unknown_group_raises(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    with pytest.raises(ValueError, match="unknown group"):
        s.update_group("bogus", status="in_progress")


def test_last_progress_truncated_to_80_chars(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    long = "a" * 200
    s.update_group("dev", last_progress=long)
    assert len(s.groups["dev"]["last_progress"]) == 80


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        StateMd.read(tmp_path / "no-such.md")
