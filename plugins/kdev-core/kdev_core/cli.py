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
    print(json.dumps({
        "flow": state["flow"],
        "slug": state["slug"],
        "status": state["status"],
        "active": state["active"],
        "current_node": state["current_node"],
        "gate_calls": state.get("gate_calls", 0),
        "history_len": len(state.get("history", [])),
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
