"""test distill scope：collect_entries 收 shared + staff Step；trigger 走 shared。"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

import distill  # noqa: E402

_STEP = "---\n\n## {sid}: {t}\ntriggers: [a,b,c,d,e]\n日期：2026-06-10\nabout: project\n\n### 执行事实\n- 工具调用次数：1\n"


def test_collect_includes_staff_steps(tmp_path):
    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    de = root / "staff" / "dev-engineer"; de.mkdir(parents=True)
    (root / "shared" / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="CEO"), encoding="utf-8")
    (de / "执行日志.md").write_text(_STEP.format(sid="Step dev-engineer-1", t="员工"), encoding="utf-8")
    entries = distill.collect_entries(root)
    ids = {e.entry_id for e in entries}
    assert "Step main-9" in ids
    assert "Step dev-engineer-1" in ids


def test_collect_flat_unchanged(tmp_path):
    root = tmp_path / "memory"; root.mkdir()
    (root / "执行日志.md").write_text(_STEP.format(sid="Step main-9", t="活"), encoding="utf-8")
    ids = {e.entry_id for e in distill.collect_entries(root)}
    assert ids == {"Step main-9"}


def test_distill_trigger_counts_f_from_shared(tmp_path):
    import importlib.util, time
    LIB = Path(__file__).parent.parent / "hooks" / "lib"
    spec = importlib.util.spec_from_file_location("distill_trigger", LIB / "distill_trigger.py")
    dt = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(LIB))
    spec.loader.exec_module(dt)

    root = tmp_path / "memory"
    (root / "shared").mkdir(parents=True)
    (root / "staff" / "dev-engineer").mkdir(parents=True)
    # 旧 .last-distill 标记（root，机器本地）→ last_ts 在过去
    marker = root / ".last-distill"
    marker.write_text("", encoding="utf-8")
    import os
    old = time.time() - 86400
    os.utime(marker, (old, old))
    # shared 下放 3 条 F（在 marker 之后产生）
    (root / "shared" / "skill-feedback.md").write_text(
        "\n".join(f"## F-{i}: x\nsubject: plugin:y\n" for i in range(1, 4)), encoding="utf-8")
    check = dt.check_distill_trigger(root)
    assert check.new_f_count == 3, f"expected 3 F from shared/, got {check.new_f_count}"
