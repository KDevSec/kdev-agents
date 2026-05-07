# kdev-design-flow v0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill that orchestrates the requirement-prototype-design pipeline by chaining `spec-kit:specify`, `frontend-design`, and `spec-kit:plan` with three review gates and configurable AI/human review modes.

**Architecture:** A single-skill plugin (`plugins/kdev-design-flow/`) with a slash-command entry point. SKILL.md drives orchestration declaratively (Claude follows steps); small Python helpers (`lib/`) handle slug normalization and `flow-state.json` IO. Intermediate artifacts land in `.kdev/design-flow/<slug>/` (gitignored), final deliverables in `docs/design-flow/<slug>/` (git-tracked).

**Tech Stack:** Python 3.10+ (helpers + tests), pytest, Markdown (SKILL.md + references), Claude Code Skill tool composition, Bash (git/file ops), jq optional.

**Spec:** [docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md](../specs/2026-05-07-kdev-design-flow-design.md)

---

## File Structure

```
plugins/kdev-design-flow/
├── .claude-plugin/
│   └── plugin.json                          # name + description + version
├── README.md                                # plugin overview, usage, install
├── CHANGELOG.md                             # version history
├── commands/
│   └── kdev-design-flow.md                  # /kdev-design-flow slash command
├── skills/
│   └── kdev-design-flow/
│       ├── SKILL.md                         # main orchestration instructions
│       └── references/
│           ├── stage1-sr-prompt.md          # SR-level requirement analysis prompt
│           ├── stage1-sr-template.md        # SR document structure
│           ├── review-gate-prompt.md        # universal review prompt (Claude self-eval / human shared)
│           └── output-merge-rules.md        # how iter-N.md → docs/design-flow/<slug>/
├── lib/
│   ├── __init__.py
│   ├── slug.py                              # feature-name → safe slug
│   └── flow_state.py                        # flow-state.json read/write
└── tests/
    ├── conftest.py                          # pytest fixtures (tmpdir helpers)
    ├── test_slug.py                         # slug edge cases
    ├── test_flow_state.py                   # state IO + corruption recovery
    └── test_skill_md_lint.py                # SKILL.md frontmatter + cross-refs
```

**Responsibilities:**

| File | Responsibility |
|------|----------------|
| `SKILL.md` | All orchestration logic Claude follows (5 stages, 3 gates, retry, abort, merge) |
| `commands/kdev-design-flow.md` | Slash command — invokes the skill with parsed `--review` / `--resume` args |
| `lib/slug.py` | Pure function: `slugify(name: str) -> str`. Handles Chinese, ASCII, dedup hash |
| `lib/flow_state.py` | `read_state(slug)`, `write_state(slug, dict)`, `init_state(slug)`. JSON file IO. |
| `references/stage1-sr-prompt.md` | Claude reads this when starting Stage 1 — the analysis prompt itself |
| `references/stage1-sr-template.md` | Section structure for SR document output |
| `references/review-gate-prompt.md` | Reusable review template (Stage name + criteria + artifact slot) |
| `references/output-merge-rules.md` | Rules for assembling final `docs/design-flow/<slug>/` files |
| `tests/test_*.py` | pytest unit tests for helpers + lint test for SKILL.md |

---

## Task 1: Spike — Verify `Skill` tool composability

**Goal:** Confirm the Claude `Skill` tool can be invoked from within a skill and that the parent skill regains control after the sub-skill runs. **If this fails, the entire orchestration architecture must be re-thought before continuing.**

**Files:**
- Create: `.worktrees/kdev-design-flow/spike-results.md` (worktree-only, not in plugin)

- [ ] **Step 1: Pick a low-cost target sub-skill that exists in this environment**

Check available skills via the system reminder injected at conversation start. Confirm `frontend-design:frontend-design` is present (we saw it in earlier context). If it's not, fall back to any other gstack skill (e.g., `simplify`).

Run: `ls /home/sec/.claude/plugins/cache/` and visually scan for installed plugins.
Expected: see at least one of: `superpowers`, plugin with `frontend-design`, or any installed skill from the gstack list.

- [ ] **Step 2: Write the spike scenario**

In a fresh terminal session (or this same session), invoke the `Skill` tool calling `frontend-design:frontend-design` with a deliberately tiny prompt: "Sketch a 1-button page that says 'spike test'."

- [ ] **Step 3: Record observations to spike-results.md**

Document in `.worktrees/kdev-design-flow/spike-results.md`:

```markdown
# Skill Tool Composability Spike

**Date:** 2026-05-07
**Sub-skill invoked:** frontend-design:frontend-design
**Prompt:** "Sketch a 1-button page that says 'spike test'."

## Observation 1: Did Claude regain control after the sub-skill finished?
[YES/NO + evidence]

## Observation 2: Was the sub-skill's output captured as a file or inline text?
[Description: where did the artifact land? File path? Inline markdown? Both?]

## Observation 3: Could the parent skill's instructions still execute next steps?
[YES/NO + did Claude continue following SKILL.md after sub-skill returned?]

## Verdict
- [ ] PROCEED — Skill composition works as designed
- [ ] ABORT — re-architect (e.g., rewrite as Bash subprocess, or split into separate slash commands chained by user)

## If ABORT, alternative architecture:
[describe]
```

- [ ] **Step 4: Decide PROCEED or ABORT**

If PROCEED: continue to Task 2.
If ABORT: stop. Escalate to user with the spike-results.md content and proposed alternative. **Do not write any plugin code** until user re-aligns.

- [ ] **Step 5: Commit spike result**

```bash
git add docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md spike-results.md
git commit -m "spike: verify Skill tool composability for kdev-design-flow"
```

(The spec is added in this commit because it was copied into the worktree but never committed yet.)

---

## Task 2: Plugin scaffolding

**Files:**
- Create: `plugins/kdev-design-flow/.claude-plugin/plugin.json`
- Create: `plugins/kdev-design-flow/README.md`
- Create: `plugins/kdev-design-flow/CHANGELOG.md`
- Create: `plugins/kdev-design-flow/commands/.keep`
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/.keep`
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/references/.keep`
- Create: `plugins/kdev-design-flow/lib/__init__.py`
- Create: `plugins/kdev-design-flow/tests/__init__.py`
- Create: `plugins/kdev-design-flow/tests/conftest.py`

- [ ] **Step 1: Create directory tree**

