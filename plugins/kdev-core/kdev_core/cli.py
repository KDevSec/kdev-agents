"""kdev-core CLI — drive a flow's R1/R2/R3 engine from the shell.

Thin argparse shell over flow_state (R1) / node_machine (R2) / gate (R3): the
orchestration Agent calls these subcommands at each node. The engine + node-table
stay harness-agnostic; the CLI is just a portable seam. node-table (+ its
`gate_specs` section) is data loaded from a YAML file.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from kdev_core import flow_state, node_machine, gate


def _load_table(path):
    """Load a node-table YAML -> (validated table, gate_specs dict)."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    table = node_machine.load_node_table(data)
    return table, data.get("gate_specs", {})


def _print_state(state):
    """Print enriched state JSON for orchestrator consumption."""
    print(json.dumps({
        "flow": state["flow"],
        "slug": state["slug"],
        "display_name": state.get("display_name"),
        "status": state["status"],
        "active": state["active"],
        "current_node": state["current_node"],
        "config": state.get("config"),
        "gate_calls": state.get("gate_calls", 0),
        "history_len": len(state.get("history", [])),
        "blocked_reason": state.get("blocked_reason"),
        "gate_iters": state.get("gate_iters", {}),
        "phase_history": state.get("phase_history", [])[-5:],
    }, ensure_ascii=False, indent=2))


def cmd_show(args):
    _print_state(flow_state.read_state(args.workspace, args.flow, args.slug))
    return 0


def cmd_init(args):
    flow_state.init_state(args.workspace, args.flow, args.slug,
                          display_name=args.display_name,
                          review_mode=args.review_mode,
                          auto_mode=args.auto_mode,
                          initial_node=args.initial_node)
    _print_state(flow_state.read_state(args.workspace, args.flow, args.slug))
    return 0


def cmd_resume(args):
    _print_state(flow_state.resume_state(args.workspace, args.flow, args.slug))
    return 0


def cmd_advance(args):
    table, _ = _load_table(args.table)
    state = node_machine.advance_persist(
        args.workspace, args.flow, args.slug, args.to_node,
        table=table, reflow=args.reflow, reason=args.reason)
    _print_state(state)
    return 0


def cmd_record_gate(args):
    table, gate_specs = _load_table(args.table)
    gr = gate.make_gate_result(
        args.gate, args.kind, node=args.node, verdict=args.verdict,
        request_id=args.request_id, by=args.by, iter=args.iter,
        issues=args.issues or [])
    state = gate.record_gate_persist(
        args.workspace, args.flow, args.slug, gr,
        table=table, gate_specs=gate_specs)
    _print_state(state)
    return 0


def cmd_complete(args):
    state = flow_state.mark_inactive(args.workspace, args.flow, args.slug,
                                     status=args.status)
    _print_state(state)
    return 0


def cmd_next_step(args):
    table, gate_specs = _load_table(args.table)
    state = flow_state.read_state(args.workspace, args.flow, args.slug)
    result = node_machine.get_next_actions(state, table, gate_specs)
    # Enrich with display-level info
    nodes = table["nodes"]
    current = result.get("current_node")
    node_info = nodes.get(current) if current else None
    result["node_kind"] = node_info["kind"] if node_info else result.get("node_kind")
    result["node_name"] = node_info["name"] if node_info else result.get("node_name")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_gate_lookup(args):
    table, gate_specs = _load_table(args.table)
    state = flow_state.read_state(args.workspace, args.flow, args.slug)
    current = state.get("current_node")
    nodes = table["nodes"]
    node_info = nodes.get(current) if current else None
    if not node_info:
        print(json.dumps({"error": f"unknown node {current!r}"}, indent=2))
        return 1
    gate_id = node_info.get("gate")
    if not gate_id:
        print(json.dumps({"error": f"node {current!r} is not a gate"}, indent=2))
        return 1
    spec = gate_specs.get(gate_id)
    if not spec:
        print(json.dumps({"error": f"gate {gate_id!r} not found in specs"}, indent=2))
        return 1
    result = dict(spec)
    result["gate"] = gate_id
    result["current_iter"] = state.get("gate_iters", {}).get(gate_id, 0)
    result["max_retries"] = table.get("max_retries", node_machine.DEFAULT_MAX_RETRIES)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_unblock(args):
    to_node = getattr(args, "to_node", None)
    state = flow_state.unblock_state(args.workspace, args.flow, args.slug,
                                    to_node=to_node)
    _print_state(state)
    return 0


def cmd_list_flows(args):
    flows = flow_state.list_flows(args.workspace)
    print(json.dumps(flows, ensure_ascii=False, indent=2))
    return 0


def _common(sub, name):
    """A subparser with the shared --workspace + flow/slug positionals."""
    sp = sub.add_parser(name)
    sp.add_argument("flow")
    sp.add_argument("slug")
    sp.add_argument("--workspace", default=".", help="workspace root (default: cwd)")
    return sp


def build_parser():
    p = argparse.ArgumentParser(prog="kdev_core",
                                description="Drive a flow's R1/R2/R3 engine.")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = _common(sub, "show")
    ps.set_defaults(func=cmd_show)

    pi = _common(sub, "init")
    pi.add_argument("--display-name", required=True)
    pi.add_argument("--review-mode", default="ai", choices=["ai", "both", "human"])
    pi.add_argument("--auto-mode", action="store_true")
    pi.add_argument("--initial-node", default=None)
    pi.set_defaults(func=cmd_init)

    pr = _common(sub, "resume")
    pr.set_defaults(func=cmd_resume)

    pa = _common(sub, "advance")
    pa.add_argument("to_node")
    pa.add_argument("--table", required=True)
    pa.add_argument("--reflow", action="store_true")
    pa.add_argument("--reason", default=None)
    pa.set_defaults(func=cmd_advance)

    pg = _common(sub, "record-gate")
    pg.add_argument("--table", required=True)
    pg.add_argument("--gate", required=True)
    pg.add_argument("--kind", required=True,
                    choices=["review", "decision", "acceptance"])
    pg.add_argument("--verdict", required=True)
    pg.add_argument("--node", default=None)
    pg.add_argument("--request-id", required=True)
    pg.add_argument("--by", default="ai")
    pg.add_argument("--iter", type=int, default=1)
    pg.add_argument("--issues", action="append")
    pg.set_defaults(func=cmd_record_gate)

    pc = _common(sub, "complete")
    pc.add_argument("--status", default="completed",
                    choices=["completed", "aborted"])
    pc.set_defaults(func=cmd_complete)

    pn = _common(sub, "next-step")
    pn.add_argument("--table", required=True)
    pn.set_defaults(func=cmd_next_step)

    pg_lk = _common(sub, "gate-lookup")
    pg_lk.add_argument("--table", required=True)
    pg_lk.set_defaults(func=cmd_gate_lookup)

    pu = _common(sub, "unblock")
    pu.add_argument("--to-node", default=None,
                    help="node to move current_node to after unblocking")
    pu.set_defaults(func=cmd_unblock)

    plf = sub.add_parser("list-flows")
    plf.add_argument("--workspace", default=".", help="workspace root (default: cwd)")
    plf.set_defaults(func=cmd_list_flows)

    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (flow_state.FlowStateError, node_machine.NodeMachineError,
            gate.GateError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
