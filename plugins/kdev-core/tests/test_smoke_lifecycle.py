"""Integration smoke — full flow lifecycle + resume-after-interrupt.

Mirrors the X3 spike smoke pattern (full lifecycle + resume after a simulated
interrupt). Validates roadmap §4.3 #1: R1 truly drives state and resume picks
up at the last node, not from scratch.
"""
from kdev_core.flow_state import (
    init_state, read_state, write_state, mark_inactive, resume_state,
)

FLOW = "coding-flow"


def test_full_lifecycle(tmp_workspace):
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n0-env")
    for node in ["n1-plan", "n2-tdd", "n3-e2e"]:
        st = read_state(tmp_workspace, FLOW, "auth")
        st["current_node"] = node
        write_state(tmp_workspace, FLOW, "auth", st)
    assert read_state(tmp_workspace, FLOW, "auth")["current_node"] == "n3-e2e"

    done = mark_inactive(tmp_workspace, FLOW, "auth", status="completed")
    # Terminal: active run folds into runs[]; disposition lives at feature level,
    # last node is preserved on the folded run summary.
    assert done["_has_active"] is False
    assert done["feature_status"] == "completed"
    assert done["runs"][-1]["status"] == "completed"
    assert done["runs"][-1]["final_node"] == "n3-e2e"


def test_resume_after_interrupt(tmp_workspace):
    # A run advances to n2 then the process dies (no mark_inactive called).
    init_state(tmp_workspace, FLOW, "auth", display_name="Auth", initial_node="n0-env")
    st = read_state(tmp_workspace, FLOW, "auth")
    st["current_node"] = "n2-tdd"
    write_state(tmp_workspace, FLOW, "auth", st)

    # A "new session" resumes: still in_progress + active run present -> resumable at n2.
    resumed = resume_state(tmp_workspace, FLOW, "auth")
    assert resumed["status"] == "in_progress"
    assert resumed["_has_active"] is True
    assert resumed["current_node"] == "n2-tdd"  # NOT reset to n0
