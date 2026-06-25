"""test Tier A hook scoped 解析：missing_summaries / archive_hint / promote_scan / milestone。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import missing_summaries  # noqa: E402
import archive_hint  # noqa: E402
import promote_scan  # noqa: E402


def _milestone():
    spec = importlib.util.spec_from_file_location("milestone", LIB_DIR / "milestone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_missing_summaries_scoped(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    (root / "shared" / "每日汇总").mkdir()
    out = missing_summaries.list_missing_past_summaries(str(root), "2026-06-10")
    assert "2020-01-01" in out


def test_archive_hint_scoped(tmp_path):
    """季度切档提醒仍照常解析 shared/ 子目录（回归保护）。"""
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "决策日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    out = archive_hint.collect_archive_hints(str(root))
    assert "决策日志.md" in out


def test_archive_hint_execution_log_monthly_gated_off(tmp_path):
    """JSONL 迁移 Phase C：执行日志.md 按月切档提醒已下线，不应再出现。

    旧条目（2020-01）相对今天必然跨月，gate off 前会触发月度提醒；gate off 后即使
    执行日志.md 里有跨月旧条目也不再提示切档（jsonl 主账无月度 rotation 落点）。
    """
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    out = archive_hint.collect_archive_hints(str(root))
    assert "执行日志.md" not in out


def test_archive_hint_quarterly_still_fires(tmp_path):
    """回归保护：决策/踩坑日志的季度切档提醒仍照常出现。"""
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    # 2020 Q1 相对任何后续季度必然跨季 → 应触发季度切档提醒。
    (root / "shared" / "决策日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    (root / "shared" / "踩坑日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    out = archive_hint.collect_archive_hints(str(root))
    assert "决策日志.md" in out
    assert "踩坑日志.md" in out
    assert "跨季" in out
    # 同时确认执行日志即便存在跨月旧条目也不混进季度提醒里。
    (root / "shared" / "执行日志.md").write_text("日期：2020-01-01\n", encoding="utf-8")
    out2 = archive_hint.collect_archive_hints(str(root))
    assert "执行日志.md" not in out2


def test_promote_scan_scoped(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    imp = root / "shared" / "改进建议.md"
    imp.write_text("\n".join(f"## R-{i} x" for i in range(1, 5)), encoding="utf-8")
    out = promote_scan.scan_promote_candidates(str(root), "2026-06-10")
    assert "改进建议" in out  # 4 条 pending ≥ 3 触发


def test_milestone_matches_shared_rule_file():
    mod = _milestone()
    assert mod.is_milestone_path(".kdev/memory/方法论铁规.md") is True
    assert mod.is_milestone_path(".kdev/memory/shared/方法论铁规.md") is True