```bash
mkdir -p plugins/kdev-design-flow/.claude-plugin
mkdir -p plugins/kdev-design-flow/commands
mkdir -p plugins/kdev-design-flow/skills/kdev-design-flow/references
mkdir -p plugins/kdev-design-flow/lib
mkdir -p plugins/kdev-design-flow/tests
touch plugins/kdev-design-flow/commands/.keep
touch plugins/kdev-design-flow/skills/kdev-design-flow/.keep
touch plugins/kdev-design-flow/skills/kdev-design-flow/references/.keep
```

- [ ] **Step 2: Write plugin.json**

```json
{
  "name": "kdev-design-flow",
  "description": "需求-原型-设计流程编排：串联 spec-kit:specify、frontend-design、spec-kit:plan 三段已有 skill，加 3 个评审闸门（默认 Claude 自评，可切人工/混合），把'原始需求 → SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计'这条工程链路固化为一条可复跑的 skill。中间产物落 .kdev/design-flow/（gitignored），最终交付物落 docs/design-flow/。",
  "version": "0.1.0",
  "author": {
    "name": "1qljc"
  },
  "license": "MIT",
  "keywords": ["design", "requirements", "prototype", "orchestration", "spec-kit", "kdev"]
}
```

Write to `plugins/kdev-design-flow/.claude-plugin/plugin.json`.

- [ ] **Step 3: Write README.md skeleton**

```markdown
# kdev-design-flow

Claude Code 插件：把"需求 → 原型 → 设计"流程固化为一个 skill，串联 spec-kit、frontend-design 等已有 skill，并嵌入评审闸门避免方向漂移。

## 安装前置

- 必需：`spec-kit` 插件已安装（`/kdev-design-flow` 启动时会硬性检测）
- 推荐：`frontend-design` 插件（Stage 3 用）

## 快速开始

```bash
/kdev-design-flow 用户登录功能
/kdev-design-flow --resume yong-hu-deng-lu-gong-neng
/kdev-design-flow --review=human 用户登录功能
```

## 流程

1. 初步需求分析 → SR 需求文档
2. 评审闸门 #1
3. 进一步需求分析（spec-kit）→ AR 用户故事
4. 原型设计（frontend-design）→ 高保真原型
5. 评审闸门 #2
6. 实现方案设计（spec-kit）→ 概要 + 详细设计
7. 评审闸门 #3
8. 产物合并 → `docs/design-flow/<slug>/`

## 评审模式

- `--review=ai`（默认）：Claude 自评
- `--review=both`：Claude 自评 + 用户拍板
- `--review=human`：纯人工评审

详见 [设计文档](../../docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md)。
```

Write to `plugins/kdev-design-flow/README.md`.

- [ ] **Step 4: Write CHANGELOG.md**

```markdown
# Changelog

## 0.1.0 — 2026-05-07

- Initial release
- 5 stages × 3 review gates orchestration
- 3 review modes (ai / both / human), default ai
- Intermediate artifacts in `.kdev/design-flow/`, final in `docs/design-flow/`
- `--resume` to continue interrupted flow
- Hard dependency check on `spec-kit` plugin
```

Write to `plugins/kdev-design-flow/CHANGELOG.md`.

- [ ] **Step 5: Write `lib/__init__.py` and `tests/__init__.py`**

Both files are empty (just touch).

- [ ] **Step 6: Write `tests/conftest.py`**

```python
import os
import sys
import tempfile
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """Provides a temporary directory simulating a project workspace.

    Layout:
        <tmp>/
            .kdev/design-flow/   (created on demand by tests)
            docs/                (created on demand)
    """
    return tmp_path
```

Write to `plugins/kdev-design-flow/tests/conftest.py`.

- [ ] **Step 7: Verify pytest discovers the suite**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/ -v`
Expected: `no tests ran in <time>` (no failures, just empty suite).

- [ ] **Step 8: Commit**

```bash
git add plugins/kdev-design-flow/
git commit -m "feat(kdev-design-flow): initial plugin scaffolding"
```

---

## Task 3: Slug normalizer (TDD)

**Files:**
- Create: `plugins/kdev-design-flow/tests/test_slug.py`
- Create: `plugins/kdev-design-flow/lib/slug.py`

- [ ] **Step 1: Write failing tests**

Write to `plugins/kdev-design-flow/tests/test_slug.py`:

```python
"""Tests for lib.slug.slugify — feature-name → filesystem-safe slug."""
import re

from lib.slug import slugify


def test_pure_ascii_passthrough():
    assert slugify("user-login") == "user-login"


def test_ascii_with_spaces_to_hyphen():
    assert slugify("User Login Feature") == "user-login-feature"


def test_uppercase_normalized_to_lowercase():
    assert slugify("UserLogin") == "userlogin"


def test_chinese_falls_back_to_hash():
    """Chinese chars don't pinyin-romanize in v0.1; we use a stable hash + first ASCII chars if any."""
    result = slugify("用户登录功能")
    # No Chinese chars survive
    assert not re.search(r"[一-鿿]", result)
    # Stable: same input → same output
    assert slugify("用户登录功能") == result
    # Non-empty (8-char hash minimum)
    assert len(result) >= 8


def test_mixed_chinese_and_ascii():
    """Mixed input keeps ASCII portion + appends hash for the Chinese remainder."""
    result = slugify("用户 login 功能")
    assert "login" in result
    # And a hash suffix for stability
    assert re.search(r"-[a-f0-9]{6,}$", result)


def test_special_chars_stripped():
    assert slugify("foo/bar?baz!") == "foo-bar-baz"


def test_empty_string_raises():
    import pytest
    with pytest.raises(ValueError):
        slugify("")


def test_whitespace_only_raises():
    import pytest
    with pytest.raises(ValueError):
        slugify("   ")


def test_max_length_truncated():
    """v0.1: cap slug at 64 chars to avoid filesystem issues."""
    long_name = "a" * 200
    result = slugify(long_name)
    assert len(result) <= 64


def test_consecutive_hyphens_collapsed():
    assert slugify("foo---bar") == "foo-bar"


def test_leading_trailing_hyphens_stripped():
    assert slugify("--foo-bar--") == "foo-bar"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/test_slug.py -v`
Expected: `ModuleNotFoundError: No module named 'lib.slug'` for all 11 tests.

- [ ] **Step 3: Write minimal implementation**

Write to `plugins/kdev-design-flow/lib/slug.py`:

```python
"""feature-name → filesystem-safe slug.

v0.1 strategy:
- Lowercase
- ASCII chars + digits + hyphen pass through
- Whitespace → hyphen
- Other chars (incl. Chinese) → stripped, but if any non-ASCII chars existed,
  append a 6-char hash suffix for stability.
- Collapse consecutive hyphens, strip leading/trailing
- Truncate to 64 chars
- Empty result → raise ValueError
"""
import hashlib
import re


