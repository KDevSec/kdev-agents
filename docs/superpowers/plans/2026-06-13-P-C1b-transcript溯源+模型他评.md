# P-C1b：Step 落盘 transcript 溯源 + 模型他评 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 kdev-memory 的 Step 落盘从"主会话手写 ~30 行 YAML + 模型自评"改成"后台 recorder 读真 transcript 客观抽事实（含 skill/subject）+ 出模型他评"，主控付出降到近零、MQ-2 在记录层修掉。

**Architecture:** commit-tracker（PostToolUse on Bash）在每次 commit 把 `transcript_path` + 当前行 offset stash 进 `pending-commits.json`；step-recorder 从 state 取范围，用 **Bash `sed`+`jq`** 切 transcript 段、调一个**确定性 Python 抽取 helper**（`transcript_extract.py`）得结构化事实（工具/报错/文件/SHA/skills/subject），再据真事实写 Step + `### 模型他评`（替换 `### 模型自评`）。

**Tech Stack:** Python 3.12（stdlib only：json/re/subprocess/pathlib）；pytest；Claude Code plugin hooks（snake_case stdin 契约）；markdown agent prompt（kdev-step-recorder.md）。

**前置已完成（spike，2026-06-13）：** §5.6 spike PASS（[spec v0.5](../specs/2026-06-09-kdev-memory会话污染治理+评分可配-design.md) §5.6）。3 修正已并入设计：① recorder 用 Bash sed/jq 不用 Read 工具（Read 有 25k 整文件闸）② commit-tracker `toolInput`→`tool_input`（[G-010](../../../.kdev/memory/踩坑日志.md)，load-bearing + 复活死掉的 nudge）③ 加 `skills_invoked`+`subject` 提取。

**红线：** 只动 `plugins/kdev-memory/`；不碰 live cache hook（改 repo 源，Task 8 bump version 后用户刷 marketplace 生效，G-004）。AI commit 身份 `git -c user.name=ly-AI -c user.email=ly1989abc@126.com`（不加引号），不 push。**TDD 用 opus；单独 worktree。**

---

## File Structure

| 文件 | 责任 | 动作 |
|---|---|---|
| `plugins/kdev-memory/hooks/commit-tracker.py` | PostToolUse on Bash：识别 commit + stash | 改：`toolInput`→`tool_input`；新增 stash `transcript_path`+offset |
| `plugins/kdev-memory/hooks/lib/pending_commits.py` | pending-commits.json CRUD | 改：state 加 `transcript_path`/`since_offset`；`append` 收 transcript_path；`clear` 收 since_offset；新增 `get_transcript_marker` |
| `plugins/kdev-memory/hooks/lib/transcript_extract.py` | **新**：JSONL 切片 → 结构化事实（确定性） | 创建 |
| `plugins/kdev-memory/hooks/lib/step_completeness.py` | 半残扫描 | 改：识别 `### 模型他评`（同 `### 模型自评` 的扣分项硬门） |
| `plugins/kdev-memory/agents/kdev-step-recorder.md` | recorder agent prompt | 改：Bash 切 transcript + 调 helper + 出他评 + skill/subject |
| `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md` | Step schema 文档 | 改：`### 模型自评`→`### 模型他评` + key_facts 加 skills_invoked/subject |
| `plugins/kdev-memory/tests/test_commit_tracker.py` | commit-tracker 测试 | 改：fixture 用真实 `tool_input` 契约 + 加 transcript stash 断言 |
| `plugins/kdev-memory/tests/test_pending_commits.py` | pending lib 测试 | 改：加 transcript_path/since_offset 断言 |
| `plugins/kdev-memory/tests/test_transcript_extract.py` | **新**：抽取 helper 测试 | 创建 |
| `plugins/kdev-memory/tests/test_step_completeness.py` | 半残测试 | 改：加 `### 模型他评` 扣分项 case |
| `plugins/kdev-memory/.claude-plugin/plugin.json` + `CHANGELOG.md` | 版本 | 改：bump minor + changelog |

---

## Task 1：修 commit-tracker `toolInput`→`tool_input`（load-bearing + 复活 nudge）

