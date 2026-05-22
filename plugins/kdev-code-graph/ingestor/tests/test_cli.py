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


def test_link_creates_related_edges(tmp_path, sample_rules_dir):
    import json
    from kdev_ingestor.cli import main

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("def f():\n    flagged_call('x')\n", encoding="utf-8")

    graph_path = tmp_path / "knowledge-graph.json"
    graph_path.write_text(json.dumps({
        "version": "1", "project": {}, "layers": [], "tour": [],
        "nodes": [
            {"id": "file:a.py", "type": "file", "name": "a.py",
             "filePath": "a.py", "summary": "s", "tags": [], "complexity": "simple"},
            {"id": "function:a.py:f", "type": "function", "name": "f",
             "filePath": "a.py", "lineRange": [1, 2], "summary": "s",
             "tags": [], "complexity": "simple"},
        ],
        "edges": [],
    }, ensure_ascii=False), encoding="utf-8")

    assert main(["inject", "--rules-dir", str(sample_rules_dir),
                 "--graph", str(graph_path)]) == 0
    assert main(["link", "--rules-dir", str(sample_rules_dir),
                 "--graph", str(graph_path), "--source-root", str(src)]) == 0

    g = json.loads(graph_path.read_text(encoding="utf-8"))
    related = [e for e in g["edges"] if e["type"] == "related"]
    assert any(e["source"] == "kdev-sec:rule:3.1.1"
               and e["target"] == "function:a.py:f" for e in related)


def test_link_idempotent(tmp_path, sample_rules_dir):
    import json
    from kdev_ingestor.cli import main

    src = tmp_path / "src"; src.mkdir()
    (src / "a.py").write_text("flagged_call('x')\n", encoding="utf-8")
    graph_path = tmp_path / "kg.json"
    graph_path.write_text(json.dumps({
        "version": "1", "project": {}, "layers": [], "tour": [],
        "nodes": [{"id": "file:a.py", "type": "file", "name": "a.py",
                   "filePath": "a.py", "summary": "s", "tags": [],
                   "complexity": "simple"}],
        "edges": [],
    }), encoding="utf-8")
    main(["inject", "--rules-dir", str(sample_rules_dir), "--graph", str(graph_path)])
    main(["link", "--rules-dir", str(sample_rules_dir), "--graph", str(graph_path),
          "--source-root", str(src)])
    n1 = len(json.loads(graph_path.read_text())["edges"])
    main(["link", "--rules-dir", str(sample_rules_dir), "--graph", str(graph_path),
          "--source-root", str(src)])
    n2 = len(json.loads(graph_path.read_text())["edges"])
    assert n1 == n2


def test_link_missing_source_root_errors(tmp_path, sample_rules_dir, capsys):
    import json
    from kdev_ingestor.cli import main
    graph_path = tmp_path / "kg.json"
    graph_path.write_text(json.dumps({
        "version": "1", "project": {}, "layers": [], "tour": [],
        "nodes": [], "edges": [],
    }), encoding="utf-8")
    rc = main(["link", "--rules-dir", str(sample_rules_dir),
               "--graph", str(graph_path), "--source-root", str(tmp_path / "nope")])
    assert rc == 2