_ASCII_TOKEN = re.compile(r"[a-z0-9]+")
_NON_ASCII = re.compile(r"[^\x00-\x7f]")


def slugify(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("slug name must be non-empty")

    has_non_ascii = bool(_NON_ASCII.search(name))

    lowered = name.lower()
    # Replace any non-ASCII-alphanumeric run with hyphen
    ascii_only = re.sub(r"[^a-z0-9]+", "-", lowered)
    # Strip leading/trailing hyphens, collapse consecutives
    cleaned = re.sub(r"-+", "-", ascii_only).strip("-")

    if has_non_ascii:
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:6]
        cleaned = f"{cleaned}-{digest}" if cleaned else digest

    if not cleaned:
        raise ValueError(f"slug result empty for input {name!r}")

    return cleaned[:64]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/test_slug.py -v`
Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-design-flow/lib/slug.py plugins/kdev-design-flow/tests/test_slug.py
git commit -m "feat(kdev-design-flow): slug normalizer with hash fallback for non-ASCII"
```

---

## Task 4: flow-state.json IO (TDD)

**Files:**
- Create: `plugins/kdev-design-flow/tests/test_flow_state.py`
- Create: `plugins/kdev-design-flow/lib/flow_state.py`

- [ ] **Step 1: Write failing tests**

Write to `plugins/kdev-design-flow/tests/test_flow_state.py`:

```python
"""Tests for lib.flow_state — flow-state.json read/write/recovery."""
import json
from pathlib import Path

import pytest

from lib.flow_state import init_state, read_state, write_state, FlowStateError


def _state_dir(workspace: Path, slug: str) -> Path:
    return workspace / ".kdev" / "design-flow" / slug


def test_init_state_creates_directory_and_file(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")

    f = _state_dir(tmp_workspace, "feat-x") / "flow-state.json"
    assert f.exists()
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["slug"] == "feat-x"
    assert data["feature_name"] == "Feat X"
    assert data["review_mode"] == "ai"
    assert data["current_stage"] == 1
    assert data["current_iter"] == 1
    assert data["status"] == "in_progress"
    assert "created_at" in data


def test_read_state_returns_dict(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    assert state["slug"] == "feat-x"


def test_read_state_missing_raises(tmp_workspace):
    with pytest.raises(FlowStateError, match="no flow-state.json"):
        read_state(tmp_workspace, "does-not-exist")


def test_write_state_overwrites(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    state["current_stage"] = 3
    write_state(tmp_workspace, "feat-x", state)

    again = read_state(tmp_workspace, "feat-x")
    assert again["current_stage"] == 3


def test_write_state_atomic_via_tempfile(tmp_workspace):
    """Writes go through tempfile + rename, so partial writes can't corrupt."""
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    state = read_state(tmp_workspace, "feat-x")
    state["current_stage"] = 2
    write_state(tmp_workspace, "feat-x", state)

    # No leftover .tmp files
    state_dir = _state_dir(tmp_workspace, "feat-x")
    leftover = list(state_dir.glob("*.tmp"))
    assert leftover == []


def test_read_corrupt_state_raises(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    f = _state_dir(tmp_workspace, "feat-x") / "flow-state.json"
    f.write_text("{ this is not valid json", encoding="utf-8")
    with pytest.raises(FlowStateError, match="corrupt"):
        read_state(tmp_workspace, "feat-x")


def test_init_state_refuses_to_overwrite_existing(tmp_workspace):
    init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")
    with pytest.raises(FlowStateError, match="already exists"):
        init_state(tmp_workspace, "feat-x", review_mode="ai", feature_name="Feat X")


def test_invalid_review_mode_raises(tmp_workspace):
    with pytest.raises(ValueError, match="review_mode"):
        init_state(tmp_workspace, "feat-x", review_mode="psychic", feature_name="X")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/test_flow_state.py -v`
Expected: ImportError on all 8 tests.

- [ ] **Step 3: Write minimal implementation**

Write to `plugins/kdev-design-flow/lib/flow_state.py`:

```python
"""flow-state.json read/write/init for kdev-design-flow.

State schema (v0.1):
{
    "slug": str,                    # feature slug (filesystem-safe)
    "feature_name": str,            # original user-provided name (for display)
    "review_mode": "ai"|"both"|"human",
    "current_stage": int,           # 1..4
    "current_iter": int,            # 1..3 within current stage
    "status": "in_progress"|"completed"|"aborted",
    "created_at": str (ISO-8601),
    "updated_at": str (ISO-8601),
    "history": list[dict],          # gate decisions; each {"stage": int, "iter": int, "verdict": "PASS"|"FAIL", "reviewer": str}
}
"""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VALID_REVIEW_MODES = {"ai", "both", "human"}


class FlowStateError(Exception):
    """Raised when flow-state.json is missing, corrupt, or in an invalid transition."""


def _state_path(workspace: Path, slug: str) -> Path:
    return workspace / ".kdev" / "design-flow" / slug / "flow-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_state(workspace: Path, slug: str, *, review_mode: str, feature_name: str) -> dict:
    if review_mode not in VALID_REVIEW_MODES:
        raise ValueError(f"review_mode must be one of {sorted(VALID_REVIEW_MODES)}, got {review_mode!r}")

    path = _state_path(workspace, slug)
    if path.exists():
        raise FlowStateError(f"flow-state.json already exists for slug {slug!r}; use --resume or pick a different name")

    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "slug": slug,
        "feature_name": feature_name,
        "review_mode": review_mode,
        "current_stage": 1,
        "current_iter": 1,
        "status": "in_progress",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "history": [],
    }
    write_state(workspace, slug, state)
    return state


def read_state(workspace: Path, slug: str) -> dict:
    path = _state_path(workspace, slug)
    if not path.exists():
        raise FlowStateError(f"no flow-state.json at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FlowStateError(f"corrupt flow-state.json at {path}: {exc}") from exc


def write_state(workspace: Path, slug: str, state: dict) -> None:
    path = _state_path(workspace, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = _now_iso()

    # Atomic write: write to .tmp in same dir, then rename
    fd, tmp_path = tempfile.mkstemp(prefix=".flow-state-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/test_flow_state.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-design-flow/lib/flow_state.py plugins/kdev-design-flow/tests/test_flow_state.py
git commit -m "feat(kdev-design-flow): atomic flow-state.json IO with corruption detection"
```

---

## Task 5: SKILL.md frontmatter + skeleton