**Files:**
- Modify: `plugins/kdev-memory/hooks/commit-tracker.py:77`
- Test: `plugins/kdev-memory/tests/test_commit_tracker.py:28`

- [ ] **Step 1：先把测试 fixture 改成真实 CC 契约（红）**

`test_commit_tracker.py` 的 `_run_hook`（L27-34）现在喂 `toolInput`（驼峰）——与被测代码的 bug 自洽（测试绿但功能死，[G-010](../../../.kdev/memory/踩坑日志.md)）。改成官方 snake_case 契约：

```python
def _run_hook(repo: Path, command: str) -> dict:
    # 真实 Claude Code PostToolUse stdin 契约：snake_case（hooks.md Common input fields）
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "transcript_path": str(repo / "fake-transcript.jsonl"),
        "session_id": "test-session",
    })
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=str(repo), input=payload, capture_output=True, text=True,
    )
    out = r.stdout.strip()
    return json.loads(out) if out else {}
```

- [ ] **Step 2：跑测试看它失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_commit_tracker.py -q`
Expected: FAIL —— `test_git_commit_appends_to_pending` 等断言 `len(commits)==1` 失败（代码读 `toolInput` 拿到 `{}`，cmd="" → 不识别 commit）。这就是 G-010 的红色复现。

- [ ] **Step 3：修代码（绿）**

`commit-tracker.py:77`：

```python
    cmd = (data.get("tool_input") or {}).get("command", "")
```

- [ ] **Step 4：跑测试看它通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_commit_tracker.py -q`
Expected: PASS（全部）。commit 现在被正确识别 → pending 累积 → nudge 复活。

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/commit-tracker.py plugins/kdev-memory/tests/test_commit_tracker.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "fix(kdev-memory): commit-tracker 读 tool_input 而非 toolInput（G-010，复活 pending nudge）(P-C1b task 1/8)"
```

---

## Task 2：pending_commits state 加 `transcript_path` + `since_offset`

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/pending_commits.py`
- Test: `plugins/kdev-memory/tests/test_pending_commits.py`

- [ ] **Step 1：写失败测试（红）**

加到 `test_pending_commits.py`：

```python
def test_append_stashes_transcript_path(tmp_path):
    sd = tmp_path / "state"
    pending_commits.append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    data = pending_commits.read(sd)
    assert data["transcript_path"] == "/t/sess.jsonl"

def test_clear_sets_since_offset(tmp_path):
    sd = tmp_path / "state"
    pending_commits.append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    pending_commits.clear(sd, "main-9", 200, new_since_offset=640)
    data = pending_commits.read(sd)
    assert data["since_offset"] == 640
    assert data["commits"] == []

def test_get_transcript_marker(tmp_path):
    sd = tmp_path / "state"
    pending_commits.clear(sd, "main-9", 200, new_since_offset=640)
    pending_commits.append(sd, "abc1234", "fix: x", 100, transcript_path="/t/sess.jsonl")
    m = pending_commits.get_transcript_marker(sd)
    assert m == {"transcript_path": "/t/sess.jsonl", "since_offset": 640}

def test_empty_state_has_new_fields(tmp_path):
    sd = tmp_path / "state"
    data = pending_commits.read(sd)
    assert data["transcript_path"] == ""
    assert data["since_offset"] == 0
```

确保文件顶部已 `from lib import pending_commits` 或同现有 import 风格（照本文件既有 import）。

- [ ] **Step 2：跑测试看失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_pending_commits.py -q -k "transcript or since_offset or marker or new_fields"`
Expected: FAIL —— `append() got unexpected keyword 'transcript_path'` / `clear() got unexpected keyword 'new_since_offset'` / KeyError。

- [ ] **Step 3：改 lib（绿）**

`pending_commits.py`：

```python
def _empty_state() -> dict:
    return {"since_step_id": "", "since_ts": 0, "since_offset": 0, "transcript_path": "", "commits": []}
