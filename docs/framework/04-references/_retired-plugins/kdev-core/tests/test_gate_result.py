"""Tests for kdev_core.gate.make_gate_result — structured verdict builder + validation."""
import pytest

from kdev_core.gate import make_gate_result, GateError, GATE_KINDS


def test_build_review_result_has_all_fields():
    r = make_gate_result("g-code", "review", node="n-tdd", verdict="PASS", request_id="req-1")
    assert r["gate"] == "g-code"
    assert r["kind"] == "review"
    assert r["node"] == "n-tdd"
    assert r["verdict"] == "PASS"
    assert r["request_id"] == "req-1"
    assert r["by"] == "ai"
    assert r["iter"] == 1
    assert r["issues"] == []
    assert r["revisions"] == []
    assert "ts" in r


def test_build_with_overrides():
    r = make_gate_result("g", "acceptance", node="n", verdict="FAIL", request_id="r2",
                         by="human", iter=3, issues=["x"], revisions=["y"], ts="2026-01-01T00:00:00+00:00")
    assert r["by"] == "human" and r["iter"] == 3
    assert r["issues"] == ["x"] and r["revisions"] == ["y"]
    assert r["ts"] == "2026-01-01T00:00:00+00:00"


def test_decision_verdict_is_freeform_branch_key():
    r = make_gate_result("g-route", "decision", node="n", verdict="rework", request_id="r3")
    assert r["verdict"] == "rework"


def test_invalid_kind_raises():
    with pytest.raises(GateError, match="kind"):
        make_gate_result("g", "weird", node="n", verdict="PASS", request_id="r")


def test_missing_request_id_raises():
    with pytest.raises(GateError, match="request_id"):
        make_gate_result("g", "review", node="n", verdict="PASS", request_id="")


def test_review_verdict_must_be_pass_or_fail():
    with pytest.raises(GateError, match="PASS/FAIL"):
        make_gate_result("g", "review", node="n", verdict="MAYBE", request_id="r")


def test_acceptance_verdict_must_be_pass_or_fail():
    with pytest.raises(GateError, match="PASS/FAIL"):
        make_gate_result("g", "acceptance", node="n", verdict="ok", request_id="r")


def test_gate_kinds_constant():
    assert GATE_KINDS == {"review", "decision", "acceptance"}