**Files:**
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md`

- [ ] **Step 1: Write SKILL.md frontmatter + skeleton**

Write to `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md`:

```markdown
---
name: kdev-design-flow
description: Use when 用户明确请求"把这个需求走一遍设计流程 / 帮我从需求到设计完整跑一遍 / 走 kdev 设计流程 / 完整需求分析+原型+设计 / 需求到方案一条龙 / 一站式跑需求分析"等表达，且明确希望产出 SR 文档 + AR 用户故事 + 高保真原型 + 概要详细设计这一整套交付物时触发。**SKIP**：用户只是在探讨想法 / 在判断是否值得做（应让 superpowers:brainstorming 或 office-hours 处理）；用户只想做单点设计或只要求其中一个产物（直接调对应 skill 即可）；用户在执行已有计划（应让 superpowers:executing-plans 处理）。本 skill 编排：内置 SR 分析 → spec-kit:specify (AR) → frontend-design (高保真原型) → spec-kit:plan (概要+详细设计)，3 个评审闸门，每闸门最多 3 次重试，3 档评审模式（默认 ai = Claude 自评）。
---

# kdev-design-flow Skill

把"原始需求 → SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计"这条工程链路固化为一个可复跑的 skill，串联已有 spec-kit 和 frontend-design 插件，并嵌入 3 个评审闸门避免方向漂移。

## 调用方式

通常通过 `/kdev-design-flow` 斜杠命令触发，不是 description 自动捕获（除非用户语气非常明确）。

## 工作流总览

| 阶段 | 用什么 | 输入 | 输出位置 |
|------|--------|------|----------|
| Stage 1 | 内置 prompt（references/stage1-sr-prompt.md） | 用户原始需求 | `.kdev/design-flow/<slug>/stage-1-sr/iter-N.md` |
| Gate 1 | 评审机制 | SR 文档 | (PASS / FAIL + 反馈) |
| Stage 2 | `Skill` 调 `spec-kit:specify` | 上一步通过的 SR 文档 | `.kdev/design-flow/<slug>/stage-2-ar/iter-N.md` |
| Stage 3 | `Skill` 调 `frontend-design:frontend-design` | 上一步通过的 AR 用户故事 | `.kdev/design-flow/<slug>/stage-3-prototype/iter-N/` |
| Gate 2 | 评审机制 | AR + 原型 | (PASS / FAIL + 反馈) |
| Stage 4 | `Skill` 调 `spec-kit:plan` | 上一步通过的 AR + 原型 | `.kdev/design-flow/<slug>/stage-4-plan/iter-N.md` |
| Gate 3 | 评审机制 | 设计方案 | (PASS / FAIL + 反馈) |
| Merge | 见 references/output-merge-rules.md | 各阶段最终通过版本 | `docs/design-flow/<slug>/` |

## 启动顺序

(详见后续 Task 6-12 各章节)
```

- [ ] **Step 2: Verify SKILL.md is parseable**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md').read().split('---')[1]))"`
Expected: dict printed with `name` and `description` keys.

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md
git commit -m "feat(kdev-design-flow): SKILL.md frontmatter + workflow overview"
```

---

## Task 6: Stage 1 references (SR prompt + template)

**Files:**
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/references/stage1-sr-prompt.md`
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/references/stage1-sr-template.md`

- [ ] **Step 1: Write SR prompt**

Write to `references/stage1-sr-prompt.md`:

````markdown
# Stage 1 — SR 级需求分析 Prompt

你正在为一个 feature 做 SR (System Requirements) 级别的需求分析。这是从"原始需求一句话"到"用户故事 (AR)"之间的桥接层：要把模糊愿望拆成可被 spec-kit:specify 接力的清晰需求。

## 输入

用户给的原始需求（一句话或一段话）：

<<<USER_INPUT
{{user_input}}
USER_INPUT>>>

## 你要做的

1. **识别核心价值主张**：这个 feature 解决谁的什么问题？为什么现在做？
2. **拆出 3-7 个 SR**（系统需求条目），每条覆盖一个独立的功能/质量维度。命名规范：`SR-<NN>: <一句话>`。
3. **每个 SR 给出**：
   - 验收标准（Given-When-Then 或 bullet 形式）
   - 关键约束（性能/安全/合规等）
   - 与其他 SR 的依赖关系
4. **识别 3-5 个开放问题**：你不确定但用户必须澄清的（用 `OPEN-Q-NN` 编号）。
5. **不要做的事**：不要画原型、不要写 API spec、不要写代码。这些是后续阶段的事。

## 输出格式

按 `references/stage1-sr-template.md` 的结构填写，落盘到 `.kdev/design-flow/{{slug}}/stage-1-sr/iter-{{iter}}.md`。

## 反馈循环

如果是第 2 或 3 次迭代（`iter > 1`），上一轮的评审反馈在：
`.kdev/design-flow/{{slug}}/stage-1-sr/iter-{{iter-1}}-review.md`

读它，然后**针对每条不通过点修订**，不要从头重写。
````

- [ ] **Step 2: Write SR template**

Write to `references/stage1-sr-template.md`:

```markdown
# {{feature_name}} — SR 级需求文档（iter {{iter}}）

**Slug:** {{slug}}
**Date:** {{date}}
**Iter:** {{iter}}

## 1. 价值主张

[一段话：为谁解决什么问题、为什么现在做]

## 2. SR 条目

### SR-01: <一句话>

**验收标准：**
- ...

**约束：**
- ...

**依赖：** (e.g., 依赖 SR-03 的 token 鉴权)

### SR-02: ...

(以此类推，3-7 个)

## 3. 开放问题

- **OPEN-Q-01:** [需要用户澄清的问题]
- **OPEN-Q-02:** ...

## 4. 显式不做

- [本 feature 不覆盖的、避免范围漂移的事项]
```

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/references/stage1-sr-prompt.md plugins/kdev-design-flow/skills/kdev-design-flow/references/stage1-sr-template.md
git commit -m "feat(kdev-design-flow): Stage 1 SR analysis prompt + template"
```

---

## Task 7: Review-gate prompt reference

**Files:**
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/references/review-gate-prompt.md`

- [ ] **Step 1: Write review prompt**

Write to `references/review-gate-prompt.md`:

````markdown
# 评审闸门通用 Prompt（Claude 自评 / 用户参考共用）

## 用途

每个 Stage 产出后，评审闸门用这个 prompt 评估产物。Claude 在 `--review=ai` 或 `--review=both` 模式下扮演评审者；在 `--review=human` 模式下，这个 prompt 的"成功标准"段也用作给用户的判断依据。

## 评审者要做的事

你正在评审 **{{stage_name}}** 阶段的产出。

**这是 iter {{iter}} of max 3。**

### {{stage_name}} 的成功标准（**逐条对照，禁止自由发挥**）

{{stage_specific_criteria}}

### 产物原文

<<<ARTIFACT
{{artifact_content}}
ARTIFACT>>>

### 必填输出（严格格式）

```
VERDICT: PASS | FAIL