```

`read()` 末尾改成"补默认键再返回"（兼容旧文件缺新键）：

```python
def read(state_dir: Path) -> dict:
    p = _path(state_dir)
    if not p.is_file():
        return _empty_state()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "commits" not in data:
            return _empty_state()
    except (OSError, ValueError):
        return _empty_state()
    # 补新字段默认值（向后兼容旧 state 文件）
    data.setdefault("since_offset", 0)
    data.setdefault("transcript_path", "")
    return data
```

`append()` 加可选 transcript_path：

```python
def append(state_dir: Path, sha: str, subject: str, ts: int, transcript_path: str | None = None) -> None:
    data = read(state_dir)
    if not data["commits"]:
        data["since_ts"] = ts
    data["commits"].append({"sha": sha, "subject": subject, "ts": ts})
    if transcript_path:
        data["transcript_path"] = transcript_path
    _write(state_dir, data)
```

`clear()` 加 since_offset，并保留 transcript_path（不清）：

```python
def clear(state_dir: Path, new_since_step_id: str, new_since_ts: int, new_since_offset: int = 0) -> None:
    prev = read(state_dir)
    _write(state_dir, {
        "since_step_id": new_since_step_id,
        "since_ts": new_since_ts,
        "since_offset": new_since_offset,
        "transcript_path": prev.get("transcript_path", ""),
        "commits": [],
    })
```

新增 helper：

```python
def get_transcript_marker(state_dir: Path) -> dict:
    """recorder 读取：{transcript_path, since_offset}（读 transcript[since_offset:EOF] 的范围素材）。"""
    data = read(state_dir)
    return {"transcript_path": data.get("transcript_path", ""), "since_offset": data.get("since_offset", 0)}
```

- [ ] **Step 4：跑测试看通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_pending_commits.py -q`
Expected: PASS（新+旧全绿；旧 `append`/`clear` 调用因新参数有默认值不破）。

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/pending_commits.py plugins/kdev-memory/tests/test_pending_commits.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): pending_commits state 加 transcript_path/since_offset + get_transcript_marker (P-C1b task 2/8)"
```

---

## Task 3：commit-tracker 在 commit 时 stash transcript_path + offset

**Files:**
- Modify: `plugins/kdev-memory/hooks/commit-tracker.py`
- Test: `plugins/kdev-memory/tests/test_commit_tracker.py`

- [ ] **Step 1：写失败测试（红）**

`_run_hook` 已在 Task 1 带 `transcript_path`。新增断言：commit 后 pending 记下 transcript_path。在 `test_commit_tracker.py` 加：

```python
def test_commit_stashes_transcript_path(tmp_path):
    repo = _make_repo_with_commit(tmp_path, "stash transcript test")
    # 造一个真实存在的 transcript 文件（commit-tracker 要 wc -l 它）
    tp = repo / "sess.jsonl"
    tp.write_text("{}\n{}\n{}\n", encoding="utf-8")  # 3 行
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m stash"},
        "transcript_path": str(tp),
        "session_id": "s1",
    })
    subprocess.run([sys.executable, str(HOOK)], cwd=str(repo), input=payload,
                   capture_output=True, text=True)
    pending = _read_pending(repo)
    assert pending["transcript_path"] == str(tp)
```

- [ ] **Step 2：跑测试看失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_commit_tracker.py::test_commit_stashes_transcript_path -q`
Expected: FAIL —— `KeyError: 'transcript_path'`（hook 还没 stash）。

- [ ] **Step 3：改 commit-tracker（绿）**

`commit-tracker.py` 的 `main()`：读 transcript_path，传给 `append`。在 `cmd = ...` 后取 transcript_path，并把 append 调用改成带 transcript_path：

```python
    cmd = (data.get("tool_input") or {}).get("command", "")
    transcript_path = data.get("transcript_path", "")
    if not _is_git_commit(cmd):
        print(SUPPRESS)
        return 0
    # ... sha/subject 不变 ...
    state_dir = repo / ".kdev" / "memory" / "state"
    try:
        append(state_dir, sha, subject, int(time.time()), transcript_path=transcript_path or None)
    except Exception:
        pass
```

