from pathlib import Path

SKILL = (Path(__file__).resolve().parents[1]
         / "skills/kdev-flow-driver/SKILL.md")


def _skill_text():
    return SKILL.read_text(encoding="utf-8")


def test_dispatch_uses_run_in_background():
    """§2.4 业务派单已改 run_in_background（B 轨核心）。"""
    assert "run_in_background" in _skill_text()


def test_dispatch_wires_handoff_protocol():
    """SKILL 接入文件交接：写/读 CLI + .handoff.json 命名。"""
    t = _skill_text()
    assert "handoff-write" in t
    assert "handoff-read" in t
    assert ".handoff.json" in t


def test_main_loop_reads_handoff_not_inline_return():
    """主循环靠完成通知 + 读交接文件，而非读 subagent 内联返回。"""
    t = _skill_text()
    assert "完成通知" in t or "completion" in t


def test_gate_section_not_backgrounded():
    """gate 判断仍在主循环——§2.5 gate 段绝不出现 run_in_background。"""
    t = _skill_text()
    start = t.index("### 2.5")
    end = t.index("### 2.6")
    assert "run_in_background" not in t[start:end]