UNCHECKED_CRITERIA: <comma-separated list of criteria IDs that the artifact does not satisfy; empty if PASS>

ISSUES (only if FAIL, max 5, priority order):
1. <one-line issue description>
2. ...

REVISIONS (only if FAIL):
1. <concrete revision instruction the next iter can apply directly>
2. ...
```

**禁止**：补充表扬话、扩展评论、解释为什么 PASS。只填这些字段。

## Stage 特定的成功标准

### Stage 1 (SR 文档)

- C-1.1: 包含 3-7 个 SR 条目
- C-1.2: 每个 SR 有验收标准 + 约束 + 依赖（三段都不空）
- C-1.3: 至少 3 个开放问题（OPEN-Q-NN）
- C-1.4: 显式列出"不做的事"
- C-1.5: 没有把原型/API/代码细节写进来（应在后续阶段）

### Stage 3 (AR + 原型 联合评审 — 这是 Gate 2)

- C-2.1: AR 用户故事覆盖了 Stage 1 所有 SR（每个 SR 至少对应 1 个 user story）
- C-2.2: 原型 HTML 可在浏览器打开且无 JS 报错
- C-2.3: 原型涵盖 AR 中的核心交互路径
- C-2.4: 原型未包含真实凭证 / 内部 URL / 敏感数据
- C-2.5: 原型样式与产品语境匹配（不是默认浏览器灰色按钮）

### Stage 4 (设计方案 — 这是 Gate 3)

- C-3.1: 包含概要设计（架构图 / 模块划分 / 数据流）
- C-3.2: 包含详细设计（关键接口 + 数据模型）
- C-3.3: 覆盖了 Stage 1 SR 的所有约束（性能/安全/合规）
- C-3.4: 列出至少 3 项已识别的实现风险 + 缓解
- C-3.5: 与 Stage 3 原型的交互一致（没有原型上有但设计里漏掉的功能）
````

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/references/review-gate-prompt.md
git commit -m "feat(kdev-design-flow): review-gate prompt with stage-specific criteria"
```

---

## Task 8: Output merge rules reference

**Files:**
- Create: `plugins/kdev-design-flow/skills/kdev-design-flow/references/output-merge-rules.md`

- [ ] **Step 1: Write merge rules**

Write to `references/output-merge-rules.md`:

````markdown
# 产物合并规则

通过最后一个评审闸门（Gate 3）后，把中间产物合并/复制到 `docs/design-flow/<slug>/` 作为最终交付物。

## 合并映射

| 来源（中间产物） | 目标（最终交付物） | 合并方式 |
|------------------|--------------------|----------|
| `.kdev/design-flow/<slug>/stage-1-sr/iter-{{last_pass}}.md` + `.kdev/design-flow/<slug>/stage-2-ar/iter-{{last_pass}}.md` | `docs/design-flow/<slug>/01-requirements.md` | 拼接：先 SR 再 AR，加 `# 第一部分：SR 级需求` / `# 第二部分：AR 级用户故事` 二级分节 |
| `.kdev/design-flow/<slug>/stage-3-prototype/iter-{{last_pass}}/` | `docs/design-flow/<slug>/02-prototype/` | 整目录递归复制（保留 frontend-design 输出的子结构） |
| `.kdev/design-flow/<slug>/stage-4-plan/iter-{{last_pass}}.md` | `docs/design-flow/<slug>/03-design.md` | 直接复制（spec-kit:plan 已经产出了完整概要+详细设计） |

## 合并步骤

1. 从 `flow-state.json` 读取每个 stage 最后一次 PASS 的 `iter` 值（在 `history[]` 里查最大的 `iter` 且 `verdict=PASS`）
2. 创建目标目录：`mkdir -p docs/design-flow/<slug>/02-prototype`
3. 按上表执行复制 / 拼接
4. 生成 `docs/design-flow/<slug>/README.md`（索引页），内容：

```markdown
# {{feature_name}}

**Slug:** {{slug}}
**生成时间:** {{date}}
**生成方式:** kdev-design-flow v0.1（手动 review 模式：{{review_mode}}）

## 交付物

- [01-requirements.md](01-requirements.md) — SR 需求文档 + AR 用户故事
- [02-prototype/](02-prototype/) — 高保真原型（HTML）
- [03-design.md](03-design.md) — 概要设计 + 详细设计

## 流程记录

中间产物（迭代历史 + 评审记录）保留在 `.kdev/design-flow/{{slug}}/`，未提交 git。
```

5. 在 `flow-state.json` 设 `status = "completed"` + 写 `completed_at` 字段。

## 不做合并的情况

- `flow-state.json` 中 `status != "in_progress"`：流程已结束（aborted 或 completed），不重复合并
- 任一 stage 没有 PASS 记录：报错"Stage N has no PASS in history; aborting merge"

## 幂等性

合并步骤可重复运行（例如用户想刷新最终产物）：
- 目标目录如果存在，先用 `git status -- docs/design-flow/<slug>/` 检查是否有未提交改动，有则提示用户先处理
- 无未提交改动 → 直接覆盖
````

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/references/output-merge-rules.md
git commit -m "feat(kdev-design-flow): output merge rules with idempotency guard"
```

---

## Task 9: SKILL.md — Stage 1 + Gate machinery sections

**Files:**
- Modify: `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md`

- [ ] **Step 1: Append Stage 1 + Gate sections to SKILL.md**

Append to existing SKILL.md (after the "## 启动顺序" line — replace that placeholder):

````markdown
## 启动顺序

每次激活，按顺序执行：

### 步骤 0：参数解析

斜杠命令 `/kdev-design-flow` 注入 `$ARGUMENTS`，需要解析：
- 必传：`feature_name`（位置参数；中文/英文均可）
- 可选：`--review=ai|both|human`（默认 `ai`）
- 可选：`--resume`（无值；存在即"恢复模式"）

如果 `--resume`：跳到"恢复模式"段（见下面"恢复"节）。

### 步骤 1：依赖检测

检查 `Skill` 工具列表中是否存在：
- `spec-kit:specify`
- `spec-kit:plan`

任一缺失 → 立即中断，向用户输出：

```
❌ kdev-design-flow 需要 spec-kit 插件，但当前环境未安装。
请先运行：
    claude plugin install spec-kit