> 说明：offset（行号）由 recorder 自取（运行时 `wc -l transcript_path`，读 `[since_offset:EOF]`），commit-tracker 只 stash 路径即可——避免 hook 5s timeout 内做 wc 的脆弱性，且 recorder 读到 EOF 比 stash 时刻的 offset 更完整。`since_offset` 由 recorder 在 clear 时写（见 Task 5）。

- [ ] **Step 4：跑测试看通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_commit_tracker.py -q`
Expected: PASS（全部）。

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/commit-tracker.py plugins/kdev-memory/tests/test_commit_tracker.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): commit-tracker stash transcript_path 进 pending state (P-C1b task 3/8)"
```

---

## Task 4：新建 `transcript_extract.py`——确定性抽取结构化事实（recorder 的可测内核）

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/transcript_extract.py`
- Test: `plugins/kdev-memory/tests/test_transcript_extract.py`

把"读 transcript 段 → 算事实"做成**确定性 Python**（而非让 LLM 解析 raw JSONL）：可测、可靠、省 recorder 上下文。recorder 只对**结构化事实 + 真 transcript 文字**做"他评"判断。

- [ ] **Step 1：写失败测试（红）**

`test_transcript_extract.py`：

```python
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
        _assistant_tool_use("Read"),                       # line 1
        _assistant_tool_use("Edit", file_path="/r/a.py"),  # line 2
        _assistant_tool_use("Bash", command="ls"),         # line 3
    ])
    facts = tx.extract(str(p), 1, None)  # since_offset=1 → 跳过第1行
    assert facts["tools_invoked"].get("Read", 0) == 0
    assert facts["tools_invoked"]["Edit"] == 1


