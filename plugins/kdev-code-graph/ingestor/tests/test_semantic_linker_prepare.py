import json
from pathlib import Path

from kdev_ingestor.cli import main


def _write_graph(graph_path: Path, nodes: list[dict]):
    graph_path.write_text(json.dumps({
        "version": "1", "project": {}, "layers": [], "tour": [],
        "nodes": nodes, "edges": [],
    }, ensure_ascii=False), encoding="utf-8")


def _doc_node(rel: str):
    return {
        "id": f"document:{rel}", "type": "document", "name": rel.split("/")[-1],
        "filePath": rel, "summary": "doc", "tags": [], "complexity": "simple",
    }


def _func_node(rel: str, name: str, summary: str = "s"):
    return {
        "id": f"function:{rel}:{name}", "type": "function", "name": name,
        "filePath": rel, "lineRange": [1, 10], "summary": summary,
        "tags": [], "complexity": "simple",
    }


def test_prepare_emits_intents_for_section_doc(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "docs").mkdir()
    (src / "docs" / "spec.md").write_text(
        "# Spec\n\n## 用户登录\n登录功能描述。\n\n## 数据导出\nCSV/JSON 导出。\n",
        encoding="utf-8",
    )
    (src / "app.py").write_text("def login(): pass\n", encoding="utf-8")

    g = tmp_path / "kg.json"
    _write_graph(g, [
        _doc_node("docs/spec.md"),
        _func_node("app.py", "login", "User login handler"),
    ])

    intents_out = tmp_path / "intents.json"
    rc = main(["spec-link-prepare",
               "--graph", str(g),
               "--source-root", str(src),
               "--out", str(intents_out)])
    assert rc == 0
    data = json.loads(intents_out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert data["doc_count"] == 1
    assert data["intent_count"] == 2
    assert {i["intent_id"] for i in data["intents"]} == {
        "docs/spec.md#用户登录", "docs/spec.md#数据导出",
    }
    login_intent = next(i for i in data["intents"] if "登录" in i["intent_id"])
    assert any(c["node_id"] == "function:app.py:login" for c in login_intent["candidates"])


def test_prepare_no_document_nodes_empty_intents(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    g = tmp_path / "kg.json"
    _write_graph(g, [_func_node("app.py", "x", "x")])
    out = tmp_path / "intents.json"
    rc = main(["spec-link-prepare",
               "--graph", str(g),
               "--source-root", str(src),
               "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["doc_count"] == 0
    assert data["intent_count"] == 0
    assert data["intents"] == []


def test_prepare_skips_missing_doc_file(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    g = tmp_path / "kg.json"
    _write_graph(g, [_doc_node("docs/missing.md")])
    out = tmp_path / "intents.json"
    rc = main(["spec-link-prepare",
               "--graph", str(g),
               "--source-root", str(src),
               "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    # doc_count counts the document node; intents=0 because file missing
    assert data["doc_count"] == 1
    assert data["intent_count"] == 0


def test_prepare_default_top_k(tmp_path):
    src = tmp_path / "src"; src.mkdir()
    (src / "docs").mkdir()
    (src / "docs" / "s.md").write_text("## X\nfoo bar\n", encoding="utf-8")
    g = tmp_path / "kg.json"
    nodes = [_doc_node("docs/s.md")] + [
        _func_node("a.py", f"f{i}", "foo bar") for i in range(50)
    ]
    _write_graph(g, nodes)
    out = tmp_path / "intents.json"
    rc = main(["spec-link-prepare",
               "--graph", str(g),
               "--source-root", str(src),
               "--out", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["intent_count"] == 1
    assert len(data["intents"][0]["candidates"]) == 30  # default top_k