然后重新触发 /kdev-design-flow。
```

`frontend-design` 缺失 → 警告但允许用户选择是否继续（Stage 3 没它会跳到"手动占位"模式）。

### 步骤 2：初始化状态

```bash
python3 -c "
from pathlib import Path
import sys
sys.path.insert(0, '${CLAUDE_PLUGIN_ROOT}')
from lib.slug import slugify
from lib.flow_state import init_state
slug = slugify('${feature_name}')
init_state(Path.cwd(), slug, review_mode='${review_mode}', feature_name='${feature_name}')
print(slug)
"
```

记录返回的 `slug`，后续所有路径用它。

### 步骤 3：自动 .gitignore

检查仓库根 `.gitignore`：

```bash
grep -qE "^/?\.kdev/design-flow/?$" .gitignore || echo "/.kdev/design-flow/" >> .gitignore
```

如果改了 `.gitignore`，提示用户"已自动追加 .gitignore（建议本次提交带上）"，但**不自动 commit**——交给用户决定何时提交。

### 步骤 4：进入主循环

按 Stage 1 → Gate 1 → Stage 2 → Stage 3 → Gate 2 → Stage 4 → Gate 3 → Merge 顺序执行。

---

## Stage 1: 初步需求分析

每次进入 Stage 1（包括 iter > 1 重试）：

1. Read `references/stage1-sr-prompt.md`
2. Read `references/stage1-sr-template.md`
3. 把模板中的 `{{user_input}}` / `{{slug}}` / `{{iter}}` / `{{feature_name}}` / `{{date}}` 占位符填好
4. 按 prompt 指示产出 SR 文档
5. Write 到 `.kdev/design-flow/<slug>/stage-1-sr/iter-<iter>.md`
6. 进入 Gate 1

---

## 评审闸门通用机器（适用于 Gate 1/2/3）

每次到一个 Gate：

1. 从 `flow-state.json` 读 `review_mode`、`current_stage`、`current_iter`
2. Read `references/review-gate-prompt.md`
3. 找到本 stage 对应的"成功标准"段
4. 把待评审产物（上一步的输出文件）读进来
5. 按 `review_mode` 分支：

### 5a. `--review=ai`（默认）

- Claude **自身**按 prompt 输出 VERDICT + UNCHECKED_CRITERIA + ISSUES + REVISIONS
- 把这段输出保存到 `.kdev/design-flow/<slug>/stage-<N>/iter-<iter>-review.md`
- 在 `flow-state.json` 的 `history` 数组追加：
  `{"stage": N, "iter": iter, "verdict": "PASS"|"FAIL", "reviewer": "claude-self"}`

### 5b. `--review=both`

- 先按 5a 跑一遍 Claude 自评
- 然后用 `AskUserQuestion` 弹窗：
  - 问题: "Claude 自评结论：{{verdict}}。{{issues_summary if FAIL}}。你是否同意？"
  - 选项: "同意 Claude 判断" / "我有不同意见（手填）"
- 用户最终结论覆盖 Claude 的，写到 review.md，记录 `reviewer: "claude-self+human"` 或 `reviewer: "human-override"`

### 5c. `--review=human`

- 直接用 `AskUserQuestion` 让用户判 PASS/FAIL + 给反馈
- 写到 review.md，记录 `reviewer: "human"`

### 5d. PASS 后行为

- 在 `flow-state.json` 设 `current_stage += 1`, `current_iter = 1`
- 继续下一 Stage

### 5e. FAIL 后行为

- 在 `flow-state.json` 设 `current_iter += 1`
- 如果 `current_iter > 3`：进入"中断"分支
- 否则：回到当前 Stage，重新跑（新 iter 会读上一轮的 review.md 作为反馈）

### 5f. 中断（3 次仍 FAIL）

- 在 `flow-state.json` 设 `status = "aborted"`, `aborted_at = now`, `aborted_reason = "review failed 3 times at gate <N>"`
- Write `.kdev/design-flow/<slug>/aborted.md`：

```markdown
# Aborted: {{feature_name}}

**Slug:** {{slug}}
**Aborted at:** {{date}} (Gate {{N}})
**Reason:** review FAILed 3 times in a row

## 最后一轮的 review

(粘贴 iter-3-review.md 的全文)

## 三次迭代的产物

- iter-1: `.kdev/design-flow/{{slug}}/stage-{{N}}/iter-1.md`
- iter-2: ...
- iter-3: ...

## 接下来怎么办

1. 读三次 review，找到 Claude 始终绕不过去的那条 criterion
2. 决定：是降低标准（修改 review-gate-prompt.md 里的 criterion）、还是手动接管这个 stage、还是终止 feature
3. 决定后用 `/kdev-design-flow --resume {{slug}}` 继续（注意先把 flow-state 里 status 改回 in_progress）
```

- 通知用户中断 + 给出 aborted.md 路径，停止流程。

````

- [ ] **Step 2: Verify SKILL.md still parses**

Run: `python3 -c "import yaml; print(yaml.safe_load(open('plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md').read().split('---')[1])['name'])"`
Expected: `kdev-design-flow`

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md
git commit -m "feat(kdev-design-flow): SKILL.md Stage 1 + universal review gate machinery"
```

---

## Task 10: SKILL.md — Stages 2-4 (delegate to other skills)

**Files:**
- Modify: `plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md`

- [ ] **Step 1: Append Stages 2-4 sections to SKILL.md**

Append to SKILL.md:

````markdown
## Stage 2: 进一步需求分析（spec-kit:specify）

1. Read 上一步通过的 SR 文档：`.kdev/design-flow/<slug>/stage-1-sr/iter-<last_pass>.md`
2. 调 `Skill` 工具，name=`spec-kit:specify`，提示词模板：

```
我有一份 SR 级需求文档（已通过初步评审），请按 spec-kit:specify 流程把它细化成 AR 级用户故事。

输入 SR 文档：
<<<
{{paste sr doc content}}
>>>

输出落盘路径建议（spec-kit 自己决定即可）：
.kdev/design-flow/<slug>/stage-2-ar/iter-<iter>.md

约束：
- 用户故事覆盖每个 SR
- 每个 user story 包含 acceptance criteria
- 不要重复 SR 文档里已经有的"显式不做"清单
```

3. spec-kit:specify 完成后，确认产物文件存在于 `.kdev/design-flow/<slug>/stage-2-ar/iter-<iter>.md`。如果落到了别的位置（spec-kit 默认路径），用 `mv` 移过来。
4. **此处不评审**——Stage 2 + Stage 3 共用 Gate 2，等 Stage 3 跑完一起评。