def test_malformed_lines_skipped(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('not json\n' + json.dumps(_assistant_tool_use("Bash", command="ls")) + "\n", encoding="utf-8")
    facts = tx.extract(str(p), 0, None)  # 不崩
    assert facts["tools_invoked"]["Bash"] == 1


def test_missing_file_returns_empty(tmp_path):
    facts = tx.extract(str(tmp_path / "nope.jsonl"), 0, None)
    assert facts["tools_invoked_count"] == 0
    assert facts["unreadable"] is True
```

- [ ] **Step 2：跑测试看失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_transcript_extract.py -q`
Expected: FAIL —— `ModuleNotFoundError: transcript_extract`。

- [ ] **Step 3：写 helper（绿）**

`hooks/lib/transcript_extract.py`：

```python
"""确定性从 transcript JSONL 切片抽结构化事实（P-C1b）。

recorder 经 Bash 调：`python -m transcript_extract <path> <since_offset>` → stdout JSON。
不读整文件进内存：逐行流式，按 since_offset 跳过已记录段。
"""
from __future__ import annotations
import json
import re
import sys
from collections import Counter
from pathlib import Path

_SHA_RE = re.compile(r"\b([0-9a-f]{7,40})\b")


def _iter_blocks(obj: dict):
    msg = obj.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        yield from (b for b in content if isinstance(b, dict))


def _result_text(block: dict) -> str:
    c = block.get("content")
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict))
    return c if isinstance(c, str) else ""


def extract(path: str, since_offset: int = 0, end_offset: int | None = None) -> dict:
    tools: Counter = Counter()
    skills, subagents, files, shas, errors = set(), set(), set(), set(), []
    p = Path(path)
    if not p.is_file():
        return _result(tools, skills, subagents, files, shas, errors, unreadable=True)
    try:
        with open(p, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < since_offset:
                    continue
                if end_offset is not None and i >= end_offset:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                for b in _iter_blocks(obj):
                    t = b.get("type")
                    if t == "tool_use":
                        name = b.get("name", "")
                        tools[name] += 1
                        inp = b.get("input") or {}
                        if name == "Skill" and inp.get("skill"):
                            skills.add(inp["skill"])
                        elif name == "Agent" and inp.get("subagent_type"):
                            subagents.add(inp["subagent_type"])
                        elif name in ("Edit", "Write", "NotebookEdit") and inp.get("file_path"):
                            files.add(inp["file_path"])
                    elif t == "tool_result":
                        txt = _result_text(b)
                        if b.get("is_error"):
                            errors.append(txt[:120])
                        for m in _SHA_RE.findall(txt):
                            if not m.isdigit():  # 滤纯数字
                                shas.add(m)
    except OSError:
        return _result(tools, skills, subagents, files, shas, errors, unreadable=True)
    return _result(tools, skills, subagents, files, shas, errors, unreadable=False)


def _result(tools, skills, subagents, files, shas, errors, unreadable):
    return {
        "tools_invoked": dict(tools),
        "tools_invoked_count": sum(tools.values()),
        "skills_invoked": sorted(skills),
        "subagents_dispatched": sorted(subagents),
        "files_touched": sorted(files),
        "commit_shas": sorted(shas),
        "errors_hit": len(errors),
        "error_samples": errors[:5],
        "unreadable": unreadable,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"unreadable": True, "error": "usage: transcript_extract <path> [since_offset]"}))
        return 2
    path = sys.argv[1]
    since = int(sys.argv[2]) if len(sys.argv) >= 3 else 0
    print(json.dumps(extract(path, since), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4：跑测试看通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_transcript_extract.py -q`
Expected: PASS（全部 7 个）。

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/transcript_extract.py plugins/kdev-memory/tests/test_transcript_extract.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): transcript_extract 确定性抽结构化事实（含 skills/subagents/subject 素材）(P-C1b task 4/8)"
```

---

## Task 5：改 kdev-step-recorder.md——读 transcript 段 + 调 helper + 出他评（prompt，手验）

**Files:**
- Modify: `plugins/kdev-memory/agents/kdev-step-recorder.md`

这是 agent prompt 改造（非单测；用 Step 6 的 step_completeness 测兜底他评 schema，末尾手验一次真 dispatch）。先读现有文件全文，按下述**精确改动点**改，保留其余 8 hard-gate / action sequence 结构。

- [ ] **Step 1：读现状**

Run: `sed -n '1,400p' plugins/kdev-memory/agents/kdev-step-recorder.md | grep -nE "模型自评|self_eval|执行事实|action sequence|工具|pending|clear|offset|transcript"` —— 定位"执行事实抽取段"、"模型自评写入段"、"clear pending 段"。

- [ ] **Step 2：加"读 transcript 抽事实"段**

在 recorder 的 action sequence 里、写 Step 之前，插入（**强调用 Bash 不用 Read 工具**）：

````markdown
### 读真 transcript 抽客观事实（P-C1b 溯源）

主会话 dispatch 时**不再喂 30 行事实 YAML**，你自己从真 transcript 抽：

1. 取范围：`python3 -c "import sys; sys.path.insert(0,'plugins/kdev-memory/hooks/lib'); import pending_commits as pc; import json; print(json.dumps(pc.get_transcript_marker(__import__('pathlib').Path('.kdev/memory/state'))))"` → 得 `{transcript_path, since_offset}`。
2. **用 Bash 调确定性抽取 helper**（⚠️ 不要用 Read 工具读 transcript——它有 25k 整文件 token 闸，offset/limit 也救不了大文件，直接拒）：
   `python3 plugins/kdev-memory/hooks/lib/transcript_extract.py "<transcript_path>" <since_offset>` → stdout JSON（tools_invoked / errors_hit / error_samples / files_touched / commit_shas / **skills_invoked** / **subagents_dispatched**）。
3. 如需读他评所需的"绕路/返工原文"，再 `sed -n 'A,Bp' "<transcript_path>" | jq -r '...'` 取具体几条（同样别用 Read 工具）。
4. `subject`：Step 主题默认 `project`；若该段含用户对某 skill/plugin 的反馈，按蒸馏决策1 三级推断（L1 显式名 / L2 取 skills_invoked 最近项 / L3 候选询问），裂解出 F-NNN（subject:plugin:X, verbatim 原话）——这条不变（沿用现有 F-NNN 流程）。
````

- [ ] **Step 3：把"模型自评"改"模型他评"**

recorder 写 Step 的评估段，从 `### 模型自评` 改 `### 模型他评`，并改判据为**读真 transcript 出执行质量 + 必引证据**：

````markdown
### 写 `### 模型他评`（替换自评，P-C1b）

