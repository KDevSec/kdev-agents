import json
import shutil
from pathlib import Path

import pytest

from kdev_ingestor.cli import main


def _setup(tmp_path: Path, sample_graph_path: Path, sample_rules_dir: Path):
    graph_dst = tmp_path / "knowledge-graph.json"
    graph_dst.write_text(sample_graph_path.read_text(encoding="utf-8"), encoding="utf-8")
    rules_dst = tmp_path / "rules"
    shutil.copytree(sample_rules_dir, rules_dst)
    return graph_dst, rules_dst


def test_inject_adds_rule_nodes(tmp_path: Path, sample_graph_path, sample_rules_dir):
    graph, rules = _setup(tmp_path, sample_graph_path, sample_rules_dir)
    rc = main(["inject", "--rules-dir", str(rules), "--graph", str(graph)])
    assert rc == 0
    data = json.loads(graph.read_text(encoding="utf-8"))
    rule_nodes = [n for n in data["nodes"] if "kdev:security_rule" in n.get("tags", [])]
    assert len(rule_nodes) == 2
    ids = {n["id"] for n in rule_nodes}
    assert ids == {"kdev-sec:rule:3.1.1", "kdev-sec:rule:3.1.2"}


def test_inject_idempotent(tmp_path: Path, sample_graph_path, sample_rules_dir):
    graph, rules = _setup(tmp_path, sample_graph_path, sample_rules_dir)
    main(["inject", "--rules-dir", str(rules), "--graph", str(graph)])
    main(["inject", "--rules-dir", str(rules), "--graph", str(graph)])
    data = json.loads(graph.read_text(encoding="utf-8"))
    rule_nodes = [n for n in data["nodes"] if "kdev:security_rule" in n.get("tags", [])]
    assert len(rule_nodes) == 2


def test_inject_keeps_existing_nodes(tmp_path: Path, sample_graph_path, sample_rules_dir):
    graph, rules = _setup(tmp_path, sample_graph_path, sample_rules_dir)
    before = json.loads(graph.read_text(encoding="utf-8"))
    main(["inject", "--rules-dir", str(rules), "--graph", str(graph)])
    after = json.loads(graph.read_text(encoding="utf-8"))
    before_ids = {n["id"] for n in before["nodes"]}
    after_ids = {n["id"] for n in after["nodes"]}
    assert before_ids.issubset(after_ids)


def test_inject_missing_graph_returns_error(tmp_path: Path, sample_rules_dir):
    rc = main([
        "inject",
        "--rules-dir", str(sample_rules_dir),
        "--graph", str(tmp_path / "missing.json"),
    ])
    assert rc != 0


def test_list_tags_outputs_kdev_tags(tmp_path: Path, capsys, sample_graph_path, sample_rules_dir):
    graph, rules = _setup(tmp_path, sample_graph_path, sample_rules_dir)
    main(["inject", "--rules-dir", str(rules), "--graph", str(graph)])
    capsys.readouterr()
    rc = main(["list-tags", "--graph", str(graph)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "kdev:security_rule" in out
    assert "kdev:rule_id:3.1.1" in out
    assert "kdev:category:input_validation" in out


def test_main_with_no_command_returns_error():
    with pytest.raises(SystemExit):
        main([])