## Stage 3: 原型设计（frontend-design）

1. Read 上一步的 AR 用户故事
2. 调 `Skill` 工具，name=`frontend-design:frontend-design`，提示词模板：

```
为下面这组用户故事设计一个高保真原型（HTML/CSS/必要的 JS），目标是评审用，不是生产用。

用户故事：
<<<
{{paste ar content}}
>>>

约束：
- 可在浏览器直接打开（单 HTML 文件或带 index.html 的目录）
- 涵盖核心交互路径（不需要每个 edge case 都画）
- 视觉语言要和产品语境匹配（不要是默认浏览器原生灰色按钮）
- 不要内嵌真实凭证 / 内部 URL / 敏感数据
- 输出落盘到 `.kdev/design-flow/<slug>/stage-3-prototype/iter-<iter>/`
```

3. frontend-design 完成后，确认产物在 `.kdev/design-flow/<slug>/stage-3-prototype/iter-<iter>/`，至少有 `index.html`。如果不在，用 `mv` 移过来。
4. **进入 Gate 2**（共评 AR + 原型；评审 prompt 把 stage-2-ar 和 stage-3-prototype 的产物都喂进去）

## Stage 4: 实现方案设计（spec-kit:plan）

1. Read Stage 2 的 AR 文档 + Stage 3 的原型 README/index.html
2. 调 `Skill` 工具，name=`spec-kit:plan`，提示词模板：

```
为下面这组 AR 用户故事 + 高保真原型，做完整的实现方案设计（概要 + 详细）。

用户故事：
<<<
{{paste ar}}
>>>

原型路径：
.kdev/design-flow/<slug>/stage-3-prototype/iter-<last_pass>/

输出要求：
- 概要设计：架构图（Mermaid 也行）/ 模块划分 / 数据流
- 详细设计：关键接口签名 / 数据模型（schema）/ 关键算法或状态机
- 实现风险 ≥ 3 项 + 缓解
- 输出落盘到 `.kdev/design-flow/<slug>/stage-4-plan/iter-<iter>.md`
```

3. spec-kit:plan 完成后，确认产物文件位置正确。
4. **进入 Gate 3**

## 通过 Gate 3 后：产物合并

1. Read `references/output-merge-rules.md`
2. 严格按规则执行（包括幂等性检查、`status = completed` 标记）
3. 完成后用一段中文向用户汇报：
   - 流程总耗时（用 `created_at` - `completed_at` 计算）
   - 三个 Gate 各自跑了多少 iter（从 history 聚合）
   - 最终交付物路径（`docs/design-flow/<slug>/`）

## 恢复模式（`--resume <slug>`）

如果用户带 `--resume <slug>`：

1. Read `flow-state.json`，校验 `status == "in_progress"`
2. 如果 `status == "aborted"`：提示用户"流程被标记为 aborted，先手动改 flow-state.json 里 status 字段才能继续"
3. 否则：从 `current_stage` + `current_iter` 接着跑

## 显式不做的事（v0.1）

- ❌ 不会主动去删 `.kdev/design-flow/<slug>/`（即使流程完成）——保留迭代历史是 B 方案的训练数据
- ❌ 不会跨会话续跑评审中的 `AskUserQuestion`（所以 `both`/`human` 模式中途断会话，需要 `--resume` 重新进入这一 Gate）
- ❌ 不支持自定义 stage 顺序、跳过 stage、并行多 feature

````

- [ ] **Step 2: Verify SKILL.md still parses**

Run: `python3 -c "import yaml; doc = open('plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md').read().split('---'); print(yaml.safe_load(doc[1])['name']); print('lines:', len(doc[2].splitlines()))"`
Expected: `kdev-design-flow` and a line count > 100.

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-design-flow/skills/kdev-design-flow/SKILL.md
git commit -m "feat(kdev-design-flow): SKILL.md Stages 2-4 + merge + resume mode"
```

---

## Task 11: SKILL.md lint test

**Files:**
- Create: `plugins/kdev-design-flow/tests/test_skill_md_lint.py`

- [ ] **Step 1: Write failing tests**

Write to `plugins/kdev-design-flow/tests/test_skill_md_lint.py`:

```python
"""Lint tests for SKILL.md — frontmatter validity + cross-references resolve."""
from pathlib import Path

import pytest
import yaml

PLUGIN = Path(__file__).resolve().parent.parent
SKILL_MD = PLUGIN / "skills" / "kdev-design-flow" / "SKILL.md"
REF_DIR = PLUGIN / "skills" / "kdev-design-flow" / "references"


def _split_frontmatter(text: str) -> tuple[dict, str]:
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("SKILL.md missing frontmatter delimiters")
    return yaml.safe_load(parts[1]), parts[2]


def _read_skill():
    return _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))


def test_frontmatter_has_required_fields():
    fm, _ = _read_skill()
    assert fm.get("name") == "kdev-design-flow"
    assert "description" in fm and len(fm["description"]) > 50


def test_description_mentions_skip_branches():
    """description must explicitly say what NOT to trigger on (per spec §3.2)."""
    fm, _ = _read_skill()
    assert "SKIP" in fm["description"] or "skip" in fm["description"].lower()


def test_description_mentions_three_review_modes():
    """description must mention the three review modes so callers know they exist."""
    fm, _ = _read_skill()
    desc = fm["description"]
    assert "ai" in desc.lower() and "both" in desc.lower() and "human" in desc.lower()


@pytest.mark.parametrize("ref_name", [
    "stage1-sr-prompt.md",
    "stage1-sr-template.md",
    "review-gate-prompt.md",
    "output-merge-rules.md",
])
def test_referenced_files_exist(ref_name):
    """All references/* files mentioned in SKILL.md must actually exist on disk."""
    _, body = _read_skill()
    assert ref_name in body, f"SKILL.md does not reference {ref_name}"
    assert (REF_DIR / ref_name).exists(), f"{ref_name} referenced but not on disk"


def test_skill_md_does_not_mention_codex():
    """v0.1 explicitly does not depend on codex (per spec patch from user feedback)."""
    fm, body = _read_skill()
    assert "codex" not in fm["description"].lower()
    assert "codex" not in body.lower()


def test_skill_md_mentions_all_three_stages():
    _, body = _read_skill()
    assert "Stage 1" in body
    assert "Stage 2" in body
    assert "Stage 3" in body
    assert "Stage 4" in body
    assert "Gate 1" in body or "Gate 1" in body  # both spellings ok
    assert "Gate 2" in body
    assert "Gate 3" in body
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `cd plugins/kdev-design-flow && python -m pytest tests/test_skill_md_lint.py -v`
Expected: all pass (we wrote SKILL.md correctly in Tasks 5/9/10).