你是**独立于主会话的 recorder**，据上一步抽到的**真事实**写他评（不是主会话自夸，也不据 summary 反推）：

```markdown
### 模型他评
- 执行质量：N/5（客观：目标达成度 / 绕路返工 / 报错恢复 / 是否一遍过）
- 扣分项：<必填，且须引 transcript 证据，如"第 X 段 Edit 报错 'modified since read' 后重读才过（error_samples[0]）"。无证据的扣分项不写——宁可写"未见明显问题"也不要据 summary 编造（防 MQ-2 confabulate）>
- skills_invoked：<helper 抽到的 skill 清单>
- subagents：<helper 抽到的 subagent 清单>
```
````

key_facts 段写入 helper 抽到的 `tools_invoked_count / errors_hit / files_touched / commit_shas / skills_invoked / subagents_dispatched`（不再由主会话 YAML 喂）。

- [ ] **Step 4：clear 时写 since_offset**

recorder 落完 Step 调 `pending_commits.clear` 时，先 `wc -l "<transcript_path>"` 得当前 EOF 行数，作为 `new_since_offset`：

````markdown
落盘收尾：`EOF=$(wc -l < "<transcript_path>")`，调 `pending_commits.clear(state_dir, "<minted_step_id>", <ts>, new_since_offset=$EOF)` —— 下一个 Step 从这里续读。⚠️ 若 transcript_path 为空 / 文件不在（跨会话或未 stash）→ since_offset=0，recorder 退回"据 dispatch summary + commit log 写"（降级，不硬卡）。
````

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/agents/kdev-step-recorder.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): step-recorder 改读真 transcript 抽事实+出模型他评（Bash 切片，非 Read）(P-C1b task 5/8)"
```

---

## Task 6：schema 迁移 `### 模型自评`→`### 模型他评`（step_completeness TDD + 文档）

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/step_completeness.py`
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`
- Test: `plugins/kdev-memory/tests/test_step_completeness.py`

- [ ] **Step 1：写失败测试（红）**

`### 模型他评` 段的扣分项必填硬门要照 `### 模型自评` 一样生效。加到 `test_step_completeness.py`：

```python
def test_model_peer_review_empty_deduction_is_half(tmp_path):
    log = tmp_path / "执行日志.md"
    log.write_text(
        "## Step main-90: x\n日期：2026-06-13\nstatus: scored\n\n"
        "### 模型他评\n- 执行质量：4/5\n- 扣分项：\n",
        encoding="utf-8",
    )
    from lib import step_completeness as sc  # 照本测试文件既有 import 风格
    res = sc.run_check(log, "2026-06-13", rating_mode="model-only")
    assert res["status"] == "has_half_complete"
    assert any("扣分项" in i for s in res["half_complete_steps"] for i in s["issues"])


def test_model_peer_review_with_deduction_is_ok(tmp_path):
    log = tmp_path / "执行日志.md"
    log.write_text(
        "## Step main-91: y\n日期：2026-06-13\nstatus: scored\n\n"
        "### 模型他评\n- 执行质量：4/5\n- 扣分项：第3段 Edit 报错后重读才过\n",
        encoding="utf-8",
    )
    from lib import step_completeness as sc
    res = sc.run_check(log, "2026-06-13", rating_mode="model-only")
    assert res["status"] == "ok"
```

（import 路径照 `test_step_completeness.py` 现有写法；若用 `sys.path.insert`+`import step_completeness` 则统一。）

- [ ] **Step 2：跑测试看失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_completeness.py -q -k "peer_review"`
Expected: FAIL —— `check_step` 只认 `### 模型自评`，不扫 `### 模型他评` → 空扣分项漏检 → status=ok（应 has_half_complete）。

- [ ] **Step 3：改 step_completeness（绿）**

`check_step()` 第 2 块（L174）改成两段名都认：

```python
    # 2. 模型自评 / 模型他评段的扣分项（P-C1b：他评替换自评，两名都查）
    self_section = (
        _extract_section(body, "### 模型他评") or _extract_section(body, "## 模型他评")
        or _extract_section(body, "### 模型自评") or _extract_section(body, "## 模型自评")
    )
```

