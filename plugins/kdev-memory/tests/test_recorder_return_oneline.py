from pathlib import Path

RECORDER = (Path(__file__).resolve().parents[1]
            / "agents/kdev-step-recorder.md")


def _success_block():
    t = RECORDER.read_text(encoding="utf-8")
    start = t.index("## Return format")
    section = t[start:]
    # 成功分支 = "On reject" 之前那段
    return section.split("On reject")[0]


def test_success_return_drops_machine_block():
    """MQ-1：成功不再回 STATUS/MINTED_ID/COUNTER 机器块。"""
    s = _success_block()
    assert "MINTED_ID:" not in s
    assert "COUNTER:" not in s


def test_success_return_is_one_line_human():
    """成功返回一句人话确认（含'执行日志'落点）。"""
    s = _success_block()
    assert "执行日志" in s


def test_reject_branch_still_structured():
    """拒绝分支保留结构化（主会话需照此修正重派）。"""
    t = RECORDER.read_text(encoding="utf-8")
    assert "STATUS: NEEDS_CONTEXT" in t
    assert "RULE_VIOLATED" in t
