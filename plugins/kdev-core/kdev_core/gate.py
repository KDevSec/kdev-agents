"""kdev-core R3 — three-kind gate (GateResult + record_gate).

Builds on R1 (flow_state.history) + R2 (node_machine.advance). A GateResult is the
structured verdict a flow feeds back after running a gate; record_gate appends it to
state["history"], bumps the double counters, and applies the resulting transition via
R2 advance.

Three gate kinds:
  - review / acceptance: verdict PASS|FAIL.
        PASS               -> advance(on_pass), reset that gate's iter
        FAIL, iter < max   -> advance(on_reflow)              [redo]
        FAIL, iter >= max  -> escalate: status="blocked", NO advance, NO force-accept
  - decision: verdict is a branch key -> advance(branches[verdict])

Gate semantics ride in a separate `gate_specs` arg (R2's node_machine is untouched):
  gate_specs = {
    "g-code":  {"kind": "review",     "on_pass": "n-next", "on_reflow": "n-tdd"},
    "g-e2e":   {"kind": "acceptance", "on_pass": "n-ship", "on_reflow": "n-fix"},
    "g-route": {"kind": "decision",   "branches": {"go": "n-go", "rework": "n-plan"}},
  }
All transition targets are still validated by R2 adjacency (advance raises on illegal edges).

[OMC] structured verdict (no regex); escalate never force-accepts. request_id is recorded
for traceability; full open/approval LOCK enforcement is deferred.
"""
from datetime import datetime, timezone

from kdev_core.node_machine import advance

GATE_KINDS = {"review", "decision", "acceptance"}
GATE_VERDICTS = {"PASS", "FAIL"}  # review/acceptance; decision uses branch keys


class GateError(Exception):
    """Malformed GateResult, unknown gate spec, or invalid verdict."""


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_gate_result(gate, kind, *, node, verdict, request_id,
                     by="ai", iter=1, issues=None, revisions=None, ts=None):
    """Build + validate a structured GateResult dict."""
    if not gate:
        raise GateError("GateResult requires a non-empty gate id")
    if kind not in GATE_KINDS:
        raise GateError(f"GateResult kind must be one of {sorted(GATE_KINDS)}, got {kind!r}")
    if not request_id:
        raise GateError("GateResult requires a non-empty request_id")
    if kind in ("review", "acceptance") and verdict not in GATE_VERDICTS:
        raise GateError(f"{kind} verdict must be PASS/FAIL, got {verdict!r}")
    return {
        "gate": gate,
        "kind": kind,
        "node": node,
        "request_id": request_id,
        "iter": iter,
        "verdict": verdict,
        "by": by,
        "issues": list(issues or []),
        "revisions": list(revisions or []),
        "ts": ts or _now_iso(),
    }