`_has_model_self_review()`（L242）同步加他评名：

```python
def _has_model_self_review(body: str) -> bool:
    return any(h in body for h in ("### 模型他评", "## 模型他评", "### 模型自评", "## 模型自评"))
```

模块 docstring L16 的"模型自评段"补一句"（P-C1b 后为模型他评段，同检扣分项）"。

- [ ] **Step 4：跑测试看通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_step_completeness.py -q`
Expected: PASS（新 peer_review case + 旧 模型自评 case 都绿——向后兼容历史条目）。

- [ ] **Step 5：改 schema 文档**

`references/六类记录-schema.md`：把 Step 的 `### 模型自评` 段定义改 `### 模型他评`（recorder 独立读 transcript 出执行质量 + 必引证据扣分项），保留"历史条目仍可为 `### 模型自评`，两者都被半残检测认"的兼容说明；key_facts 加 `skills_invoked` / `subagents_dispatched` / `subject` 字段说明（先 `grep -n "模型自评\|key_facts\|执行事实" references/六类记录-schema.md` 定位再改）。

- [ ] **Step 6：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/step_completeness.py plugins/kdev-memory/tests/test_step_completeness.py plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): schema 迁移 模型自评→模型他评（半残检测+schema 文档兼容两名）(P-C1b task 6/8)"
```

---

## Task 7：nudge 阈值改 age 为主（避免 TDD 爆量刷屏）

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/pending_commits.py:88-110`（`format_brief_hint`）
- Test: `plugins/kdev-memory/tests/test_pending_commits.py`

- [ ] **Step 1：写失败测试（红）**

目标：count 高但都很新（age 小）→ 不 nudge（避免一个工作单元内反复 nudge）；age 过阈值 → nudge（即便 count 少）。加：

```python
def test_nudge_age_primary_suppresses_fresh_burst(tmp_path):
    sd = tmp_path / "state"
    now = 1000
    for i in range(8):  # TDD 爆 8 个 commit，但都在 now 前 60s 内
        pending_commits.append(sd, f"sha{i}", f"t {i}", now - 60)
    # age=60s 远小于 age 阈值 → 不 nudge（age 为主，count 不再单独触发）
    assert pending_commits.format_brief_hint(sd, now) is None

def test_nudge_age_primary_fires_when_old(tmp_path):
    sd = tmp_path / "state"
    now = 100000
    pending_commits.append(sd, "sha", "t", now - 2000)  # age=2000s > 1800
    assert pending_commits.format_brief_hint(sd, now) is not None
```

- [ ] **Step 2：跑测试看失败（红）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_pending_commits.py -q -k nudge`
Expected: FAIL —— `test_nudge_age_primary_suppresses_fresh_burst`：现逻辑 `n>=3` 就触发（8>=3）→ 返回非 None。

- [ ] **Step 3：改 format_brief_hint（绿）**

把"count OR age"改成"age 为主、count 大幅调高作兜底"。`format_brief_hint` 的阈值判断：

```python
def format_brief_hint(
    state_dir: Path,
    now: int,
    threshold_count: int = 12,          # P-C1b：count 调高（TDD 爆量不刷屏），age 为主
    threshold_age_sec: int = DEFAULT_THRESHOLD_AGE_SEC,
) -> Optional[str]:
    data = read(state_dir)
    commits = data["commits"]
    if not commits:
        return None
    n = len(commits)
    age = now - commits[0]["ts"]
    # age 为主：未到 age 阈值且 count 未到（很高的）兜底值 → 不 nudge
    if age < threshold_age_sec and n < threshold_count:
        return None
    # ... 其余格式化不变 ...
```

（同步把模块常量 `DEFAULT_THRESHOLD_COUNT` 注释标"P-C1b：age 为主，count 仅极端兜底"。）

- [ ] **Step 4：跑测试看通过（绿）**

Run: `cd plugins/kdev-memory && python -m pytest tests/test_pending_commits.py -q`
Expected: PASS（新 nudge case + 旧 threshold case；若旧 case 断言 count=3 触发，按新语义改其断言或标注）。

- [ ] **Step 5：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/pending_commits.py plugins/kdev-memory/tests/test_pending_commits.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): nudge 阈值改 age 为主（TDD 爆量不刷屏）(P-C1b task 7/8)"
```

