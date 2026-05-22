"""Linker family: connect kdev rule nodes to code nodes in a UA graph.

Member 1 is PatternLinker (deterministic, pattern-based). Member 2 (a future
LLM-based SemanticLinker) shares the `Linker` protocol below.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from kdev_ingestor.graph_io import KnowledgeGraph
from kdev_ingestor.security_rules import SecurityRule

SECURITY_EDGE_TYPE = "related"
SECURITY_EDGE_WEIGHT = 0.6


class Linker(Protocol):
    def link(
        self,
        rules: list[SecurityRule],
        graph: KnowledgeGraph,
        source_root: Path,
    ) -> list[dict]:
        """Return edge dicts (rule node -> code node). Pure; does not persist."""
        ...


def build_path_index(graph: KnowledgeGraph) -> dict[str, dict]:
    """Index graph nodes by filePath for O(1)-ish hit resolution.

    Returns {filePath: {"file": <file_node_id|None>,
                         "funcs": [(start, end, func_node_id), ...]}}
    """
    idx: dict[str, dict] = {}
    for n in graph.nodes:
        fp = n.get("filePath")
        if not fp:
            continue
        entry = idx.setdefault(fp, {"file": None, "funcs": []})
        if n.get("type") == "file":
            entry["file"] = n["id"]
        elif n.get("type") == "function":
            lr = n.get("lineRange")
            if isinstance(lr, (list, tuple)) and len(lr) == 2:
                entry["funcs"].append((lr[0], lr[1], n["id"]))
    return idx


def resolve_node_id(
    path_index: dict[str, dict], rel_path: str, line_no: int
) -> str | None:
    """Map a (file, line) hit to the enclosing function node, else the file node."""
    entry = path_index.get(rel_path)
    if entry is None:
        return None
    for start, end, node_id in entry["funcs"]:
        if start <= line_no <= end:
            return node_id
    return entry["file"]


def make_security_edge(rule_node_id: str, code_node_id: str) -> dict:
    return {
        "source": rule_node_id,
        "target": code_node_id,
        "type": SECURITY_EDGE_TYPE,
        "direction": "forward",
        "weight": SECURITY_EDGE_WEIGHT,
    }
