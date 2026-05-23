from pathlib import Path

import pytest

from kdev_ingestor.intents import Intent, extract_intents_from_markdown


@pytest.fixture
def docs_dir() -> Path:
    return Path(__file__).parent / "fixtures" / "sample-docs"


def _read(docs_dir: Path, name: str) -> str:
    return (docs_dir / name).read_text(encoding="utf-8")


def test_simple_three_sections(docs_dir):
    intents = extract_intents_from_markdown(
        _read(docs_dir, "simple.md"), "docs/simple.md"
    )
    assert len(intents) == 3
    assert all(i.intent_kind == "section" for i in intents)
    titles = [i.intent_title for i in intents]
    assert titles == ["概览", "用户管理", "数据导出"]
    assert intents[0].intent_id == "docs/simple.md#概览"
    assert "项目概览" in intents[0].intent_text
    assert all(i.source_doc == "docs/simple.md" for i in intents)


def test_fr_table_splits_rows(docs_dir):
    intents = extract_intents_from_markdown(
        _read(docs_dir, "with-fr-table.md"), "docs/prd.md"
    )
    assert len(intents) == 3
    kinds = [i.intent_kind for i in intents]
    assert kinds == ["fr_row", "fr_row", "section"]
    assert intents[0].intent_id == "docs/prd.md#F1.1"
    assert intents[0].intent_title.startswith("F1.1")
    assert "多语言 AST 解析" in intents[0].intent_title
    assert intents[1].intent_id == "docs/prd.md#F1.2"
    assert intents[2].intent_kind == "section"
    assert intents[2].intent_title == "F2: 普通章节"


def test_no_headings_whole_doc(docs_dir):
    intents = extract_intents_from_markdown(
        _read(docs_dir, "no-headings.md"), "docs/loose.md"
    )
    assert len(intents) == 1
    assert intents[0].intent_kind == "doc"
    assert intents[0].intent_id == "docs/loose.md"
    assert "没有结构" in intents[0].intent_text


def test_section_text_truncated_to_800():
    body = "## Big\n\n" + ("x" * 2000)
    intents = extract_intents_from_markdown(body, "docs/big.md")
    assert len(intents) == 1
    assert len(intents[0].intent_text) <= 800


def test_intent_dataclass_fields():
    i = Intent(intent_id="a", source_doc="b", intent_kind="section",
               intent_title="t", intent_text="x")
    assert i.intent_id == "a"