---

## Task 8：全量绿 + 版本 bump + 真 dispatch 手验

**Files:**
- Modify: `plugins/kdev-memory/.claude-plugin/plugin.json`（version）、`plugins/kdev-memory/CHANGELOG.md`

- [ ] **Step 1：全量测试绿**

Run: `cd plugins/kdev-memory && python -m pytest -q`
Expected: PASS（全部；注意 commit-tracker fixture 改 tool_input 后无遗漏旧 toolInput 调用）。若有红，定位修到绿，不跳过。

- [ ] **Step 2：bump version + CHANGELOG**

`plugin.json` version 从当前（`0.15.1`）bump 到 `0.16.0`（minor：新 feature）。`CHANGELOG.md` 加条目：

```markdown
## 0.16.0 — P-C1b：Step 落盘 transcript 溯源 + 模型他评
- fix(G-010): commit-tracker 读 tool_input（snake，官方契约）而非 toolInput → 复活死掉的 pending nudge
- feat: commit-tracker stash transcript_path；recorder 用 Bash sed/jq + transcript_extract.py 读真 transcript 抽事实（含 skills_invoked/subagents/subject），不再要主会话喂 ~30 行 YAML
- feat: 评估从 `### 模型自评` 改 `### 模型他评`（独立 recorder 读真 transcript，记录层修 MQ-2 confabulate），半残检测兼容两名
- feat: nudge 阈值改 age 为主（TDD 爆量不刷屏）
```

- [ ] **Step 3：commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/.claude-plugin/plugin.json plugins/kdev-memory/CHANGELOG.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "chore(kdev-memory): bump 0.16.0 — P-C1b transcript 溯源 + 模型他评 (P-C1b task 8/8)"
```

- [ ] **Step 4：真 dispatch 手验（merge 前，G-004 提醒）**

⚠️ G-004：plugin 改了须用户**刷 marketplace + 重启 session** 才 live。手验清单（重启后）：
1. 做一个真 commit → 查 `.kdev/memory/state/pending-commits.json` 有 `transcript_path` + 该 commit（验 Task 1/3 + nudge 活）。
2. dispatch step-recorder（不喂事实 YAML，只给 title）→ 看它 Bash 调 transcript_extract、落 Step 带 `### 模型他评` + skills_invoked + 真实工具数/SHA（验 Task 4/5）。
3. 故意造一个无证据扣分项场景，确认 recorder 不编造（写"未见明显问题"而非 confab）。
4. 跑 `python -m pytest -q` 终态全绿截图/记录。

---

## Self-Review（已过）

- **Spec coverage**：spec v0.5 §5.1（主控近零）→ Task 5；§5.2（抽取清单+skill/subject）→ Task 4/5；§5.4（切分粒度，commit 不当边界）→ 不变（recorder 工作单元粒度，无代码改动）；§5.5（nudge age 为主）→ Task 7；§5.6（Bash 不用 Read + toolInput 修 + transcript_path stash）→ Task 1/3/4/5；§5.8（他评替换自评，记录层修 MQ-2）→ Task 5/6。**全覆盖。**
- **Placeholder scan**：无 TBD/TODO；每个 code 步有真实代码 + 真实命令 + 预期。
- **Type consistency**：`transcript_path`/`since_offset`/`get_transcript_marker`/`transcript_extract.extract(path,since_offset,end_offset)` 跨 Task 2/3/4/5 一致；`extract` 返回键（tools_invoked/skills_invoked/subagents_dispatched/files_touched/commit_shas/errors_hit/error_samples/unreadable）在 Task 4 定义、Task 5 消费，名字一致。
- **已知非 TDD**：Task 5（agent prompt）+ Task 6 Step 5（schema 文档）+ Task 8 Step 4（真 dispatch）靠手验——prompt/doc 本质不可单测，故配 step_completeness 单测兜他评 schema 硬门 + merge 前真 dispatch 清单。
