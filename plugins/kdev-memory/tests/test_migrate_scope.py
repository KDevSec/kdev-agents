"""test migrate_scope.py：flat → scoped，markdown 进 shared，state 留 root，幂等。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import migrate_scope  # noqa: E402
from migrate_scope import migrate_to_scoped  # noqa: E402


def _flat_repo(tmp_path):
    kdev = tmp_path / ".kdev"
    mem = kdev / "memory"
    mem.mkdir(parents=True)
    (mem / "执行日志.md").write_text("# log", encoding="utf-8")
    (mem / "决策日志.md").write_text("# q", encoding="utf-8")
    (mem / "踩坑日志.md").write_text("# g", encoding="utf-8")
    (mem / "skill-feedback.md").write_text("# f", encoding="utf-8")
    (mem / "当前状态.md").write_text("---\nphase: x\n---\n", encoding="utf-8")
    (mem / "改进建议.md").write_text("# r", encoding="utf-8")
    (mem / "每日汇总").mkdir()
    (mem / "每日汇总" / "2026-06-01.md").write_text("d", encoding="utf-8")
    (mem / "config.yaml").write_text("record_mode: hybrid\n", encoding="utf-8")
    (mem / "state").mkdir()
    (mem / "state" / "step-counter-main.txt").write_text("9\n", encoding="utf-8")
    (mem / ".last-flush").write_text("", encoding="utf-8")
    return mem


def test_migrate_moves_markdown_to_shared(tmp_path):
    mem = _flat_repo(tmp_path)
    result = migrate_to_scoped(mem, staff=["dev-engineer", "req-architect"], today="2026-06-10")
    assert result["migrated"] is True
    assert (mem / "shared" / "执行日志.md").is_file()
    assert (mem / "shared" / "当前状态.md").is_file()
    assert (mem / "shared" / "每日汇总" / "2026-06-01.md").is_file()
    assert not (mem / "执行日志.md").exists()
    assert (mem / "staff" / "dev-engineer").is_dir()
    assert (mem / "staff" / "req-architect").is_dir()
    # plumbing 留 root
    assert (mem / "state" / "step-counter-main.txt").is_file()
    assert (mem / "config.yaml").is_file()
    assert (mem / ".last-flush").is_file()
    assert (mem / "MIGRATED-scope-2026-06-10.md").is_file()
    gi = (mem.parent / ".gitignore").read_text(encoding="utf-8")
    assert "state/" in gi


def test_migrate_idempotent(tmp_path):
    mem = _flat_repo(tmp_path)
    migrate_to_scoped(mem, staff=["dev-engineer"], today="2026-06-10")
    result = migrate_to_scoped(mem, staff=["dev-engineer", "test-engineer"], today="2026-06-10")
    assert result["migrated"] is False   # 没再搬 markdown
    assert (mem / "staff" / "test-engineer").is_dir()  # 新员工补建
    assert (mem / "shared" / "执行日志.md").read_text(encoding="utf-8") == "# log"


def test_migrate_creates_shared_marker(tmp_path):
    from scope import is_scoped
    mem = _flat_repo(tmp_path)
    migrate_to_scoped(mem, staff=["dev-engineer"], today="2026-06-10")
    assert is_scoped(mem) is True


def test_migrate_partial_failure_tracked(tmp_path, monkeypatch):
    import shutil as _sh
    mem = _flat_repo(tmp_path)
    real_move = _sh.move
    def fake_move(src, dst, *a, **k):
        if str(src).endswith("踩坑日志.md"):
            raise OSError("simulated")
        return real_move(src, dst, *a, **k)
    monkeypatch.setattr(migrate_scope.shutil, "move", fake_move)
    result = migrate_scope.migrate_to_scoped(mem, staff=["dev-engineer"], today="2026-06-10")
    assert "踩坑日志.md" in result["failed"]
    assert "踩坑日志.md" not in result["moved"]
    # 失败项保持原位
    assert (mem / "踩坑日志.md").is_file()
    # 其它项正常迁入
    assert (mem / "shared" / "执行日志.md").is_file()
    # notice 含失败区
    assert "迁移失败" in (mem / "MIGRATED-scope-2026-06-10.md").read_text(encoding="utf-8")
