"""CLI for kdev-ingestor.

Usage:
    kdev-ingest inject --rules-dir <dir> --graph <path>
    kdev-ingest list-tags --graph <path>
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

from kdev_ingestor.graph_io import (
    GraphIOError,
    load_graph,
    save_graph,
    upsert_node,
)
from kdev_ingestor.security_rules import (
    RuleParseError,
    parse_rules_dir,
    rule_to_node,
)


def _cmd_inject(args: argparse.Namespace) -> int:
    graph_path = Path(args.graph)
    rules_dir = Path(args.rules_dir)
    try:
        graph = load_graph(graph_path)
        rules = parse_rules_dir(rules_dir)
    except (GraphIOError, RuleParseError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    inserted = 0
    for rule in rules:
        node = rule_to_node(rule)
        upsert_node(graph, node)
        inserted += 1

    try:
        save_graph(graph, graph_path)
    except GraphIOError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"injected {inserted} rule node(s) into {graph_path}")
    return 0


def _cmd_list_tags(args: argparse.Namespace) -> int:
    try:
        graph = load_graph(Path(args.graph))
    except GraphIOError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    counter: Counter[str] = Counter()
    for node in graph.nodes:
        for tag in node.get("tags", []):
            if isinstance(tag, str) and tag.startswith("kdev:"):
                counter[tag] += 1

    for tag, count in sorted(counter.items()):
        print(f"{count:5d}  {tag}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kdev-ingest")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inject = sub.add_parser("inject", help="inject security rules into a UA graph")
    p_inject.add_argument("--rules-dir", required=True)
    p_inject.add_argument("--graph", required=True)
    p_inject.set_defaults(func=_cmd_inject)

    p_list = sub.add_parser("list-tags", help="list kdev:* tags in a UA graph")
    p_list.add_argument("--graph", required=True)
    p_list.set_defaults(func=_cmd_list_tags)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