If any FAIL: fix SKILL.md to match, do not relax the test.

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-design-flow/tests/test_skill_md_lint.py
git commit -m "test(kdev-design-flow): SKILL.md lint (frontmatter + cross-refs + no-codex)"
```

---

## Task 12: Slash command file

**Files:**
- Create: `plugins/kdev-design-flow/commands/kdev-design-flow.md`

- [ ] **Step 1: Write the command file**

Write to `plugins/kdev-design-flow/commands/kdev-design-flow.md`:

````markdown
---
description: 走完整需求-原型-设计流程：SR 需求文档 → AR 用户故事 → 高保真原型 → 概要+详细设计，3 个评审闸门
argument-hint: <feature-name> [--review=ai|both|human] [--resume]
---

# /kdev-design-flow

把"原始需求 → 工程设计文档"这一条链路固化为可复跑的 skill。

## 用法

```
/kdev-design-flow 用户登录功能
/kdev-design-flow 用户登录功能 --review=both
/kdev-design-flow --resume yong-hu-deng-lu-gong-neng
```

## 参数

- `<feature-name>`：必填（除非用 `--resume`）。中文/英文均可，会被规范化为 slug。
- `--review=ai|both|human`：评审模式，默认 `ai`（Claude 自评）。
- `--resume <slug>`：恢复中断的流程（不带 feature-name）。

## 你的任务

调用 `kdev-design-flow` skill，把 `$ARGUMENTS` 透传给它。skill 自身负责参数解析、依赖检测、状态初始化和主循环。

参数原文：`$ARGUMENTS`

按 `kdev-design-flow` skill 的 SKILL.md 步骤执行。
````

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-design-flow/commands/kdev-design-flow.md
git commit -m "feat(kdev-design-flow): slash command entry point"
```

---

## Task 13: E2E smoke test (manual)

**Files:**
- Create: `plugins/kdev-design-flow/tests/e2e-smoke.md` (manual test record)

- [ ] **Step 1: Set up sandbox project**

```bash
mkdir -p /tmp/kdev-design-flow-smoke
cd /tmp/kdev-design-flow-smoke
git init
echo "Smoke test sandbox" > README.md
git add README.md && git commit -m "init"
```

- [ ] **Step 2: Manually invoke the skill (in this Claude session, after install)**

In the sandbox dir, invoke `/kdev-design-flow 一个简单计数器 --review=ai`. The skill should:

1. Detect spec-kit (skip if dev environment doesn't have it — note that as expected limitation)
2. Slugify "一个简单计数器" to something like `yi-ge-jian-dan-ji-shu-qi-<hash>` or `<hash>-only`
3. Init `.kdev/design-flow/<slug>/`
4. Append `/.kdev/design-flow/` to .gitignore
5. Run Stage 1 → produce `iter-1.md`
6. Self-review → PASS or FAIL
7. (At least) reach Gate 1

- [ ] **Step 3: Record observations**

Write to `plugins/kdev-design-flow/tests/e2e-smoke.md`:

```markdown
# E2E Smoke Test — 2026-05-07

**Sandbox:** /tmp/kdev-design-flow-smoke
**Command:** `/kdev-design-flow 一个简单计数器 --review=ai`

## Observations

- [ ] Slugify produced: `<actual-slug>`
- [ ] `.gitignore` updated: yes/no
- [ ] flow-state.json created at `.kdev/design-flow/<slug>/flow-state.json`: yes/no
- [ ] Stage 1 produced `iter-1.md`: yes/no
- [ ] Self-review gave VERDICT: PASS|FAIL
- [ ] Reached Stage 2 (spec-kit:specify): yes/no/skipped-due-to-missing-dep

## Issues found

[describe]

## Verdict

- [ ] v0.1 ships
- [ ] Need to fix N before shipping
```

- [ ] **Step 4: Fix any issues found**

For each issue in the smoke test, file an inline fix (new mini-task or direct edit if trivial). After fixes, re-run the smoke test.

- [ ] **Step 5: Commit smoke test record**

```bash
cd /home/sec/workspace/org/kdev-agents/.worktrees/kdev-design-flow
git add plugins/kdev-design-flow/tests/e2e-smoke.md
git commit -m "test(kdev-design-flow): E2E smoke test record"
```

---

## Task 14: README polish + final verification

**Files:**
- Modify: `plugins/kdev-design-flow/README.md`
- Modify: `plugins/kdev-design-flow/CHANGELOG.md`

- [ ] **Step 1: Add a "limitations" section to README.md**

Append to README.md:

```markdown
## 已知限制 (v0.1)

- 中间产物落 `.kdev/design-flow/`，不自动清理（保留迭代历史作 B 方案训练数据）
- `--review=both` / `--review=human` 模式下，会话中断后必须 `--resume` 重新进入评审闸门
- 不支持自定义 stage 顺序、跳过 stage、并行多 feature
- spec-kit:specify / spec-kit:plan 是硬依赖，没装会硬中断
- 中文 feature-name 走 hash 兜底（v0.1 不依赖拼音库）

详见 [设计文档](../../docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md)。
```

- [ ] **Step 2: Run all tests**

```bash
cd plugins/kdev-design-flow && python -m pytest tests/ -v
```

Expected: all tests pass (slug + flow_state + skill_md_lint).

- [ ] **Step 3: Commit final polish**

```bash
git add plugins/kdev-design-flow/README.md
git commit -m "docs(kdev-design-flow): document v0.1 limitations"
```

- [ ] **Step 4: Verify branch is ready for PR**

```bash
git log --oneline main..feat/kdev-design-flow
```

Expected: ~14 commits, one per task.

```bash
git status
```

Expected: clean working tree.

---

## Done Criteria (v0.1)

All items must hold before declaring v0.1 shippable:

- [ ] Spike (Task 1) PROCEED verdict written and committed
- [ ] All Python tests pass: `python -m pytest plugins/kdev-design-flow/tests/`
- [ ] SKILL.md frontmatter parses; lint test passes
- [ ] E2E smoke test reached at least Gate 1 in sandbox
- [ ] No `codex` mentions anywhere in plugin (per spec patch)
- [ ] `.gitignore` self-write works (creates `/.kdev/design-flow/` line if missing)
- [ ] All 14 tasks committed atomically (one feat/test/docs commit each)
- [ ] PR description references the spec doc and links the spike result
