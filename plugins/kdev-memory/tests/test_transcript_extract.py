import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "hooks" / "lib"))
import transcript_extract as tx


def _write_jsonl(p: Path, rows: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _assistant_tool_use(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def _tool_result(is_error=False, text=""):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": is_error,
            "content": [{"type": "text", "text": text}]}]}}


def test_extract_counts_tools(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        _assistant_tool_use("Edit", file_path="/r/a.py"),
        _assistant_tool_use("Edit", file_path="/r/b.py"),
        _assistant_tool_use("Bash", command="git commit -m x"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert facts["tools_invoked"]["Edit"] == 2
    assert facts["tools_invoked"]["Bash"] == 1
    assert facts["tools_invoked_count"] == 3


def test_extract_errors_and_detours(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        _assistant_tool_use("Edit", file_path="/r/a.py"),
        _tool_result(is_error=True, text="<tool_use_error>File has been modified since read</tool_use_error>"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert facts["errors_hit"] == 1
    assert "modified since read" in facts["error_samples"][0]


def test_extract_files_and_shas(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        _assistant_tool_use("Write", file_path="/r/x.md"),
        _tool_result(text="[main 0bd0411] docs: y\n 1 file changed"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert "/r/x.md" in facts["files_touched"]
    assert "0bd0411" in facts["commit_shas"]


def test_extract_skills_and_subagents(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        _assistant_tool_use("Skill", skill="superpowers:brainstorming"),
        _assistant_tool_use("Agent", subagent_type="general-purpose"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert "superpowers:brainstorming" in facts["skills_invoked"]
    assert "general-purpose" in facts["subagents_dispatched"]


def test_offset_slice(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        _assistant_tool_use("Read"),
        _assistant_tool_use("Edit", file_path="/r/a.py"),
        _assistant_tool_use("Bash", command="ls"),
    ])
    facts = tx.extract(str(p), 1, None)  # since_offset=1 → 跳过第1行
    assert facts["tools_invoked"].get("Read", 0) == 0
    assert facts["tools_invoked"]["Edit"] == 1


def test_malformed_lines_skipped(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('not json\n' + json.dumps(_assistant_tool_use("Bash", command="ls")) + "\n", encoding="utf-8")
    facts = tx.extract(str(p), 0, None)
    assert facts["tools_invoked"]["Bash"] == 1


def test_missing_file_returns_empty(tmp_path):
    facts = tx.extract(str(tmp_path / "nope.jsonl"), 0, None)
    assert facts["tools_invoked_count"] == 0
    assert facts["unreadable"] is True


def test_sha_only_from_git_commit_bracket(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        # hex noise that must NOT be captured (css color, sha256 fragment, uuid seg)
        _tool_result(text="color deadbeef; digest 3f786850e387550fdab836ed7e6dc881de23001b; id 550e8400"),
        # real git commit output — must be captured
        _tool_result(text="[main 0bd0411] docs: y\n 1 file changed"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert facts["commit_shas"] == ["0bd0411"]


def test_empty_tool_name_skipped(tmp_path):
    p = tmp_path / "t.jsonl"
    _write_jsonl(p, [
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "", "input": {}}]}},
        _assistant_tool_use("Bash", command="ls"),
    ])
    facts = tx.extract(str(p), 0, None)
    assert "" not in facts["tools_invoked"]
    assert facts["tools_invoked_count"] == 1
