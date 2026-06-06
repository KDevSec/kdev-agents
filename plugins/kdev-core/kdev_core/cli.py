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
