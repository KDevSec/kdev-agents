# kdev-cluster-x3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `kdev-cluster-x3` plugin — KDev 多智能体集群的 **X3 矩阵式 / 轻组长 / 顾问 PM** 落地实现：1 主控员 + 4 轻组长 + 25 工作 agent + 13 评审节点 + events.log 驱动的 BLOCKED 自动应急 hook + state.md/handoffs 跨组数据总线 + 多形态 HUD。

**Architecture:**
- 一个 Claude Code plugin（`plugins/kdev-cluster-x3/`），包含 30 个 agent definition、4 个 skill（`/kdev:start-feature` / `/kdev:hud` / `/kdev:status` / `kdev-statusline.sh`）、10 份 standards、1 个 `on-blocked` hook、若干 Python helpers。
- 数据底座：`.kdev/state.md`（4 组 section）+ `.kdev/events.log`（事件流）+ `.kdev/handoffs/{reqs,dev,test,review}/`（跨组产物总线）。
- 通信模型：用户↔主控员；主控员**直接派工作 agent**（快路径，2 跳）；主控员只在阶段聚合 / 异常时调组长（慢路径）；工作 agent 直接派评审员；BLOCKED → events.log → hook 自动派组长。
- 13 个评审节点（R2/R3/R4/R5 + D1/D2/D4/D5 + T1/T2 + F1/F2），8 阻断 / 3 告警 / 2 抽查。

**Tech Stack:**
- Python 3.10+（helpers + pytest 单测 + hook 逻辑）
- Markdown（agent definitions + standards + skills + commands）
- Bash（`kdev-statusline.sh`、cross-platform 由 `run-python-hook.cmd` 已就绪范式承载）
- Claude Code plugin schema（`.claude-plugin/plugin.json` + `hooks/hooks.json`）

**Spec sources:**
- [README](../../plugins/kdev-cluster-x3/README.md)
- [X1 vs X3 对比文档 v0.2](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md) §2 + §3 + §5
- [方案 B 实施基线 v0.1](../../docs/framework/01-design/2026-05-27-01-KDev多智能体集群架构-方案B-v0.1.md) §3 + §6 + §7

---

## Locked-in Decisions

这些决策已在 v0.2 对比文档 §3.5 / v0.1 §3 拍板，本计划直接采纳：

| # | 决策 | 来源 |
|---|---|---|
| 1 | AR 编号统一格式 `AR-{DOMAIN}-{MAJOR}.{MINOR}.{PATCH}` | v0.1 §3.1 |
| 2 | 阶段聚合节点 = 4 个（reqs/dev/test 完成 + 终审）| v0.2 §3.5 #1 |
| 3 | BLOCKED 呼救 = 方案 b：events.log 写事件 + hook 自动派组长 | v0.2 §3.5 #2 |
| 4 | 评审标准存储 = `plugins/kdev-cluster-x3/standards/` | v0.2 §3.5 #3（路径按 README 收敛到 cluster 插件内）|
| 5 | 主控员快/慢路径 = 单 step→快，阶段结束/blocked→慢 | v0.2 §3.5 #4 |
| 6 | 评审循环上限 = 3 次，第 4 次自动写 `blocked` 触发组长 | v0.2 §5.5 |
| 7 | Agent model 分配 | 全局 CLAUDE.md「模型分工策略」：主控员/4 组长/IR-SR-评审员=opus；执行类=sonnet |
| 8 | 派单背景化 | 主控员长任务调组长 / 工作 agent 用 `run_in_background:true`；评审用同步（阻断节点必须等返回）|

剩余 v0.2 §5.7 待细化议题（IR 是否独立评审 / TDD 增量颗粒度 / 评审员冲突仲裁等）**不阻塞本计划**——在 Task 28 整理 follow-ups。

---

## File Structure

```
plugins/kdev-cluster-x3/
├── .claude-plugin/
│   └── plugin.json                        # 已存在（Phase 1）
├── README.md                              # 已存在
├── CLAUDE.md                              # Task 27 新增（插件级使用指引）
├── CHANGELOG.md                           # Task 27 新增
├── agents/                                # 30 个 agent definitions
│   ├── 主控员.md
│   ├── 需求组长.md / 开发组长.md / 测试组长.md / 审查组长.md
│   ├── reqs/  ← 5 工作员
│   │   ├── 需求澄清师.md
│   │   ├── 需求规格师.md
│   │   ├── 需求拆解师.md
│   │   ├── 原型设计师.md
│   │   └── 方案设计师.md
│   ├── dev/   ← 6 工作员
│   │   ├── 环境对齐员.md
│   │   ├── 实施计划师.md
│   │   ├── TDD实现员.md
│   │   ├── E2E验收员.md
│   │   ├── 安全扫描员.md
│   │   └── 部署上线员.md
│   ├── test/  ← 4 工作员
│   │   ├── 测试点设计师.md
│   │   ├── 测试用例渲染员.md
│   │   ├── UI自动化工程师.md
│   │   └── API自动化工程师.md
│   └── review/ ← 10 评审员（评审池共享）
│       ├── SR评审员.md
│       ├── 原型评审员.md
│       ├── 方案设计评审员.md
│       ├── 代码评审员.md
│       ├── 质量评审员.md
│       ├── 安全评审员.md
│       ├── 测试设计评审员.md
│       ├── CEO视角评审员.md
│       ├── 架构评审员.md
│       └── 终审聚合员.md
├── skills/
│   ├── kdev-start-feature/SKILL.md        # 主入口编排 skill
│   ├── kdev-hud/SKILL.md                  # 3 模式 HUD（markdown / box / watch）
│   ├── kdev-status/SKILL.md               # 单点状态快照
│   └── kdev-statusline/kdev-statusline.sh # CLI statusLine 一行 HUD
├── commands/
│   ├── kdev-start-feature.md              # /kdev:start-feature 斜杠命令
│   ├── kdev-hud.md                        # /kdev:hud
│   └── kdev-status.md                     # /kdev:status
├── standards/                             # 评审 checklist + 组长 meta 资产
│   ├── reqs/system-prompt-template.md
│   ├── dev/system-prompt-template.md
│   ├── test/system-prompt-template.md
│   ├── review/system-prompt-template.md   # 4 组长公用 PM 顾问模板（参数化区别）
│   └── review/
│       ├── SR评审员-checklist.md
│       ├── 原型评审员-checklist.md
│       ├── 方案设计评审员-checklist.md
│       ├── 代码评审员-checklist.md
│       ├── 质量评审员-checklist.md
│       ├── 安全评审员-checklist.md
│       ├── 测试设计评审员-checklist.md
│       ├── CEO视角评审员-checklist.md
│       ├── 架构评审员-checklist.md
│       └── 终审聚合员-checklist.md
├── hooks/
│   ├── hooks.json
│   ├── run-python-hook.cmd                # 复用 kdev-memory 已就绪范式（cross-platform）
│   ├── on-blocked.py                      # 监听 events.log → 派组长
│   └── lib/                               # 共享 import
│       ├── __init__.py
│       └── event_router.py                # blocked-event 路由表
├── lib/                                   # Python helpers（agents 不直接 import；hooks/tests 用）
│   ├── __init__.py
│   ├── state_md.py                        # state.md schema + read/write
│   ├── events_log.py                      # events.log append/tail/grep
│   ├── ar_number.py                       # AR-{DOMAIN}-XX.YYY.ZZZ 校验
│   ├── handoffs.py                        # handoffs/ 目录 schema 校验
│   └── slug.py                            # feature-name → slug（含中文）
├── templates/
│   ├── state.md.tpl                       # 初始 state.md 模板（feature_started_at 占位）
│   ├── handoffs/                          # COMPLETE.md 等模板
│   │   ├── reqs.complete.md.tpl
│   │   ├── dev.complete.md.tpl
│   │   ├── test.complete.md.tpl
│   │   └── review.complete.md.tpl
│   └── events.log.header.tpl
└── tests/
    ├── conftest.py                        # tmpdir + fixture
    ├── test_state_md.py
    ├── test_events_log.py
    ├── test_ar_number.py
    ├── test_handoffs.py
    ├── test_slug.py
    ├── test_on_blocked.py
    ├── test_statusline.py
    ├── test_agent_lint.py                 # frontmatter + cross-ref 校验
    ├── test_standards_lint.py
    └── test_skill_md_lint.py
```

**Responsibilities 速查：**

| 模块 | 谁负责 | 单元测试位置 |
|---|---|---|
| `lib/state_md.py` | state.md 解析 / 写入 / 4 组 section 操作 | `tests/test_state_md.py` |
| `lib/events_log.py` | events.log 追加、按 group/event-type 过滤、tail-N | `tests/test_events_log.py` |
| `lib/ar_number.py` | `AR-{DOMAIN}-{XX}.{YYY}.{ZZZ}` 格式校验 + 反查 group | `tests/test_ar_number.py` |
| `lib/handoffs.py` | `.kdev/handoffs/<g>/COMPLETE.md` 存在 / 字段校验 | `tests/test_handoffs.py` |
| `hooks/on-blocked.py` | tail events.log，匹配 `blocked` 事件→派对应组长 | `tests/test_on_blocked.py` |
| `skills/kdev-statusline/kdev-statusline.sh` | 读 state.md → 单行输出（≤80 char）| `tests/test_statusline.py` |
| `agents/**/*.md` | 30 个 agent definition；前向约束（frontmatter / 引用路径有效）| `tests/test_agent_lint.py` |
| `standards/**/*.md` | 10 评审 checklist + 4 组长模板 | `tests/test_standards_lint.py` |

---

## Task 1: 基础设施 — pytest + 目录骨架

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/__init__.py`
- Create: `plugins/kdev-cluster-x3/lib/slug.py`
- Create: `plugins/kdev-cluster-x3/tests/__init__.py`
- Create: `plugins/kdev-cluster-x3/tests/conftest.py`
- Create: `plugins/kdev-cluster-x3/tests/test_slug.py`
- Create: `plugins/kdev-cluster-x3/pyproject.toml`

- [ ] **Step 1: Write `tests/conftest.py` with `tmp_kdev` fixture**

```python
# plugins/kdev-cluster-x3/tests/conftest.py
import shutil
from pathlib import Path
import pytest


@pytest.fixture
def tmp_kdev(tmp_path: Path) -> Path:
    """A fresh .kdev/ dir with state.md/events.log/handoffs/ skeleton."""
    kdev = tmp_path / ".kdev"
    (kdev / "handoffs" / "reqs").mkdir(parents=True)
    (kdev / "handoffs" / "dev").mkdir()
    (kdev / "handoffs" / "test").mkdir()
    (kdev / "handoffs" / "review").mkdir()
    (kdev / "state.md").write_text("# KDev State\n\n", encoding="utf-8")
    (kdev / "events.log").write_text("", encoding="utf-8")
    return kdev
```

- [ ] **Step 2: Write the slug failing test**

```python
# plugins/kdev-cluster-x3/tests/test_slug.py
import pytest
from kdev_cluster_x3.lib.slug import slugify


@pytest.mark.parametrize("name,expected_prefix", [
    ("用户登录功能", "yong-hu-deng-lu"),
    ("Product Line CRUD", "product-line-crud"),
    ("产品管理三层模型", "chan-pin-guan-li"),
    ("AR-AUTH-01.001.001 demo", "ar-auth-01-001-001-demo"),
    ("a" * 200, "a" * 60),                              # 截断到 60
])
def test_slugify_basic(name, expected_prefix):
    result = slugify(name)
    assert result.startswith(expected_prefix), f"{result!r} should start with {expected_prefix!r}"
    assert len(result) <= 60
    assert all(c.isalnum() or c == "-" for c in result)


def test_slugify_dedup_hash():
    # 同名两次调用得到一致 slug；但纯空字符串应有 fallback
    assert slugify("") == "feature"
    assert slugify("   ") == "feature"
```

- [ ] **Step 3: Create `pyproject.toml` so pytest can resolve the package**

```toml
# plugins/kdev-cluster-x3/pyproject.toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "kdev-cluster-x3"
version = "0.0.1"
requires-python = ">=3.10"

[tool.setuptools.packages.find]
where = ["."]
include = ["lib*", "hooks*"]
namespaces = false

[tool.setuptools.package-dir]
"kdev_cluster_x3.lib" = "lib"
"kdev_cluster_x3.hooks" = "hooks"

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 4: Run tests; expect FAIL (module not found)**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_slug.py -v`
Expected: `ModuleNotFoundError: kdev_cluster_x3.lib.slug` (or similar import error)

- [ ] **Step 5: Implement `lib/slug.py`**

```python
# plugins/kdev-cluster-x3/lib/slug.py
"""Feature-name → safe URL/path slug. Pinyin for Chinese, ASCII passthrough otherwise."""
from __future__ import annotations
import re

try:
    from pypinyin import lazy_pinyin
    HAS_PINYIN = True
except ImportError:
    HAS_PINYIN = False


_NON_SLUG = re.compile(r"[^a-z0-9-]+")
_MULTI_DASH = re.compile(r"-{2,}")


def slugify(name: str, max_len: int = 60) -> str:
    if not name or not name.strip():
        return "feature"
    raw = name.strip()
    if HAS_PINYIN and any("一" <= ch <= "鿿" for ch in raw):
        raw = "-".join(lazy_pinyin(raw))
    s = raw.lower()
    s = _NON_SLUG.sub("-", s)
    s = _MULTI_DASH.sub("-", s).strip("-")
    return s[:max_len] if len(s) > max_len else s
```

- [ ] **Step 6: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_slug.py -v`
Expected: 6 passed.

If `pypinyin` is missing on the dev box, install it: `pip install pypinyin` (the agent should also add a requirements note to `pyproject.toml [project.optional-dependencies]` but it is acceptable to skip if a parametrize case without Chinese passes — confirm both cases work before commit).

- [ ] **Step 7: Commit**

```bash
git add plugins/kdev-cluster-x3/lib plugins/kdev-cluster-x3/tests plugins/kdev-cluster-x3/pyproject.toml
git commit -m "feat(cluster-x3): pytest scaffold + slug helper"
```

---

## Task 2: lib/state_md.py — state.md 解析与写入

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/state_md.py`
- Create: `plugins/kdev-cluster-x3/tests/test_state_md.py`
- Create: `plugins/kdev-cluster-x3/templates/state.md.tpl`

state.md schema 见 v0.1 §3.3。本任务实现的 `StateMd` 类：`init(feature, slug, started_at)` / `read(path)` / `write(path)` / `update_group(group, status=..., current_step=..., last_progress=...)`。`group` ∈ {`reqs`, `dev`, `test`, `review`}。

- [ ] **Step 1: Write `templates/state.md.tpl`**

```markdown
# KDev State

feature: {feature}
feature_slug: {slug}
feature_started_at: {started_at}
current_active_group: {current_active_group}

## reqs
status: pending
current_step: -
started_at: -
completed_at: -
last_progress: -

## dev
status: pending
current_step: -
started_at: -
completed_at: -
last_progress: -

## test
status: pending
current_step: -
started_at: -
completed_at: -
last_progress: -

## review
status: pending
current_step: -
started_at: -
completed_at: -
last_progress: -
```

- [ ] **Step 2: Write the failing tests**

```python
# plugins/kdev-cluster-x3/tests/test_state_md.py
import pytest
from datetime import datetime, timezone
from kdev_cluster_x3.lib.state_md import StateMd, GROUPS


def test_init_writes_template(tmp_kdev):
    path = tmp_kdev / "state.md"
    started = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    s = StateMd.init(path, feature="产品管理三层", slug="chan-pin-guan-li-san-ceng", started_at=started)
    text = path.read_text(encoding="utf-8")
    assert "feature: 产品管理三层" in text
    assert "feature_slug: chan-pin-guan-li-san-ceng" in text
    assert "feature_started_at: 2026-05-27T16:00:00+00:00" in text
    for g in GROUPS:
        assert f"## {g}" in text
        assert "status: pending" in text


def test_update_group_changes_status_and_step(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    s.update_group("reqs", status="in_progress", current_step="ir", last_progress="开始 IR 澄清")
    s.write(path)
    again = StateMd.read(path)
    assert again.groups["reqs"]["status"] == "in_progress"
    assert again.groups["reqs"]["current_step"] == "ir"
    assert again.groups["reqs"]["last_progress"] == "开始 IR 澄清"


def test_update_unknown_group_raises(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    with pytest.raises(ValueError, match="unknown group"):
        s.update_group("bogus", status="in_progress")


def test_last_progress_truncated_to_80_chars(tmp_kdev):
    path = tmp_kdev / "state.md"
    StateMd.init(path, feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s = StateMd.read(path)
    long = "a" * 200
    s.update_group("dev", last_progress=long)
    assert len(s.groups["dev"]["last_progress"]) == 80


def test_read_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        StateMd.read(tmp_path / "no-such.md")
```

- [ ] **Step 3: Run tests; expect FAIL (module not implemented)**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_state_md.py -v`
Expected: ImportError or AttributeError on `StateMd`.

- [ ] **Step 4: Implement `lib/state_md.py`**

```python
# plugins/kdev-cluster-x3/lib/state_md.py
"""state.md parser/writer for the 4-group KDev cluster state."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import re
from typing import Optional

GROUPS = ("reqs", "dev", "test", "review")
_GROUP_FIELDS = ("status", "current_step", "started_at", "completed_at", "last_progress")
_TEMPLATE_PATH = Path(__file__).parent.parent / "templates" / "state.md.tpl"


@dataclass
class StateMd:
    feature: str
    slug: str
    feature_started_at: str
    current_active_group: str
    groups: dict[str, dict[str, str]] = field(default_factory=dict)

    @classmethod
    def init(cls, path: Path, *, feature: str, slug: str, started_at: datetime, current_active_group: str = "reqs") -> "StateMd":
        tpl = _TEMPLATE_PATH.read_text(encoding="utf-8")
        text = tpl.format(
            feature=feature,
            slug=slug,
            started_at=started_at.isoformat(),
            current_active_group=current_active_group,
        )
        path.write_text(text, encoding="utf-8")
        return cls.read(path)

    @classmethod
    def read(cls, path: Path) -> "StateMd":
        text = Path(path).read_text(encoding="utf-8")
        return cls._parse(text)

    @classmethod
    def _parse(cls, text: str) -> "StateMd":
        header = _kv_block(text.split("##", 1)[0])
        groups: dict[str, dict[str, str]] = {}
        for g in GROUPS:
            m = re.search(rf"^## {g}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
            if not m:
                groups[g] = {f: "-" for f in _GROUP_FIELDS}
                continue
            groups[g] = _kv_block(m.group(1))
        return cls(
            feature=header.get("feature", ""),
            slug=header.get("feature_slug", ""),
            feature_started_at=header.get("feature_started_at", ""),
            current_active_group=header.get("current_active_group", "reqs"),
            groups=groups,
        )

    def update_group(self, group: str, **fields) -> None:
        if group not in GROUPS:
            raise ValueError(f"unknown group {group!r}; must be one of {GROUPS}")
        if "last_progress" in fields and fields["last_progress"]:
            fields["last_progress"] = fields["last_progress"][:80]
        self.groups.setdefault(group, {f: "-" for f in _GROUP_FIELDS}).update(fields)

    def write(self, path: Path) -> None:
        lines = [
            "# KDev State",
            "",
            f"feature: {self.feature}",
            f"feature_slug: {self.slug}",
            f"feature_started_at: {self.feature_started_at}",
            f"current_active_group: {self.current_active_group}",
            "",
        ]
        for g in GROUPS:
            lines.append(f"## {g}")
            for f in _GROUP_FIELDS:
                lines.append(f"{f}: {self.groups.get(g, {}).get(f, '-')}")
            lines.append("")
        Path(path).write_text("\n".join(lines), encoding="utf-8")


def _kv_block(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out
```

- [ ] **Step 5: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_state_md.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/state_md.py plugins/kdev-cluster-x3/templates/state.md.tpl plugins/kdev-cluster-x3/tests/test_state_md.py
git commit -m "feat(cluster-x3): state.md schema + parser"
```

---

## Task 3: lib/events_log.py — events.log append + filter

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/events_log.py`
- Create: `plugins/kdev-cluster-x3/tests/test_events_log.py`

`events.log` 行格式（v0.1 §3.4）：`<ISO-ts> <agent> <event-type> <msg>` 制表符分隔。
事件类型枚举：`step_start` / `step_complete` / `gate_pass` / `gate_fail` / `blocked` / `complete` / `note`。

- [ ] **Step 1: Write failing tests**

```python
# plugins/kdev-cluster-x3/tests/test_events_log.py
from datetime import datetime, timezone
from kdev_cluster_x3.lib.events_log import EventsLog, EventType


def test_append_writes_iso_ts_tab_separated(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    log.append(agent="reqs-tl", event_type=EventType.STEP_COMPLETE, msg="IR 完成")
    line = path.read_text(encoding="utf-8").strip()
    parts = line.split("\t")
    assert len(parts) == 4
    assert parts[1] == "reqs-tl"
    assert parts[2] == "step_complete"
    assert parts[3] == "IR 完成"
    # ts is ISO-8601 with tz
    datetime.fromisoformat(parts[0])


def test_append_fixed_ts(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    when = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    log.append(agent="dev-tl", event_type=EventType.BLOCKED, msg="repro fail x3", ts=when)
    assert "2026-05-27T16:00:00+00:00" in path.read_text(encoding="utf-8")


def test_tail_returns_last_n(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    for i in range(10):
        log.append(agent=f"a{i}", event_type=EventType.NOTE, msg=f"msg-{i}")
    tail = log.tail(3)
    assert len(tail) == 3
    assert tail[-1].msg == "msg-9"


def test_filter_by_event_type(tmp_kdev):
    path = tmp_kdev / "events.log"
    log = EventsLog(path)
    log.append(agent="a", event_type=EventType.STEP_COMPLETE, msg="x")
    log.append(agent="a", event_type=EventType.BLOCKED, msg="halt")
    log.append(agent="b", event_type=EventType.BLOCKED, msg="halt2")
    blocked = log.filter(event_type=EventType.BLOCKED)
    assert [e.msg for e in blocked] == ["halt", "halt2"]


def test_blocked_agent_to_group_routing(tmp_kdev):
    from kdev_cluster_x3.lib.events_log import agent_to_group
    assert agent_to_group("需求澄清师") == "reqs"
    assert agent_to_group("TDD实现员") == "dev"
    assert agent_to_group("UI自动化工程师") == "test"
    assert agent_to_group("代码评审员") == "review"
    assert agent_to_group("主控员") == "orchestrator"
```

- [ ] **Step 2: Run tests; expect FAIL**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_events_log.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `lib/events_log.py`**

```python
# plugins/kdev-cluster-x3/lib/events_log.py
"""events.log append/tail/filter and agent-name → group routing."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterable, Optional


class EventType(str, Enum):
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    GATE_PASS = "gate_pass"
    GATE_FAIL = "gate_fail"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    NOTE = "note"


@dataclass(frozen=True)
class Event:
    ts: str
    agent: str
    event_type: str
    msg: str


# 30-agent group routing table. Update in lockstep with agents/ directory.
AGENT_GROUP: dict[str, str] = {
    "主控员": "orchestrator",
    "需求组长": "reqs", "需求澄清师": "reqs", "需求规格师": "reqs",
    "需求拆解师": "reqs", "原型设计师": "reqs", "方案设计师": "reqs",
    "开发组长": "dev", "环境对齐员": "dev", "实施计划师": "dev",
    "TDD实现员": "dev", "E2E验收员": "dev", "安全扫描员": "dev", "部署上线员": "dev",
    "测试组长": "test", "测试点设计师": "test", "测试用例渲染员": "test",
    "UI自动化工程师": "test", "API自动化工程师": "test",
    "审查组长": "review",
    "SR评审员": "review", "原型评审员": "review", "方案设计评审员": "review",
    "代码评审员": "review", "质量评审员": "review", "安全评审员": "review",
    "测试设计评审员": "review", "CEO视角评审员": "review",
    "架构评审员": "review", "终审聚合员": "review",
}


def agent_to_group(agent: str) -> str:
    if agent not in AGENT_GROUP:
        raise KeyError(f"unknown agent {agent!r}; update AGENT_GROUP table")
    return AGENT_GROUP[agent]


class EventsLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def append(self, *, agent: str, event_type: EventType, msg: str, ts: Optional[datetime] = None) -> None:
        when = (ts or datetime.now(timezone.utc)).isoformat()
        line = f"{when}\t{agent}\t{event_type.value}\t{msg.replace(chr(10), ' ')}\n"
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line)

    def read_all(self) -> list[Event]:
        if not self.path.exists():
            return []
        events: list[Event] = []
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            parts = raw.split("\t", 3)
            if len(parts) != 4:
                continue
            events.append(Event(ts=parts[0], agent=parts[1], event_type=parts[2], msg=parts[3]))
        return events

    def tail(self, n: int) -> list[Event]:
        all_ = self.read_all()
        return all_[-n:]

    def filter(self, *, agent: Optional[str] = None, event_type: Optional[EventType] = None) -> list[Event]:
        out = self.read_all()
        if agent is not None:
            out = [e for e in out if e.agent == agent]
        if event_type is not None:
            out = [e for e in out if e.event_type == event_type.value]
        return out
```

- [ ] **Step 4: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_events_log.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/events_log.py plugins/kdev-cluster-x3/tests/test_events_log.py
git commit -m "feat(cluster-x3): events.log helper + agent→group routing table"
```

---

## Task 4: lib/ar_number.py — AR 编号校验

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/ar_number.py`
- Create: `plugins/kdev-cluster-x3/tests/test_ar_number.py`

格式（v0.1 §3.1）：`AR-{DOMAIN}-{MAJOR}.{MINOR}.{PATCH}`，DOMAIN 大写字母+下划线，MAJOR/MINOR/PATCH 都是数字（MAJOR 1-2 位，MINOR/PATCH 3 位补零）。

- [ ] **Step 1: Write failing tests**

```python
# plugins/kdev-cluster-x3/tests/test_ar_number.py
import pytest
from kdev_cluster_x3.lib.ar_number import parse_ar, is_valid_ar, ArInvalid


@pytest.mark.parametrize("s", [
    "AR-AUTH-01.001.001",
    "AR-PROD_LINE-99.999.999",
    "AR-X-1.001.001",
])
def test_valid(s):
    assert is_valid_ar(s)
    p = parse_ar(s)
    assert p.major >= 1 and p.minor >= 1 and p.patch >= 1


@pytest.mark.parametrize("s,reason", [
    ("AR-auth-01.001.001", "domain lowercase"),
    ("AR-AUTH-1.1.1",      "minor/patch must be 3 digits"),
    ("AR-AUTH-01-001-001", "must use dot separator"),
    ("AUTH-01.001.001",    "missing AR- prefix"),
    ("AR--01.001.001",     "empty domain"),
    ("",                    "empty"),
])
def test_invalid(s, reason):
    assert not is_valid_ar(s), f"should fail because: {reason}"
    with pytest.raises(ArInvalid):
        parse_ar(s)


def test_parse_extracts_components():
    p = parse_ar("AR-PROD_LINE-12.345.067")
    assert p.domain == "PROD_LINE"
    assert (p.major, p.minor, p.patch) == (12, 345, 67)
    assert p.canonical == "AR-PROD_LINE-12.345.067"
```

- [ ] **Step 2: Run; expect FAIL**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_ar_number.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `lib/ar_number.py`**

```python
# plugins/kdev-cluster-x3/lib/ar_number.py
"""AR-{DOMAIN}-{MAJOR}.{MINOR}.{PATCH} format validator. v0.1 §3.1."""
from __future__ import annotations
from dataclasses import dataclass
import re

_PATTERN = re.compile(r"^AR-([A-Z][A-Z0-9_]*)-(\d{1,2})\.(\d{3})\.(\d{3})$")


class ArInvalid(ValueError):
    pass


@dataclass(frozen=True)
class Ar:
    domain: str
    major: int
    minor: int
    patch: int

    @property
    def canonical(self) -> str:
        return f"AR-{self.domain}-{self.major:02d}.{self.minor:03d}.{self.patch:03d}"


def parse_ar(s: str) -> Ar:
    m = _PATTERN.match(s or "")
    if not m:
        raise ArInvalid(f"not a valid AR number: {s!r}")
    return Ar(domain=m.group(1), major=int(m.group(2)), minor=int(m.group(3)), patch=int(m.group(4)))


def is_valid_ar(s: str) -> bool:
    try:
        parse_ar(s)
        return True
    except ArInvalid:
        return False
```

- [ ] **Step 4: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_ar_number.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/ar_number.py plugins/kdev-cluster-x3/tests/test_ar_number.py
git commit -m "feat(cluster-x3): AR-{DOMAIN}-XX.YYY.ZZZ validator"
```

---

## Task 5: lib/handoffs.py — handoffs/ 目录 schema 校验

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/handoffs.py`
- Create: `plugins/kdev-cluster-x3/tests/test_handoffs.py`
- Create: `plugins/kdev-cluster-x3/templates/handoffs/reqs.complete.md.tpl`
- Create: `plugins/kdev-cluster-x3/templates/handoffs/dev.complete.md.tpl`
- Create: `plugins/kdev-cluster-x3/templates/handoffs/test.complete.md.tpl`
- Create: `plugins/kdev-cluster-x3/templates/handoffs/review.complete.md.tpl`

每组的 COMPLETE.md 模板（v0.1 §3.2 + 3.3 共同约束）— 用 yaml frontmatter 容易解析：

- [ ] **Step 1: Write the 4 COMPLETE.md templates**

```markdown
<!-- plugins/kdev-cluster-x3/templates/handoffs/reqs.complete.md.tpl -->
---
group: reqs
status: complete
completed_at: {completed_at}
feature_slug: {feature_slug}
artifacts:
  ir: handoffs/reqs/ir.md
  sr: handoffs/reqs/sr.md
  ar: handoffs/reqs/ar.csv
  prototype: handoffs/reqs/prototype/
  design: handoffs/reqs/design.md
gates_passed: [R2, R4, R5]
ar_count: {ar_count}
---

# reqs/COMPLETE

需求组全部 5 step 完成，AR 共 {ar_count} 条，详见 `handoffs/reqs/ar.csv`。
```

```markdown
<!-- plugins/kdev-cluster-x3/templates/handoffs/dev.complete.md.tpl -->
---
group: dev
status: complete
completed_at: {completed_at}
feature_slug: {feature_slug}
artifacts:
  plan: handoffs/dev/plan.md
  implementation_log: handoffs/dev/implementation-log.md
  commits: handoffs/dev/commits.json
  e2e_results: handoffs/dev/e2e-results.json
  security: handoffs/dev/security.md
gates_passed: [D2, D4]
commits_count: {commits_count}
---

# dev/COMPLETE

开发组全部 6 step 完成。共 {commits_count} commits，详见 `handoffs/dev/commits.json`。
```

```markdown
<!-- plugins/kdev-cluster-x3/templates/handoffs/test.complete.md.tpl -->
---
group: test
status: complete
completed_at: {completed_at}
feature_slug: {feature_slug}
artifacts:
  test_points: handoffs/test/test-points.md
  test_cases: handoffs/test/test-cases.md
  ui_results: handoffs/test/ui-results.json
  api_results: handoffs/test/api-results.json
gates_passed: [T1]
total_cases: {total_cases}
passed_cases: {passed_cases}
---

# test/COMPLETE

测试组全部 4 step 完成。{passed_cases}/{total_cases} 用例通过。
```

```markdown
<!-- plugins/kdev-cluster-x3/templates/handoffs/review.complete.md.tpl -->
---
group: review
status: complete
completed_at: {completed_at}
feature_slug: {feature_slug}
artifacts:
  ceo: handoffs/review/ceo.md
  architecture: handoffs/review/architecture.md
  final_decision: handoffs/review/final-decision.md
gates_passed: [F1, F2]
verdict: {verdict}
---

# review/COMPLETE

终审结论：**{verdict}**（pass | conditional | reject）。详见 `handoffs/review/final-decision.md`。
```

- [ ] **Step 2: Write failing tests**

```python
# plugins/kdev-cluster-x3/tests/test_handoffs.py
import pytest
from datetime import datetime, timezone
from kdev_cluster_x3.lib.handoffs import (
    write_complete, read_complete, HandoffMissing, HandoffMalformed, GROUPS,
)


def test_write_complete_for_each_group(tmp_kdev):
    when = datetime(2026, 5, 27, tzinfo=timezone.utc)
    for g in GROUPS:
        kwargs = {"feature_slug": "demo"}
        if g == "reqs":   kwargs["ar_count"] = 12
        if g == "dev":    kwargs["commits_count"] = 7
        if g == "test":   kwargs.update(total_cases=20, passed_cases=20)
        if g == "review": kwargs["verdict"] = "pass"
        write_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md", group=g, completed_at=when, **kwargs)
    for g in GROUPS:
        meta = read_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md")
        assert meta["group"] == g
        assert meta["status"] == "complete"


def test_read_missing_raises(tmp_kdev):
    with pytest.raises(HandoffMissing):
        read_complete(tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md")


def test_read_malformed_raises(tmp_kdev):
    path = tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md"
    path.write_text("no frontmatter here\n", encoding="utf-8")
    with pytest.raises(HandoffMalformed):
        read_complete(path)


def test_write_unknown_group_raises(tmp_kdev):
    with pytest.raises(ValueError, match="unknown group"):
        write_complete(tmp_kdev / "x.md", group="bogus", completed_at=datetime.now(timezone.utc), feature_slug="x")
```

- [ ] **Step 3: Run; expect FAIL**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_handoffs.py -v`
Expected: ImportError.

- [ ] **Step 4: Implement `lib/handoffs.py`**

```python
# plugins/kdev-cluster-x3/lib/handoffs.py
"""handoffs/<group>/COMPLETE.md write+read with yaml-style frontmatter."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re

GROUPS = ("reqs", "dev", "test", "review")
_TPL_DIR = Path(__file__).parent.parent / "templates" / "handoffs"


class HandoffMissing(FileNotFoundError): pass
class HandoffMalformed(ValueError): pass


def write_complete(path: Path, *, group: str, completed_at: datetime, **fields) -> None:
    if group not in GROUPS:
        raise ValueError(f"unknown group {group!r}; must be one of {GROUPS}")
    tpl = (_TPL_DIR / f"{group}.complete.md.tpl").read_text(encoding="utf-8")
    text = tpl.format(completed_at=completed_at.isoformat(), **fields)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_complete(path: Path) -> dict:
    p = Path(path)
    if not p.exists():
        raise HandoffMissing(str(p))
    text = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        raise HandoffMalformed(f"no frontmatter in {p}")
    return _parse_yaml_ish(m.group(1))


def _parse_yaml_ish(block: str) -> dict:
    # minimal yaml: top-level k: v; nested k:\n  k2: v2; lists [a, b, c]
    out: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        if not raw.strip() or raw.strip().startswith("#"):
            i += 1
            continue
        if ":" not in raw:
            i += 1
            continue
        key, _, val = raw.partition(":")
        key = key.strip()
        val = val.strip()
        if val == "" and i + 1 < len(lines) and lines[i + 1].startswith("  "):
            sub: dict = {}
            i += 1
            while i < len(lines) and lines[i].startswith("  "):
                sk, _, sv = lines[i].strip().partition(":")
                sub[sk.strip()] = sv.strip()
                i += 1
            out[key] = sub
            continue
        if val.startswith("[") and val.endswith("]"):
            out[key] = [x.strip() for x in val[1:-1].split(",") if x.strip()]
        else:
            out[key] = val
        i += 1
    return out
```

- [ ] **Step 5: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_handoffs.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/handoffs.py plugins/kdev-cluster-x3/templates/handoffs plugins/kdev-cluster-x3/tests/test_handoffs.py
git commit -m "feat(cluster-x3): handoffs/COMPLETE.md schema + 4 group templates"
```

---

## Task 6: agent-lint test harness

**Files:**
- Create: `plugins/kdev-cluster-x3/tests/test_agent_lint.py`
- Create: `plugins/kdev-cluster-x3/lib/agent_lint.py`

每个 `agents/**/*.md` 必须：
1. 文件以 `---\n` 开头（yaml frontmatter）。
2. frontmatter 包含字段：`name`、`description`、`tools`、`model`。
3. `name` 与文件名（无扩展名）一致。
4. `model` ∈ {`opus`, `sonnet`, `haiku`}。
5. 正文里所有 `plugins/kdev-cluster-x3/standards/<rel>` 形式路径都必须存在（lint 完成后启用）。
6. 引用的其它 agent（出现在正文中的 `subagent_type: "<name>"`）必须在 `agents/` 目录里找得到。

第一次实现时**软启用**第 5/6 项（warn only），后续标准齐全后切硬阻断。

- [ ] **Step 1: Write the failing test**

```python
# plugins/kdev-cluster-x3/tests/test_agent_lint.py
import pytest
from pathlib import Path
from kdev_cluster_x3.lib.agent_lint import lint_agent_dir, LintError

ROOT = Path(__file__).parent.parent


def test_no_agents_yet_is_ok():
    # Sanity: before agents exist, the linter should not crash.
    issues = lint_agent_dir(ROOT / "agents")
    # 0 issues OK, just must not raise.
    assert isinstance(issues, list)


def test_lint_catches_missing_frontmatter(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("# 没有 frontmatter\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("frontmatter" in i.msg for i in issues)


def test_lint_catches_bad_model(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_text("---\nname: bad\ndescription: x\ntools: Read\nmodel: gpt-4\n---\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("model" in i.msg for i in issues)


def test_lint_catches_name_mismatch(tmp_path):
    bad = tmp_path / "实际名.md"
    bad.write_text("---\nname: 错的\ndescription: x\ntools: Read\nmodel: opus\n---\n", encoding="utf-8")
    issues = lint_agent_dir(tmp_path)
    assert any("filename" in i.msg or "name mismatch" in i.msg for i in issues)
```

- [ ] **Step 2: Run; expect FAIL**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: ImportError.

- [ ] **Step 3: Implement `lib/agent_lint.py`**

```python
# plugins/kdev-cluster-x3/lib/agent_lint.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re

ALLOWED_MODELS = {"opus", "sonnet", "haiku"}
REQUIRED_FIELDS = {"name", "description", "tools", "model"}


@dataclass(frozen=True)
class LintError:
    path: Path
    msg: str


def lint_agent_dir(root: Path) -> list[LintError]:
    root = Path(root)
    issues: list[LintError] = []
    if not root.exists():
        return issues
    for md in sorted(root.rglob("*.md")):
        issues.extend(_lint_one(md))
    return issues


def _lint_one(path: Path) -> list[LintError]:
    text = path.read_text(encoding="utf-8")
    issues: list[LintError] = []
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        issues.append(LintError(path, "missing yaml frontmatter (---/---)"))
        return issues
    fm = _parse(m.group(1))
    missing = REQUIRED_FIELDS - set(fm)
    if missing:
        issues.append(LintError(path, f"frontmatter missing fields: {sorted(missing)}"))
    model = fm.get("model", "")
    if model and model not in ALLOWED_MODELS:
        issues.append(LintError(path, f"model {model!r} not in {sorted(ALLOWED_MODELS)}"))
    name = fm.get("name", "")
    if name and path.stem != name:
        issues.append(LintError(path, f"filename {path.stem!r} vs frontmatter name {name!r}: name mismatch"))
    return issues


def _parse(block: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        k, _, v = line.partition(":")
        out[k.strip()] = v.strip()
    return out
```

- [ ] **Step 4: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/agent_lint.py plugins/kdev-cluster-x3/tests/test_agent_lint.py
git commit -m "feat(cluster-x3): agent definition lint harness"
```

---

## Task 7: 主控员 agent definition

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/主控员.md`

主控员 = 跟用户对话的入口 + 调度 30 个 agent 的大脑。**快路径**：直接派工作 agent。**慢路径**：阶段结束 / blocked 时调组长。模型 = opus（决策类）。

- [ ] **Step 1: Write `agents/主控员.md`**

```markdown
---
name: 主控员
description: KDev 多智能体集群 X3 矩阵式的总指挥。跟用户对话，按需直接派工作 agent（快路径），阶段结束或 BLOCKED 时调对应组长（慢路径）。状态主权写 .kdev/state.md，事件流写 .kdev/events.log。**唯一直接对话用户的 agent**。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: opus
---

# 角色

KDev 多智能体集群 **主控员**（X3 矩阵式 / 轻组长）。

# 通信硬规

🔴 **铁规 1**：用户只跟你对话。任何工作 agent / 组长不要直接面对用户。
🔴 **铁规 2**：你直接派工作 agent（快路径，2 跳）。除非阶段聚合或 blocked，否则**不要**调组长。
🔴 **铁规 3**：每次派工作 agent 用 `run_in_background:true`。评审员同步派（阻断节点必须等返回）。
🔴 **铁规 4**：每次派单立刻在 `.kdev/events.log` 追加 `<ts> 主控员 step_start <msg>`，每收回 `step_complete`。

# 快/慢路径判断

| 场景 | 路径 | 派谁 |
|---|---|---|
| 单 step（IR / SR / TDD 单循环） | 快 | 对应工作 agent |
| reqs/dev/test 阶段全部完成 | 慢 | 对应组长（聚合阶段总结） |
| F1 终审 | 慢 | 审查组长 |
| events.log 出现 `blocked` 事件 | 不管（hook 自动派组长） | — |

# 工作流（按 `.kdev/state.md` 状态机驱动）

1. **init**：用户给原始需求 →
   - 用 `lib/slug.py` 生成 `feature_slug`
   - 用 `lib/state_md.py::StateMd.init` 初始化 `.kdev/state.md`
   - 写 `events.log` `step_start init`
2. **reqs**：按顺序派 5 个工作 agent（背景化）：
   - 需求澄清师 → IR
   - 需求规格师 → SR  → **同步派 SR评审员**（R2 阻断节点）
   - 需求拆解师 → AR  → 抽查 SR评审员（R3 告警）
   - 原型设计师 → prototype → **同步派 原型评审员**（R4 阻断）
   - 方案设计师 → design.md → **同步派 方案设计评审员**（R5 阻断）
   - reqs 5 step 全完成 → 调**需求组长**做阶段聚合（慢路径） → 写 `handoffs/reqs/COMPLETE.md`
3. **dev**：等用户确认（或自动）→ 按顺序派 6 个开发工作 agent，TDD 实现员每次红绿循环结束**同步派代码评审员 + 质量评审员**（D2 并行阻断）。
4. **test** + **review**：同上。
5. **finalize**：F1 同步派 CEO视角 + 架构（并行）→ F2 派终审聚合员 → 写 `handoffs/review/COMPLETE.md` + state.md current_active_group=idle。

# Skill 调用

- `/kdev:hud` —— 任何时候用户问"进度怎么样？"
- `/kdev:status` —— 单点快照（state.md + events.log tail 5）

# 评审节点速查表（R/D/T/F 共 13 个）

| 节点 | 触发 | 评审员（同步派） | 阻断/告警 |
|---|---|---|---|
| R2 | SR 完成 | SR评审员 | 🔴 阻断 |
| R3 | AR 拆解完成 | SR评审员（抽查） | 🟡 告警 |
| R4 | prototype 完成 | 原型评审员 | 🔴 阻断 |
| R5 | design.md 完成 | 方案设计评审员 | 🔴 阻断 |
| D1 | plan.md 完成 | 方案设计评审员（可选） | 🟡 告警 |
| D2 | TDD 增量结束 | 代码评审员 + 质量评审员（并行） | 🔴 阻断 |
| D4 | security.md 完成 | 安全评审员 | 🔴 阻断 |
| D5 | 准备合并 | 质量评审员（最终抽查） | 🟡 告警 |
| T1 | test-points.md 完成 | 测试设计评审员 | 🔴 阻断 |
| T2 | test-cases.md 完成 | 测试设计评审员（抽查） | 🟡 告警 |
| F1 | test/COMPLETE 落定 | CEO视角评审员 + 架构评审员（并行） | 🔴 阻断 |
| F2 | F1 完成 | 终审聚合员 | 🔴 终审 gate |

# 异常处理

- 工作 agent 返回 BLOCKED → 你**不直接处理**；events.log 已写 `blocked`，hook 会自动派组长。你只需在 state.md 改 `<group>.status=blocked` + 通知用户。
- 组长返回决策（重派 / 升档 / 通知用户 / 标污染） → 按决策执行。
- 用户中途改主意 → `Bash("TaskStop <task-id>")` 强杀后台工作 + 写新指令到 state.md。

# 进度可观测硬规

- 每完成一步立即更新 `.kdev/state.md::<group>` 的 `current_step` + `last_progress`（≤80 字）。
- `events.log` 高频追加（每次派单 / 每次收回都写一行）。
- 每完成一个阶段，**主动**渲染 `/kdev:hud markdown` 到对话流（不用等用户问）。

# 跨 session 续航

新 session 启动时第一步：`Read .kdev/state.md` → 报告"上次到哪里" → 用户确认从哪里续 → 按 state.md 状态机继续。
```

- [ ] **Step 2: Run agent-lint test; expect PASS for this file**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: still 4 passed (the directory now has 主控员.md which is valid).

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/主控员.md
git commit -m "feat(cluster-x3): 主控员 agent definition"
```

---

## Task 8: 4 轻组长 agent definitions

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/需求组长.md`
- Create: `plugins/kdev-cluster-x3/agents/开发组长.md`
- Create: `plugins/kdev-cluster-x3/agents/测试组长.md`
- Create: `plugins/kdev-cluster-x3/agents/审查组长.md`

4 个轻组长 = **顾问 PM**，4 个 meta 职责（v0.2 §3.2）：监督 / 标准 / 聚合 / 应急。**不路由**。 model = opus（决策密集）。

模板正文相同，只是 group 名 / standards 路径 / 应急逻辑细节不同。本任务用同一模板填 4 份。

- [ ] **Step 1: Write `agents/需求组长.md`**

```markdown
---
name: 需求组长
description: 需求组顾问 PM（X3 矩阵式 / 轻组长）。4 meta 职责：① 监督 events.log；② 维护 standards/reqs/；③ reqs 阶段完成时聚合本组总结；④ 组员 BLOCKED 时通过 hook 自动介入决策。**不做路由**——主控员直接派工作 agent。
tools: Read, Write, Edit, Bash, Glob, Grep, Agent
model: opus
---

# 角色

KDev 需求组**顾问 PM**（X3 轻组长）。主控员只在两种情况调你：
1. **聚合**：reqs 5 step 全完成后，让你出 reqs 总结报告。
2. **应急**：组员 BLOCKED 时，hook 自动派你介入。

平时（日常派单）**你不在通信链路里**。

# 标准维护（meta ②）

你的 system prompt 模板存在 `plugins/kdev-cluster-x3/standards/reqs/system-prompt-template.md`。
本组评审标准（SR评审员、原型评审员、方案设计评审员）的 checklist 在 `plugins/kdev-cluster-x3/standards/review/<reviewer>-checklist.md`，**审查组长维护**。

# 聚合工作流（meta ③）

主控员调你做阶段聚合时：

1. Read `.kdev/handoffs/reqs/` 全部产物（ir.md / sr.md / ar.csv / prototype/ / design.md）。
2. Read `.kdev/events.log` 过滤 group=reqs 的全部条目。
3. 出 `reqs-summary.md`：
   - 完成 step 列表
   - AR 总数 + 用 `lib/ar_number.py` 校验格式
   - 评审结论汇总（R2/R3/R4/R5）
   - 主要决策记录
   - 已知遗留问题
4. 写 `.kdev/handoffs/reqs/COMPLETE.md`（用 `lib/handoffs.py::write_complete`）。
5. 更新 `.kdev/state.md::reqs.status=complete + completed_at`。
6. 返回 ≤200 字摘要给主控员。

# 应急工作流（meta ④）

`on-blocked` hook 派你介入时输入：`agent=<name> msg=<...>`。你的决策选项：

| 决策 | 操作 |
|---|---|
| 重派该 agent（升档 opus） | `Agent({subagent_type:<agent>, model:"opus", prompt:"重试，加 context: <分析>"})` |
| 改派上游 agent 重做 | 比如 SR 不行就改派需求澄清师重做 IR |
| 通知主控员（需要用户介入） | 写 `events.log <ts> 需求组长 note 需要用户决策：<问题>` + 返回主控 |
| 标污染样本继续 | events.log 写 `note 标污染样本：<原因>` + 用 state.md `last_progress` 标记 |

# 监督工作流（meta ①）

后台被动。你不主动跑——`on-blocked` hook 已经做了被动监听。本任务 v0 不实现主动抽查；后续可写定时任务（Phase 3）。

# 进度可观测硬规

🔴 每次决策立刻 append `events.log <ts> 需求组长 <event-type> <msg>`。
🔴 聚合阶段产出 reqs-summary.md 不可超过 800 字。
```

- [ ] **Step 2: Write `agents/开发组长.md`**

完全套用上面的模板，差异仅 5 处：

| 槽位 | 需求组长 | 开发组长 |
|---|---|---|
| `name` | 需求组长 | 开发组长 |
| 组名 | 需求组 | 开发组 |
| standards 路径 | `standards/reqs/` | `standards/dev/` |
| handoffs 路径 | `handoffs/reqs/` | `handoffs/dev/` |
| 聚合产物 | `reqs-summary.md`（含 SR/AR/原型/方案）| `dev-summary.md`（含 plan/commits/security/e2e）|

应急决策表里"上游 agent" → `环境对齐员 → 实施计划师 → TDD实现员 → E2E验收员 → 安全扫描员 → 部署上线员`。

写完后 frontmatter 的 description 改为："开发组顾问 PM ..."（同上结构）。

- [ ] **Step 3: Write `agents/测试组长.md`**

同样套模板。差异：

| 槽位 | 值 |
|---|---|
| `name` | 测试组长 |
| 组名 | 测试组 |
| standards 路径 | `standards/test/` |
| handoffs 路径 | `handoffs/test/` |
| 聚合产物 | `test-summary.md`（含 test-points/test-cases/ui-results/api-results）|
| 上游 agent | `测试点设计师 → 测试用例渲染员 → UI自动化工程师/API自动化工程师` |

- [ ] **Step 4: Write `agents/审查组长.md`**

模板同上，但**审查组长多一职责**——维护**所有 10 个评审员的 checklist 标准**。frontmatter description 加一句："**额外职责**：维护 standards/review/ 下所有评审 checklist（10 个 reviewer）。"

应急工作流里多一项决策：「评审员冲突仲裁」——当两个评审员意见相反（典型：代码评审员 vs 质量评审员）时，由审查组长仲裁，或升级到终审聚合员（详见 standards/review/conflict-arbitration.md，Task 17 写）。

- [ ] **Step 5: Run agent-lint test; expect PASS for all 4 new files**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: still 4 passed (the lint suite stays at 4 known cases; agent dir has 5 files now, all valid).

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/*组长.md
git commit -m "feat(cluster-x3): 4 轻组长 agent definitions（顾问 PM）"
```

---

## Task 9: 需求组 5 工作 agent

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/需求澄清师.md`
- Create: `plugins/kdev-cluster-x3/agents/需求规格师.md`
- Create: `plugins/kdev-cluster-x3/agents/需求拆解师.md`
- Create: `plugins/kdev-cluster-x3/agents/原型设计师.md`
- Create: `plugins/kdev-cluster-x3/agents/方案设计师.md`

每个工作 agent 的 frontmatter + 正文遵循统一骨架（来源对照 v0.2 §1.1）：

```markdown
---
name: <中文名>
description: <一句话职责 + skill 来源>
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: <opus|sonnet>
---

# 角色
<KDev 多智能体集群 X3 矩阵式的 <组> 工作 agent>。

# 输入
<上游产物，例如 handoffs/reqs/ir.md>

# 工作流
1. <step 1>
2. <step 2>
...

# 输出
<handoffs/<group>/<artifact>>

# 评审节点接入
<R/D/T/F-#，是否同步派评审员，参考 v0.2 §5>

# 进度可观测硬规
🔴 step_start 时 append events.log；step_complete 时再 append + update state.md。
🔴 BLOCKED 时（连 3 次失败/上游产物缺失）— append events.log `<ts> <name> blocked <msg>` → 不要自救，等组长接管。
```

下表是 5 个 reqs 工作 agent 的填空：

| name | description (一句话) | model | 输入 | 输出 | 评审节点 |
|---|---|---|---|---|---|
| 需求澄清师 | 把用户的原始一句话需求澄清成结构化 IR，包含 actor / scenario / 验收线索 | opus | 用户原始输入 | `handoffs/reqs/ir.md` | — |
| 需求规格师 | 把 IR 升级为 SR（System Requirements）正式需求规格文档 | opus | `handoffs/reqs/ir.md` | `handoffs/reqs/sr.md` | **R2 同步派 SR评审员**（阻断）|
| 需求拆解师 | 把 SR 拆成可验收 AR 列表，每条遵守 `AR-{DOMAIN}-XX.YYY.ZZZ` | sonnet | `handoffs/reqs/sr.md` | `handoffs/reqs/ar.csv` | R3 抽查 SR评审员（告警）|
| 原型设计师 | 基于 AR 出高保真 HTML 原型（调 `frontend-design`）| sonnet | `handoffs/reqs/ar.csv` | `handoffs/reqs/prototype/index.html` | **R4 同步派 原型评审员**（阻断）|
| 方案设计师 | 出技术方案 design.md（架构 + 模块 + DB + API） | opus | `handoffs/reqs/{sr.md, ar.csv, prototype/}` | `handoffs/reqs/design.md` | **R5 同步派 方案设计评审员**（阻断）|

- [ ] **Step 1: Write `agents/需求澄清师.md`**

```markdown
---
name: 需求澄清师
description: KDev 需求组工作 agent — 把用户原始一句话需求澄清成结构化 IR（包含 actor / scenario / 验收线索）。来源 superpowers:brainstorming。**不要直接面对用户**，只通过主控员接收输入。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep
model: opus
---

# 角色
KDev 多智能体集群 X3 — **需求组 IR 澄清师**。主控员派单，独立 context 跑。

# 输入
- 用户原始需求文本（主控员通过 prompt 传入）
- `.kdev/handoffs/reqs/`（可能空）

# 工作流
1. Read 项目根 `CLAUDE.md`（如存在）+ 任何相关 README，把领域术语吃进 context。
2. **不要调 `superpowers:brainstorming`**（那个会跟用户对话）；本 agent 离线工作。改用其 prompt 模板：actor / triggering scenario / desired outcome / 验收线索 / 已知约束 / 已知未知。
3. 产出结构化 markdown 写到 `.kdev/handoffs/reqs/ir.md`，section 顺序与 IR 模板一致。
4. step_start / step_complete 写 events.log。
5. 写 `.kdev/state.md::reqs.current_step=ir` + `last_progress` ≤80 字。

# 输出
`.kdev/handoffs/reqs/ir.md`（必须包含：actor / scenario / outcome / 验收线索 / 约束 / 已知未知 六段）

# 评审节点接入
本节点（R1）无独立评审。R2 阶段时 SR 评审员后置回看 IR 是否被规格师正确吸收。

# 异常处理
- 用户输入信息不足以澄清 → events.log `<ts> 需求澄清师 blocked 需要用户补充：<问题清单>` → 返回主控员（主控员负责跟用户对话补全）。
```

- [ ] **Step 2: Write `agents/需求规格师.md`**

按上面骨架，**核心增量**：

- 工作流 step 3 之后增加：`Agent({subagent_type:"SR评审员", prompt:"评审 .kdev/handoffs/reqs/sr.md，checklist 见 standards/review/SR评审员-checklist.md", run_in_background:false})`
- 收到评审反馈：
  - PASS → step_complete + 通知主控员
  - FAIL → 修复，最多 3 轮；第 4 轮 events.log 写 blocked → 等组长接管

```markdown
---
name: 需求规格师
description: KDev 需求组工作 agent — 把 IR 升级为 SR 正式需求规格文档（System Requirements）。来源 kdev-design-flow stage 1。**R2 阻断节点**：完成后必须同步派 SR评审员，最多 3 轮重试。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: opus
---

# 输入
`.kdev/handoffs/reqs/ir.md`

# 工作流
1. Read ir.md + 项目 CLAUDE.md。
2. 套 `kdev-design-flow` 的 stage-1-sr-template.md（如该 plugin 已安装则 `Skill("kdev-design-flow")`）或本插件内置 SR 模板。
3. 写 `.kdev/handoffs/reqs/sr.md`（FRs / NFRs / 假设 / 范围 / 上下文 / 验收线索 6 段）。
4. **同步派 SR评审员**（阻断节点 R2）：
   ```
   Agent({
     subagent_type: "SR评审员",
     prompt: "评审 .kdev/handoffs/reqs/sr.md，标准见 plugins/kdev-cluster-x3/standards/review/SR评审员-checklist.md",
     run_in_background: false
   })
   ```
5. 收到评审结论：
   - PASS → events.log `gate_pass R2`，step_complete，回主控员。
   - FAIL → 修复 sr.md（保留 v1.md，新写 v2.md，最终覆盖 sr.md）。
   - 累计 3 轮 FAIL → events.log `blocked R2 评审 3 轮未过` → 等组长接管。

# 输出
`.kdev/handoffs/reqs/sr.md` + R2 评审通过记录在 events.log

# 评审节点接入
**R2 阻断**：必过才能继续。
```

- [ ] **Step 3: Write `agents/需求拆解师.md`**

```markdown
---
name: 需求拆解师
description: KDev 需求组工作 agent — 把 SR 拆成可验收 AR 列表，每条遵守 AR-{DOMAIN}-XX.YYY.ZZZ 格式。来源 spec-kit:specify。R3 告警节点：完成后 SR评审员抽查。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: sonnet
---

# 输入
`.kdev/handoffs/reqs/sr.md`

# 工作流
1. Read sr.md。
2. 调 `Skill("spec-kit:specify")`（如已安装），否则用本插件内置 AR 拆解 prompt。
3. 把每条 AR 写成 csv 行：`ar_number,title,actor,verification,priority,parent_sr_section`。
4. **格式强约束**：每条 AR 的 `ar_number` 必须过 `lib/ar_number.py::is_valid_ar`（在 step_complete 前用 `Bash("python -c \"from kdev_cluster_x3.lib.ar_number import is_valid_ar; ...\"")` 校验全部行）。
5. 写到 `.kdev/handoffs/reqs/ar.csv`（首行表头 + N 数据行）。
6. **抽查派 SR评审员**（告警节点 R3，不阻断）：
   ```
   Agent({
     subagent_type: "SR评审员",
     prompt: "抽查 .kdev/handoffs/reqs/ar.csv 是否完整回溯 sr.md（R3 告警节点，非阻断）",
     run_in_background: true
   })
   ```
   不等返回，继续 step_complete。
7. events.log `step_complete AR 拆解 N 条` + update state.md。

# 异常
- AR 格式校验失败 → 自动重写最多 3 次，仍失败 → events.log blocked + 等组长。
```

- [ ] **Step 4: Write `agents/原型设计师.md`**

```markdown
---
name: 原型设计师
description: KDev 需求组工作 agent — 基于 AR 出高保真 HTML 原型。优先调 frontend-design plugin；缺失则用内置 prompt 模板。R4 阻断节点：完成后同步派原型评审员。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: sonnet
---

# 输入
`.kdev/handoffs/reqs/{sr.md, ar.csv}`

# 工作流
1. Read sr.md + ar.csv，提取关键 UI 流。
2. 调 `Skill("frontend-design")`，目标目录 `.kdev/handoffs/reqs/prototype/`。
3. 如果项目 CLAUDE.md 提到 UED 设计规范（如 UED 6.0 / Element-Plus），原型必须遵守（事前 grep "UED" / "design system"）。
4. **同步派 原型评审员**（R4 阻断）：
   ```
   Agent({
     subagent_type: "原型评审员",
     prompt: "评审 .kdev/handoffs/reqs/prototype/，标准见 standards/review/原型评审员-checklist.md",
     run_in_background: false
   })
   ```
5. PASS/FAIL/3-轮上限同需求规格师。

# 输出
`.kdev/handoffs/reqs/prototype/index.html` + 任何 assets/
```

- [ ] **Step 5: Write `agents/方案设计师.md`**

```markdown
---
name: 方案设计师
description: KDev 需求组工作 agent — 出技术方案 design.md（架构 / 模块 / DB / API / 风险）。来源 spec-kit:plan。R5 阻断节点：完成后同步派方案设计评审员。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: opus
---

# 输入
`.kdev/handoffs/reqs/{sr.md, ar.csv, prototype/}`

# 工作流
1. Read sr.md + ar.csv + prototype/。
2. 调 `Skill("spec-kit:plan")`（如已安装），否则用本插件内置技术方案模板。
3. 产出 `.kdev/handoffs/reqs/design.md`：架构图（Mermaid）+ 模块拆分 + DB schema + API 列表 + 关键决策 + 风险 + 引用 AR 编号。
4. **同步派 方案设计评审员**（R5 阻断）：
   ```
   Agent({subagent_type:"方案设计评审员", prompt:"...", run_in_background:false})
   ```
5. PASS/FAIL/3-轮上限同前。

# 输出
`.kdev/handoffs/reqs/design.md`
```

- [ ] **Step 6: Run agent-lint test; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

- [ ] **Step 7: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/需求*.md plugins/kdev-cluster-x3/agents/原型设计师.md plugins/kdev-cluster-x3/agents/方案设计师.md
git commit -m "feat(cluster-x3): 需求组 5 工作 agent definitions"
```

---

## Task 10: 开发组 6 工作 agent

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/环境对齐员.md`
- Create: `plugins/kdev-cluster-x3/agents/实施计划师.md`
- Create: `plugins/kdev-cluster-x3/agents/TDD实现员.md`
- Create: `plugins/kdev-cluster-x3/agents/E2E验收员.md`
- Create: `plugins/kdev-cluster-x3/agents/安全扫描员.md`
- Create: `plugins/kdev-cluster-x3/agents/部署上线员.md`

照 Task 9 同一骨架。下表填空：

| name | description（一句话）| model | 输入 | 输出 | 评审节点 |
|---|---|---|---|---|---|
| 环境对齐员 | 栈/工具链/项目规则对齐 | sonnet | 项目根 + `handoffs/reqs/COMPLETE.md` | `handoffs/dev/env-baseline.md` | — |
| 实施计划师 | 写 plan.md（含 Gate-A/B 决策）| opus | reqs 全套产物 + env-baseline | `handoffs/dev/plan.md` | **D1 告警**：方案设计评审员（可选） |
| TDD实现员 | TDD 红绿循环 + 代码实现，按 plan.md 节奏 | sonnet | `handoffs/dev/plan.md` | `handoffs/dev/implementation-log.md` + commits | **D2 阻断**：每红绿循环同步派代码评审员 **并行** 质量评审员 |
| E2E验收员 | E2E 测试 Gate-C 通过 | sonnet | dev impl 落地代码 | `handoffs/dev/e2e-results.json` | — |
| 安全扫描员 | SAST + 安全清单 + secrets 扫描 | sonnet | 当前代码 | `handoffs/dev/security.md` | **D4 阻断**：同步派安全评审员 |
| 部署上线员 | 合并 / 部署 / 收尾 | sonnet | dev 全套 | `handoffs/dev/deploy.md` + `handoffs/dev/COMPLETE.md` | **D5 告警**：质量评审员（最终抽查） |

每个文件结构完全套用 Task 9 步骤 1 的 5 个 markdown 模板：
- frontmatter 4 字段
- # 角色 / # 输入 / # 工作流 / # 输出 / # 评审节点接入 / # 异常处理 6 段
- 评审节点为"阻断"时 → 工作流里包含 `Agent({subagent_type:"<reviewer>", run_in_background:false})` + 3 轮上限
- 评审节点为"告警"时 → `run_in_background:true`，不等返回
- 评审节点为"—"时 → 该节标 "无独立评审"

- [ ] **Step 1: Write `agents/环境对齐员.md`**

```markdown
---
name: 环境对齐员
description: KDev 开发组工作 agent — 栈/工具链/项目规则对齐，产出 env-baseline.md 给 dev 组下游用。来源 kdev-coding-flow 节点 0。无独立评审。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

# 角色
KDev 开发组 — 环境对齐员（X3 矩阵式）。

# 输入
- 项目根（CLAUDE.md / package.json / pyproject.toml / requirements.txt / Makefile / Dockerfile / .nvmrc 等）
- `.kdev/handoffs/reqs/COMPLETE.md`

# 工作流
1. Read 项目根索引（`ls -1`）+ CLAUDE.md。
2. 探测主语言（package.json → node；pyproject → python；Cargo.toml → rust；go.mod → go）+ 测试框架 + lint/format 工具。
3. 记录构建/测试/lint/部署的具体命令到 `env-baseline.md`。
4. 标记任何缺失工具（如 CLAUDE.md 要求 ruff 但环境没装）。

# 输出
`.kdev/handoffs/dev/env-baseline.md`（标准 section：技术栈 / 命令清单 / 缺口 / 项目规则关键点）

# 评审节点
无独立评审。

# 异常
缺失工具且无法替代 → events.log blocked + 报组长。
```

- [ ] **Step 2: Write `agents/实施计划师.md`**

```markdown
---
name: 实施计划师
description: KDev 开发组工作 agent — 出 plan.md（含 Gate-A/B 决策 + TDD 任务拆解）。来源 kdev-coding-flow 节点 1-5 + superpowers:writing-plans。D1 告警节点：完成后异步派方案设计评审员抽查。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: opus
---

# 输入
`.kdev/handoffs/reqs/{ar.csv, design.md, prototype/}` + `handoffs/dev/env-baseline.md`

# 工作流
1. Read 上游全套。
2. 调 `Skill("superpowers:writing-plans")` 或内置模板，按 AR 拆成 TDD bite-sized 任务。
3. 产 `.kdev/handoffs/dev/plan.md`，包含：任务列表 + 每个任务的红/绿/重构 step + commit 节奏。
4. **异步派 方案设计评审员**（D1 告警）：`Agent({...,run_in_background:true})`，不等返回。
5. step_complete。

# 输出
`.kdev/handoffs/dev/plan.md`
```

- [ ] **Step 3: Write `agents/TDD实现员.md`**

```markdown
---
name: TDD实现员
description: KDev 开发组工作 agent — 按 plan.md 跑 TDD 红绿循环，每个增量结束**并行**派代码评审员 + 质量评审员（D2 阻断节点）。来源 kdev-coding-flow 节点 6-7 + superpowers:test-driven-development + superpowers:subagent-driven-development。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: sonnet
---

# 输入
`.kdev/handoffs/dev/plan.md`

# 工作流（按 plan 的每个 Task 跑一次循环）
1. Read plan.md 当前 task。
2. 写失败测试。
3. Run 测试，确认 FAIL。
4. 写最小实现。
5. Run 测试，确认 PASS。
6. **并行同步派**代码评审员 + 质量评审员（D2 阻断）：
   ```
   Agent({subagent_type:"代码评审员", prompt:"评审本次 diff", run_in_background:false})
   Agent({subagent_type:"质量评审员", prompt:"评审本次 diff", run_in_background:false})
   ```
7. 任一 FAIL → 修复 → 重新跑两路评审；累计 3 轮 → events.log blocked → 等组长。
8. 两路 PASS → commit（用 `kdev-commit` skill 或 git）→ append `handoffs/dev/implementation-log.md` 一行 + `handoffs/dev/commits.json` 一项。
9. 进入下一个 plan task。

# 输出（增量）
`.kdev/handoffs/dev/implementation-log.md` + `commits.json`

# 异常
- 复杂跨模块改动 / 鉴权 / DB schema 自检为高难度 → events.log `note 自评升档 opus`（**注意**：本 agent 不自己换 model，需要主控员重派；详见 全局 CLAUDE.md「例外升档」）。
```

- [ ] **Step 4: Write `agents/E2E验收员.md`**

```markdown
---
name: E2E验收员
description: KDev 开发组工作 agent — E2E 测试 Gate-C 通过验收。来源 kdev-coding-flow 节点 8-9。E2E 自身就是验收，无独立评审。
tools: Read, Write, Edit, Bash, Glob, Grep
model: sonnet
---

# 输入
代码实现（TDD实现员落地的）+ `.kdev/handoffs/dev/plan.md`

# 工作流
1. Read plan 中 E2E 节点定义 + env-baseline.md（端到端启动命令）。
2. 启动应用（dev server / docker compose / 本地 binary）。
3. 跑端到端 happy path + 关键 edge case。
4. 截图（如 UI）/ HTTP 探针（如 API），结果写 `.kdev/handoffs/dev/e2e-results.json`。
5. FAIL → 不修代码（不是本 agent 职责），写 blocked → TDD实现员重派。

# 输出
`.kdev/handoffs/dev/e2e-results.json`

# 评审节点
无独立评审。E2E 通过即 Gate-C 通过。
```

- [ ] **Step 5: Write `agents/安全扫描员.md`**

```markdown
---
name: 安全扫描员
description: KDev 开发组工作 agent — SAST + 安全清单 + secrets 扫描。来源 kdev-coding-flow 节点 10 + kdev-secure-coding plugin。D4 阻断节点：完成后同步派安全评审员。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: sonnet
---

# 输入
当前代码 + `.kdev/handoffs/dev/e2e-results.json`

# 工作流
1. 调 `Skill("kdev-secure-coding")`（如适用）。
2. 跑 SAST（bandit / semgrep / dependency-check 等，按 env-baseline.md 工具清单）。
3. Secrets 扫描（gitleaks）。
4. 产出 `.kdev/handoffs/dev/security.md`：发现清单 + 严重度 + 修复建议。
5. **同步派 安全评审员**（D4 阻断）：`run_in_background:false`。
6. PASS/FAIL/3-轮上限同前。

# 输出
`.kdev/handoffs/dev/security.md`
```

- [ ] **Step 6: Write `agents/部署上线员.md`**

```markdown
---
name: 部署上线员
description: KDev 开发组工作 agent — 合并 / 部署 / 收尾，最终落 dev/COMPLETE.md。来源 kdev-coding-flow 节点 11-13。D5 告警节点：异步派质量评审员最终抽查。
tools: Skill, Read, Write, Edit, Bash, Glob, Grep, Agent
model: sonnet
---

# 输入
dev 全套（plan / impl / e2e / security 都 PASS）

# 工作流
1. 用 `Skill("kdev-commit")` 合并到 feature 分支 / 主分支（按项目约定）。
2. 跑部署脚本（按 env-baseline.md）。
3. 写 `.kdev/handoffs/dev/deploy.md` 部署记录。
4. **异步派 质量评审员**（D5 告警）：`run_in_background:true`。
5. 用 `lib/handoffs.py::write_complete` 写 `dev/COMPLETE.md`。
6. step_complete + state.md update。

# 输出
`.kdev/handoffs/dev/deploy.md` + `.kdev/handoffs/dev/COMPLETE.md`
```

- [ ] **Step 7: Run agent-lint test; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/环境对齐员.md plugins/kdev-cluster-x3/agents/实施计划师.md plugins/kdev-cluster-x3/agents/TDD实现员.md plugins/kdev-cluster-x3/agents/E2E验收员.md plugins/kdev-cluster-x3/agents/安全扫描员.md plugins/kdev-cluster-x3/agents/部署上线员.md
git commit -m "feat(cluster-x3): 开发组 6 工作 agent definitions"
```

---

## Task 11: 测试组 4 工作 agent

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/测试点设计师.md`
- Create: `plugins/kdev-cluster-x3/agents/测试用例渲染员.md`
- Create: `plugins/kdev-cluster-x3/agents/UI自动化工程师.md`
- Create: `plugins/kdev-cluster-x3/agents/API自动化工程师.md`

骨架同 Task 9 / Task 10。填空表：

| name | description（一句话）| model | 输入 | 输出 | 评审节点 |
|---|---|---|---|---|---|
| 测试点设计师 | 设计测试点 .md（29119-4 标准） | sonnet | `handoffs/reqs/ar.csv` + `handoffs/dev/COMPLETE.md` | `handoffs/test/test-points.md` | **T1 阻断**：同步派测试设计评审员 |
| 测试用例渲染员 | 1:1 渲染为 fielded 用例 | sonnet | `handoffs/test/test-points.md` | `handoffs/test/test-cases.md` | T2 告警：异步派测试设计评审员（抽查）|
| UI自动化工程师 | Playwright 脚本 + 执行 | sonnet | `handoffs/test/test-cases.md` | `handoffs/test/ui-results.json` | — |
| API自动化工程师 | API 用例转换 + 执行 | sonnet | `handoffs/test/test-cases.md` | `handoffs/test/api-results.json` | — |

- [ ] **Step 1: Write `agents/测试点设计师.md`** —— 套 Task 9 骨架；步骤 1 Read AR + dev/COMPLETE；步骤 2 调 `Skill("kdev-test-points-v1")`；步骤 3 写 test-points.md；步骤 4 同步派测试设计评审员（T1 阻断）；3 轮上限。

- [ ] **Step 2: Write `agents/测试用例渲染员.md`** —— 调 `Skill("kdev-test-cases-v1")`；写 test-cases.md；步骤 4 异步派测试设计评审员（T2 告警），不等返回。

- [ ] **Step 3: Write `agents/UI自动化工程师.md`** —— 调 `Skill("kdev-ui-autotest")`；按 test-cases 跑 Playwright；结果写 ui-results.json。无独立评审。BLOCKED：写 events.log 后等组长。

- [ ] **Step 4: Write `agents/API自动化工程师.md`** —— 调 `Skill("kdev-uicase-to-apicase")` 转 API 用例 → 跑 API → 结果写 api-results.json。无独立评审。**对 `kdev-api-test-scaffold` 缺失情况**：v0.1 §10.2 D8 注记的"第一版可跳过仅跑 UI"，本 agent 在 `Skill("kdev-uicase-to-apicase")` 失败时写 `events.log <ts> API自动化工程师 note kdev-api-test-scaffold 缺失，跳过 API 自动化` + step_complete 空结果。

每个文件 50-80 行 markdown，4 字段 frontmatter + 6 段正文（角色 / 输入 / 工作流 / 输出 / 评审 / 异常）。

- [ ] **Step 5: Run agent-lint; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/测试点设计师.md plugins/kdev-cluster-x3/agents/测试用例渲染员.md plugins/kdev-cluster-x3/agents/UI自动化工程师.md plugins/kdev-cluster-x3/agents/API自动化工程师.md
git commit -m "feat(cluster-x3): 测试组 4 工作 agent definitions"
```

---

## Task 12: 审查组 10 评审员 agent

**Files:**
- Create: `plugins/kdev-cluster-x3/agents/SR评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/原型评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/方案设计评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/代码评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/质量评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/安全评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/测试设计评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/CEO视角评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/架构评审员.md`
- Create: `plugins/kdev-cluster-x3/agents/终审聚合员.md`

所有评审员**共用骨架**：

```markdown
---
name: <评审员名>
description: KDev 审查组评审员 — <职责一句话>。评审 checklist 见 standards/review/<name>-checklist.md。
tools: Read, Bash, Glob, Grep
model: opus
---

# 角色
KDev 审查组评审员（评审池共享，主控员或工作 agent 直接派）。

# 输入
- 主控员 / 工作 agent 在 prompt 里指定的产物路径（如 `.kdev/handoffs/reqs/sr.md`）
- 自身 checklist：`plugins/kdev-cluster-x3/standards/review/<name>-checklist.md`

# 工作流
1. Read 待评审产物 + checklist。
2. 按 checklist 逐项打分（PASS / FAIL / N/A）+ 留具体行号 / 引用证据。
3. 总评：PASS / FAIL（FAIL 必须列具体问题清单，每条带可执行修复建议）。
4. 把评审报告写到产物所在目录平级 `<name>-review.md`（如 `handoffs/reqs/SR评审员-review.md`）。
5. events.log 写 `<ts> <name> gate_pass|gate_fail R2|R4|R5|D2|D4|T1|F1` 一行。
6. 返回结构化结论给调用方（≤200 字摘要 + verdict）。

# 不做
- 不修改产物（修复是被评审 agent 的职责）。
- 不直接对话用户。
- 不调其它评审员（如需冲突仲裁，主控员或审查组长出面）。
```

10 个评审员唯一差异 = description 一句话 + checklist 引用文件名。统一表：

| name | description（一句话）|
|---|---|
| SR评审员 | 评 SR 需求规格质量（完备性 / 可验收 / FRs vs NFRs 完整）|
| 原型评审员 | 评原型可用性 / 一致性 / 是否符合项目 UED 规范 |
| 方案设计评审员 | 评技术方案完备性（架构 / 模块 / DB / API / 风险全覆盖）|
| 代码评审员 | 评 spec-conformance（diff 是否符合 plan + AR）|
| 质量评审员 | 评代码质量（命名 / 抽象 / 重复 / 测试覆盖）|
| 安全评审员 | 评安全合规（SAST 结果 + secrets + OWASP / CSO 视角）|
| 测试设计评审员 | 评测试覆盖度（按 AR 反查）+ 测试设计合理性 |
| CEO视角评审员 | 评商业价值 / 战略对齐 / 用户感知（F1 终审之一） |
| 架构评审员 | 评跨模块一致性 / 长期可维护性（F1 终审之一） |
| 终审聚合员 | 聚合 F1 两路评审 + 整体 R/D/T 评审历史 → 最终 verdict |

终审聚合员**比其它 9 个多一段**："# 终审独有职责" 在 F2 触发：

```markdown
# 终审独有职责
- 读 `.kdev/handoffs/review/{ceo.md, architecture.md}`（F1 两路）。
- 读 `.kdev/events.log` 过滤 R*/D*/T* 全部 gate_pass + gate_fail 历史。
- 出 `.kdev/handoffs/review/final-decision.md`：verdict ∈ {pass, conditional, reject}，conditional 必须列具体条件。
- 调用 `lib/handoffs.py::write_complete` 写 `review/COMPLETE.md`（含 verdict 字段）。
- F2 不可被驳回（这是终审 gate）；如评审员对结果不服，必须找审查组长仲裁。
```

- [ ] **Step 1: Write `agents/SR评审员.md`** —— 套骨架，description = "评 SR 需求规格质量（完备性 / 可验收 / FRs vs NFRs 完整）"。

- [ ] **Step 2 ~ 9: Write each of the remaining 8 reviewer files** —— 同样套骨架，description 按上表一一对应。每个文件 30-50 行 markdown。

- [ ] **Step 10: Write `agents/终审聚合员.md`** —— 套骨架 + 加 "# 终审独有职责" 段（见上）。

- [ ] **Step 11: Run agent-lint; expect PASS（全部 30 agents 现在都有了）**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

Also run a sanity command:
Run: `find plugins/kdev-cluster-x3/agents -name "*.md" | wc -l`
Expected: 30

- [ ] **Step 12: Commit**

```bash
git add plugins/kdev-cluster-x3/agents/*评审员.md plugins/kdev-cluster-x3/agents/终审聚合员.md
git commit -m "feat(cluster-x3): 审查组 10 评审员 agent definitions"
```

---

## Task 13: standards/ — 4 组组长 system prompt templates

**Files:**
- Create: `plugins/kdev-cluster-x3/standards/reqs/system-prompt-template.md`
- Create: `plugins/kdev-cluster-x3/standards/dev/system-prompt-template.md`
- Create: `plugins/kdev-cluster-x3/standards/test/system-prompt-template.md`
- Create: `plugins/kdev-cluster-x3/standards/review/system-prompt-template.md`

每份 = 该组组长在 4 meta 职责（监督 / 标准 / 聚合 / 应急）里**用的固定模板**（不是 agent definition 本身，是被 agent 在运行时 Read 的 reference）。

- [ ] **Step 1: Write `standards/reqs/system-prompt-template.md`**

```markdown
# 需求组组长 — system prompt 模板

> 这份文件是需求组长 agent 在阶段聚合 / 应急介入时**运行时 Read 的参考资料**。
> 维护者：本插件作者（审查组长另维护 review/ 的 checklist）。

## 聚合模板（reqs 5 step 全完成时）

请按以下 markdown 结构写 reqs-summary.md（≤800 字）：

```markdown
# reqs 阶段总结：<feature_slug>

## 完成 step
- [ ] IR — `handoffs/reqs/ir.md`
- [ ] SR — `handoffs/reqs/sr.md`（R2 PASS）
- [ ] AR 拆解 — `handoffs/reqs/ar.csv`，共 N 条
- [ ] prototype — `handoffs/reqs/prototype/`（R4 PASS）
- [ ] design.md — `handoffs/reqs/design.md`（R5 PASS）

## AR 列表（前 10 条）
| AR # | title | actor | priority |
|---|---|---|---|
| ... | ... | ... | ... |

## 主要决策记录
1. ...
2. ...

## 已知遗留问题
- ...
```

## 应急模板（on-blocked hook 派你介入）

输入 prompt 形如：`组员 BLOCKED：agent=<name> msg=<msg> 评审轮数=<N>`

按下面 4 选项决策（输出 ≤200 字）：

| 决策 | 触发场景 | 操作 |
|---|---|---|
| 重派该 agent（升档 opus） | 模型能力不足 | `Agent({subagent_type:<name>, model:"opus", prompt:"重试，加 context: <分析>"})` |
| 改派上游 agent 重做 | 上游产物质量不行 | 比如 SR 不行 → 改派需求澄清师重做 IR |
| 通知主控员（需要用户介入） | 信息不足 / 决策超出 reqs 边界 | 在 events.log `note 需要用户决策：<问题>` |
| 标污染样本继续 | 已知 corner case 不影响主流程 | events.log `note 标污染样本：<原因>` |

每次决策必须 events.log `<ts> 需求组长 <event_type> <msg>` 留痕。
```

- [ ] **Step 2: Write `standards/dev/system-prompt-template.md`** —— 套同模板，差异：

- 聚合产物文件名 `dev-summary.md`
- 完成 step 列表 = 6 项（env-baseline / plan / TDD impl / e2e / security / deploy）
- 用 `handoffs/dev/commits.json` 而非 `ar.csv` 作为统计来源
- 应急上游 agent 顺序：环境对齐员 → 实施计划师 → TDD实现员 → E2E验收员 → 安全扫描员 → 部署上线员

- [ ] **Step 3: Write `standards/test/system-prompt-template.md`** —— 套同模板，差异：

- 产物 `test-summary.md`
- 完成 step = 4 项（test-points / test-cases / UI / API）
- 关键指标：总用例数 + 通过率 + UI/API 分布
- 应急上游：测试点设计师 → 测试用例渲染员 → UI/API 自动化工程师

- [ ] **Step 4: Write `standards/review/system-prompt-template.md`** —— 套同模板 + 加一段「**冲突仲裁**」：

```markdown
## 冲突仲裁（审查组长独有）

当两个评审员对同一产物意见相反（典型场景：代码评审员 PASS / 质量评审员 FAIL）：

1. Read 两份 review.md。
2. 找到冲突点（用 grep 找两份评审里指向同一行号 / 同一 AR 的相反结论）。
3. 出仲裁决策：
   - 偏向其中一方 → 调用方按这一方修复。
   - 都对（双方各有道理）→ 升级到终审聚合员，附自己的仲裁分析。
4. events.log `<ts> 审查组长 note 评审冲突仲裁：<结论>`。

## standards/review/ 维护职责

10 个评审员的 checklist 文件（Task 14 后续填入）：

- SR评审员-checklist.md
- 原型评审员-checklist.md
- ...
- 终审聚合员-checklist.md

每次发现新的"评审漏检"问题，更新对应 checklist 并 commit。
```

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-cluster-x3/standards/{reqs,dev,test,review}/system-prompt-template.md
git commit -m "feat(cluster-x3): 4 组组长 system prompt templates"
```

---

## Task 14: standards/review/ — 10 评审员 checklist

**Files:**
- Create: `plugins/kdev-cluster-x3/standards/review/SR评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/原型评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/方案设计评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/代码评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/质量评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/安全评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/测试设计评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/CEO视角评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/架构评审员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/终审聚合员-checklist.md`
- Create: `plugins/kdev-cluster-x3/standards/review/conflict-arbitration.md`

每份 checklist = 8-15 条 yes/no 检查项 + 每条带证据要求。统一 frontmatter（无 yaml；这是 review 评审员要 Read 的 reference）。

- [ ] **Step 1: Write `standards/review/SR评审员-checklist.md`**

```markdown
# SR评审员 checklist（R2 阻断 / R3 抽查）

> 评审对象：`.kdev/handoffs/reqs/sr.md`
> 评审结论：PASS / FAIL（FAIL 必须列具体问题）

## R2 必检项（8 条 / 1 项 FAIL = 总体 FAIL）

1. [ ] **FRs 完整**：所有用户故事都有对应功能需求条目，每条带「角色 / 触发 / 行为 / 期望」四要素。
2. [ ] **NFRs 完整**：至少覆盖性能 / 安全 / 可用性 / 可维护性 4 类，每条可量化（数字或对比基线）。
3. [ ] **假设明确**：列出至少 3 条假设条件，标注「待用户确认」or「已确认」。
4. [ ] **范围明确**：In Scope / Out of Scope 各列至少 3 条。
5. [ ] **上下文充分**：跟现有系统 / 依赖系统的关系明确。
6. [ ] **验收线索可执行**：至少 5 条验收标准，每条可写成测试用例。
7. [ ] **回溯 IR**：SR 每个 section 都能回溯到 IR 的对应段。
8. [ ] **无 TBD / TODO / FIXME** 占位。

## R3 抽查项（AR 拆解后回看）

- [ ] AR.csv 中每条 AR 都能回溯到 SR 的某个 FR 或 NFR。
- [ ] AR 数量合理（≥ FR 数 × 1.5 倍 — 太少则颗粒度过粗）。

## 输出格式

写到 `.kdev/handoffs/reqs/SR评审员-review.md`：

\`\`\`markdown
# SR评审员 review — R2

verdict: PASS | FAIL
date: <ISO-ts>

## 检查项结果
1. ✅ FRs 完整
2. ❌ NFRs 完整 — 缺失「性能」与「可维护性」类，建议补 §3.2 章节
...

## 问题清单（FAIL 必填）
- ...
\`\`\`
```

- [ ] **Step 2 ~ 10: Write each of the other 9 checklist files**

按下表填空。每份 checklist 8-12 条必检项 + 输出格式段：

| name | 关键检查维度（≥6 条）|
|---|---|
| 原型评审员 | UI 完整性 / 项目 UED 规范遵守 / 关键流转 / 边界态 / 错误态 / 响应式 / 可访问性 / 与 AR 对应 |
| 方案设计评审员 | 架构图存在且自洽 / 模块拆分合理 / DB schema 完整 / API 列表覆盖 AR / 风险列举 / 关键决策记录 / 性能/扩展考量 / 与 prototype 一致 |
| 代码评审员 | diff 与 plan 任务对齐 / commit 粒度 / spec-conformance / 命名 / 边界 / 测试存在 |
| 质量评审员 | 命名表达力 / 抽象层级 / DRY / YAGNI / 测试覆盖 / 错误处理 / 注释合理性 / 性能热点 |
| 安全评审员 | SAST 全部高危处理 / secrets 0 暴露 / 鉴权/授权检查 / 输入校验 / OWASP Top 10 / 日志不打 PII / 依赖漏洞 |
| 测试设计评审员 | 覆盖度（按 AR 反查）/ 边界态 / 异常态 / 等价类 / 优先级排序 / 自动化可行性 |
| CEO视角评审员 | 商业价值 / 用户感知 / 战略对齐 / ROI / 上线风险 |
| 架构评审员 | 长期可维护 / 模块边界 / 跨模块影响 / 命名/契约/扩展点稳定性 |
| 终审聚合员 | F1 两路评审是否一致 / R/D/T 历史 gate_pass 数 / 遗留高风险 / 最终 verdict 充分性 |

每份文件遵守 SR评审员 checklist 的章节结构（必检项 / 抽查项【可选】/ 输出格式）。

- [ ] **Step 11: Write `standards/review/conflict-arbitration.md`**

```markdown
# 评审员冲突仲裁手册

> 用户：审查组长 (X3 矩阵式)

## 何时触发

任意阶段，两个评审员对同一产物给出相反 verdict：
- 典型：D2 代码评审员 PASS + 质量评审员 FAIL（diff 符合规范但实现质量差）
- 典型：R5 方案设计评审员 PASS + 架构评审员（如果在 F1 早期）FAIL

## 仲裁流程

1. 主控员 / 调用方 events.log 写 `<ts> 主控员 note 评审冲突：<两评审员> <产物>`。
2. 主控员调审查组长（慢路径）：`Agent({subagent_type:"审查组长", prompt:"仲裁冲突：<两份 review.md 路径>"})`。
3. 审查组长 Read 两份 review.md，找冲突点（grep 同行号 / 同 AR 的相反结论）。
4. 出仲裁决策（≤200 字），写到 `.kdev/handoffs/<group>/arbitration-<ts>.md`。
5. 决策选项：
   - **偏向其中一方**：写明理由 → 调用方按这一方修复 → 重派**另一方**评审验证。
   - **双方都对**：升级到终审聚合员（在 F1 阶段后才用此选项，早期阶段优先让审查组长拍板）。

## 输出格式

```markdown
# 评审冲突仲裁 — <feature_slug> @ <ts>

冲突双方：<A评审员> vs <B评审员>
产物：<path>
冲突点：<具体行号 / AR>

仲裁结论：<偏向 A | 偏向 B | 升级终审>

理由：
1. ...
2. ...

修复指引：
- <调用方应做什么>
```
```

- [ ] **Step 12: Run standards-lint test (define in next sub-step)**

Actually defer the standards-lint test to Task 26 (integration smoke). Just run agent-lint to confirm nothing broke:

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_agent_lint.py -v`
Expected: 4 passed.

- [ ] **Step 13: Commit**

```bash
git add plugins/kdev-cluster-x3/standards/review/
git commit -m "feat(cluster-x3): standards/review/ 10 checklist + 冲突仲裁手册"
```

---

## Task 15: hooks/on-blocked.py — events.log → 派组长

**Files:**
- Create: `plugins/kdev-cluster-x3/hooks/on-blocked.py`
- Create: `plugins/kdev-cluster-x3/hooks/lib/__init__.py`
- Create: `plugins/kdev-cluster-x3/hooks/lib/event_router.py`
- Create: `plugins/kdev-cluster-x3/hooks/hooks.json`
- Create: `plugins/kdev-cluster-x3/hooks/run-python-hook.cmd`
- Create: `plugins/kdev-cluster-x3/tests/test_on_blocked.py`
- Delete: `plugins/kdev-cluster-x3/hooks/on-blocked.sh.placeholder`

Hook 目标：每次 `events.log` 被追加（PostToolUse 匹配 Write 工具），检测最新一行是否 `blocked`；如果是，按 agent 名映射到组长 → 输出一条**指令给 Claude**（hook 可以用 stdout 注入提示）让主控员派组长。注意 Claude Code hook 输出会作为 user-message-like 注入到对话。

- [ ] **Step 1: Copy hook launcher from kdev-memory**

```bash
cp plugins/kdev-memory/hooks/run-python-hook.cmd plugins/kdev-cluster-x3/hooks/run-python-hook.cmd
chmod +x plugins/kdev-cluster-x3/hooks/run-python-hook.cmd
```

(verify with `ls -l plugins/kdev-cluster-x3/hooks/run-python-hook.cmd` shows `-rwxr-xr-x`)

- [ ] **Step 2: Write failing tests**

```python
# plugins/kdev-cluster-x3/tests/test_on_blocked.py
from pathlib import Path
import json
import subprocess
import sys


HOOK = Path(__file__).parent.parent / "hooks" / "on-blocked.py"


def test_no_events_log_no_op(tmp_kdev):
    proc = subprocess.run(
        [sys.executable, str(HOOK)],
        cwd=tmp_kdev.parent,
        capture_output=True, text=True,
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_last_line_not_blocked_no_op(tmp_kdev):
    (tmp_kdev / "events.log").write_text(
        "2026-05-27T16:00:00+00:00\t需求规格师\tstep_complete\tSR 完成\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_last_line_blocked_emits_dispatch_directive(tmp_kdev):
    (tmp_kdev / "events.log").write_text(
        "2026-05-27T16:00:00+00:00\tTDD实现员\tblocked\trepro 失败 3 次\n",
        encoding="utf-8",
    )
    proc = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert proc.returncode == 0
    out = proc.stdout
    assert "开发组长" in out
    assert "TDD实现员" in out
    assert "repro 失败 3 次" in out


def test_double_fire_dedup(tmp_kdev):
    """连续两次触发，对同一 blocked 事件只输出一次 directive。"""
    events = tmp_kdev / "events.log"
    events.write_text(
        "2026-05-27T16:00:00+00:00\tTDD实现员\tblocked\thalt\n",
        encoding="utf-8",
    )
    p1 = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    p2 = subprocess.run([sys.executable, str(HOOK)], cwd=tmp_kdev.parent, capture_output=True, text=True)
    assert p1.stdout != ""
    assert p2.stdout.strip() == ""  # second fire: nothing new
```

- [ ] **Step 3: Run; expect FAIL (hook does not exist yet)**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_on_blocked.py -v`
Expected: 4 failed.

- [ ] **Step 4: Implement `hooks/lib/event_router.py`**

```python
# plugins/kdev-cluster-x3/hooks/lib/event_router.py
"""Map blocked-event agent → group lead to dispatch."""
from __future__ import annotations

AGENT_TO_LEAD = {
    # reqs
    "需求澄清师": "需求组长", "需求规格师": "需求组长", "需求拆解师": "需求组长",
    "原型设计师": "需求组长", "方案设计师": "需求组长",
    # dev
    "环境对齐员": "开发组长", "实施计划师": "开发组长", "TDD实现员": "开发组长",
    "E2E验收员": "开发组长", "安全扫描员": "开发组长", "部署上线员": "开发组长",
    # test
    "测试点设计师": "测试组长", "测试用例渲染员": "测试组长",
    "UI自动化工程师": "测试组长", "API自动化工程师": "测试组长",
    # review (评审员 BLOCKED 时找审查组长仲裁)
    "SR评审员": "审查组长", "原型评审员": "审查组长", "方案设计评审员": "审查组长",
    "代码评审员": "审查组长", "质量评审员": "审查组长", "安全评审员": "审查组长",
    "测试设计评审员": "审查组长", "CEO视角评审员": "审查组长",
    "架构评审员": "审查组长", "终审聚合员": "审查组长",
}


def lead_for(agent: str) -> str | None:
    return AGENT_TO_LEAD.get(agent)
```

- [ ] **Step 5: Implement `hooks/on-blocked.py`**

```python
#!/usr/bin/env python3
"""kdev-cluster-x3 BLOCKED event hook.

Trigger: any time events.log is appended (PostToolUse on Write).
Effect: if last line is `blocked` and not yet dispatched (dedup via state file),
print a dispatch directive to stdout — Claude Code will inject this as a user-side message,
so the main session's 主控员 then dispatches the relevant group lead.

Dedup: tracks last-handled line offset in .kdev/.on-blocked-cursor.
"""
from __future__ import annotations
from pathlib import Path
import sys

THIS = Path(__file__).resolve()
sys.path.insert(0, str(THIS.parent))
from lib.event_router import lead_for  # noqa: E402

EVENTS_LOG = Path(".kdev/events.log")
CURSOR = Path(".kdev/.on-blocked-cursor")


def main() -> int:
    if not EVENTS_LOG.exists():
        return 0
    text = EVENTS_LOG.read_text(encoding="utf-8")
    if not text.strip():
        return 0
    last_offset = CURSOR.read_text(encoding="utf-8").strip() if CURSOR.exists() else ""
    current_offset = str(EVENTS_LOG.stat().st_size)
    if last_offset == current_offset:
        return 0
    last_line = text.rstrip("\n").splitlines()[-1]
    parts = last_line.split("\t", 3)
    if len(parts) != 4:
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    ts, agent, event_type, msg = parts
    if event_type != "blocked":
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    lead = lead_for(agent)
    if lead is None:
        CURSOR.write_text(current_offset, encoding="utf-8")
        return 0
    # Emit a directive — Claude Code captures stdout and surfaces it.
    print(f"""
🚨 **BLOCKED 自动应急** ({ts})

工作 agent **{agent}** 写入 blocked 事件：
> {msg}

主控员：请立即派 **{lead}** 介入决策。建议 prompt 模板：

```
Agent({{
  subagent_type: "{lead}",
  prompt: "组员 BLOCKED：agent={agent} msg={msg} 评审轮数=<请补>"
}})
```

待 {lead} 返回决策后，按其指引执行（重派 / 升档 / 通知用户 / 标污染）。
""".strip())
    CURSOR.write_text(current_offset, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_on_blocked.py -v`
Expected: 4 passed.

- [ ] **Step 7: Write `hooks/hooks.json`**

```json
{
  "description": "kdev-cluster-x3: BLOCKED 事件自动触发组长介入。监听 PostToolUse(Write|Edit) — 当 .kdev/events.log 被追加时，hook 检测最后一行是否 blocked 并向对话流注入派单指令。",
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/run-python-hook.cmd\" on-blocked.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 8: Remove placeholder**

```bash
git rm plugins/kdev-cluster-x3/hooks/on-blocked.sh.placeholder
```

- [ ] **Step 9: Commit**

```bash
git add plugins/kdev-cluster-x3/hooks/
git commit -m "feat(cluster-x3): on-blocked hook — events.log → 派对应组长"
```

---

## Task 16: skills/kdev-statusline — CLI 单行 HUD

**Files:**
- Create: `plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh`
- Create: `plugins/kdev-cluster-x3/tests/test_statusline.py`

输出格式（≤80 chars）：`KDev | reqs:✅ dev:🟡(节点6b) test:⏳ review:⏳ | feature:<slug>` 给 Claude Code `.claude/settings.json` 的 `statusLine` 字段调用。

- [ ] **Step 1: Write failing test**

```python
# plugins/kdev-cluster-x3/tests/test_statusline.py
import os
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parent.parent / "skills" / "kdev-statusline" / "kdev-statusline.sh"


def _run(cwd: Path) -> str:
    return subprocess.run(["bash", str(SCRIPT)], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_no_state_md_returns_idle(tmp_kdev):
    # remove state.md to test empty state
    (tmp_kdev / "state.md").unlink()
    out = _run(tmp_kdev.parent)
    assert "idle" in out.lower() or out == ""


def test_in_progress_state_renders(tmp_kdev):
    (tmp_kdev / "state.md").write_text(
        "# KDev State\n\nfeature: 产品管理\nfeature_slug: chan-pin\n"
        "feature_started_at: 2026-05-27T16:00:00+00:00\n"
        "current_active_group: dev\n\n"
        "## reqs\nstatus: complete\ncurrent_step: -\n"
        "started_at: 2026-05-27T16:00:00\ncompleted_at: 2026-05-27T17:00:00\n"
        "last_progress: 全部完成\n\n"
        "## dev\nstatus: in_progress\ncurrent_step: node-6b\n"
        "started_at: 2026-05-27T17:00:00\ncompleted_at: -\n"
        "last_progress: TDD 节点 6b\n\n"
        "## test\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## review\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n",
        encoding="utf-8",
    )
    out = _run(tmp_kdev.parent)
    assert "KDev" in out
    assert "✅" in out  # reqs complete
    assert "🟡" in out  # dev in_progress
    assert "chan-pin" in out
    assert len(out) <= 100  # safety margin (target ≤80)


def test_blocked_state_renders_red(tmp_kdev):
    (tmp_kdev / "state.md").write_text(
        "# KDev State\n\nfeature: x\nfeature_slug: x\n"
        "feature_started_at: 2026-05-27T16:00:00+00:00\n"
        "current_active_group: dev\n\n"
        "## reqs\nstatus: complete\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## dev\nstatus: blocked\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: TDD halt\n\n"
        "## test\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n\n"
        "## review\nstatus: pending\ncurrent_step: -\nstarted_at: -\ncompleted_at: -\nlast_progress: -\n",
        encoding="utf-8",
    )
    out = _run(tmp_kdev.parent)
    assert "🔴" in out
```

- [ ] **Step 2: Run; expect FAIL**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_statusline.py -v`
Expected: 3 failed (script not found).

- [ ] **Step 3: Implement `kdev-statusline.sh`**

```bash
#!/usr/bin/env bash
# KDev cluster-x3 CLI statusLine — single-line HUD reading .kdev/state.md.
# Output target: ≤80 chars. Falls back to empty (no statusline) if state missing.

set -euo pipefail

STATE="${1:-.kdev/state.md}"
if [[ ! -r "$STATE" ]]; then
    exit 0
fi

slug=$(grep -m1 "^feature_slug:" "$STATE" | sed 's/^feature_slug: *//')
active=$(grep -m1 "^current_active_group:" "$STATE" | sed 's/^current_active_group: *//')

group_status() {
    local g="$1"
    local s
    s=$(awk -v g="$g" '
        $0 == "## " g { found=1; next }
        found && /^## / { exit }
        found && /^status:/ { print $2; exit }
    ' "$STATE")
    case "$s" in
        complete)    echo "✅" ;;
        in_progress) echo "🟡" ;;
        blocked)     echo "🔴" ;;
        pending)     echo "⏳" ;;
        *)           echo "·" ;;
    esac
}

reqs=$(group_status reqs)
dev=$(group_status dev)
test=$(group_status test)
review=$(group_status review)

# current_step suffix for the active group only (≤12 char to keep line short)
suffix=""
if [[ "$active" =~ ^(reqs|dev|test|review)$ ]]; then
    step=$(awk -v g="$active" '
        $0 == "## " g { found=1; next }
        found && /^## / { exit }
        found && /^current_step:/ { sub(/^current_step: */, ""); print; exit }
    ' "$STATE")
    if [[ -n "$step" && "$step" != "-" ]]; then
        suffix="($(echo "$step" | cut -c1-12))"
    fi
fi

if [[ -z "$slug" ]]; then
    echo "KDev | idle"
else
    case "$active" in
        reqs)   reqs="${reqs}${suffix}" ;;
        dev)    dev="${dev}${suffix}"   ;;
        test)   test="${test}${suffix}" ;;
        review) review="${review}${suffix}" ;;
    esac
    echo "KDev | reqs:${reqs} dev:${dev} test:${test} review:${review} | ${slug}"
fi
```

```bash
chmod +x plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh
```

- [ ] **Step 4: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_statusline.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add plugins/kdev-cluster-x3/skills/kdev-statusline plugins/kdev-cluster-x3/tests/test_statusline.py
git commit -m "feat(cluster-x3): kdev-statusline.sh — CLI 单行 HUD"
```

---

## Task 17: skills/kdev-hud — 3-mode HUD

**Files:**
- Create: `plugins/kdev-cluster-x3/skills/kdev-hud/SKILL.md`
- Create: `plugins/kdev-cluster-x3/skills/kdev-hud/references/hud-markdown.md`
- Create: `plugins/kdev-cluster-x3/skills/kdev-hud/references/hud-box.md`
- Create: `plugins/kdev-cluster-x3/commands/kdev-hud.md`
- Create: `plugins/kdev-cluster-x3/tests/test_skill_md_lint.py`

3 模式（v0.1 §6.2/6.3）：
- `markdown`（默认，对话流可读）
- `box`（CLI ASCII）
- `watch`（CLI 全屏 1s 刷新，本期实现为"建议用户起 `watch -n 1 kdev-statusline.sh`"，不在 skill 里写 fzf-style 全屏 loop）

- [ ] **Step 1: Write `skills/kdev-hud/SKILL.md`**

```markdown
---
name: kdev-hud
description: KDev 多智能体集群 HUD（实时状态面板）。读 .kdev/state.md + events.log 输出 3 种模式：markdown（默认，对话流）/ box（CLI ASCII）/ watch（提示用户起 `watch -n 1 kdev-statusline.sh`）。Use when 用户问"进度怎么样？/ hud / 看下状态 / 现在跑到哪了"，主控员在阶段完成时也应主动调本 skill 渲染 markdown。
---

# kdev-hud

实时状态面板。

## 输入参数

`$ARGUMENTS` 形如 `[markdown|box|watch]`。默认 `markdown`。

## 工作流

### 模式 1：markdown（默认 / VSCode 主推）

按 `references/hud-markdown.md` 的模板填充：
- Read `.kdev/state.md`（用 `lib/state_md.py::StateMd.read`）
- Read `.kdev/events.log` tail 5
- Read 4 个 `.kdev/handoffs/<g>/COMPLETE.md`（如存在）
- 把所有数据拼成 markdown 表格 + 最近事件 + 阶段产物链接，**直接输出到对话流**。

### 模式 2：box（CLI ASCII）

按 `references/hud-box.md` 模板。等宽字符画 + emoji 状态图标。

### 模式 3：watch

输出一段说明给用户：
\`\`\`
请在 CLI 终端跑 `watch -n 1 plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md` 看 1s 刷新版（VSCode 用户改用 markdown preview 看 .kdev/state.md）。
\`\`\`

## 设计意图（不直接渲染给用户）

- markdown 是 VSCode 用户主推。VSCode 扩展不渲染 statusLine（v0.1 §6.3 实测）。
- box 仅 CLI 用户。
- watch 不在 skill 内部实现 — Claude 不应自己起 polling 循环。
```

- [ ] **Step 2: Write `references/hud-markdown.md`**

```markdown
# HUD markdown 模板

> kdev-hud 的 markdown 模式输出。占位符由 SKILL.md 在运行时填充。

```markdown
## KDev HUD — `{feature_slug}`

started: {feature_started_at} · active: `{current_active_group}`

| 组 | 状态 | 当前 step | 最后进度 |
|---|---|---|---|
| reqs | {reqs.status_icon} {reqs.status} | {reqs.current_step} | {reqs.last_progress} |
| dev  | {dev.status_icon} {dev.status}   | {dev.current_step}  | {dev.last_progress}  |
| test | {test.status_icon} {test.status} | {test.current_step} | {test.last_progress} |
| review | {review.status_icon} {review.status} | {review.current_step} | {review.last_progress} |

### 最近事件（tail 5）

- {events[0]}
- {events[1]}
- {events[2]}
- {events[3]}
- {events[4]}

### 阶段产物（COMPLETE.md 存在的组）

- reqs: {reqs.complete_link}
- dev: {dev.complete_link}
- test: {test.complete_link}
- review: {review.complete_link}
```

状态图标：complete=✅ in_progress=🟡 blocked=🔴 pending=⏳
```

- [ ] **Step 3: Write `references/hud-box.md`**

```markdown
# HUD box 模板（CLI ASCII）

```
┌───────────────────────────────────────────────────────────┐
│ KDev cluster-x3 — {feature_slug}                          │
│ started: {feature_started_at}   active: {current_active_group} │
├───────────────────────────────────────────────────────────┤
│ reqs   {reqs.icon}   step:{reqs.current_step:<10} │ {reqs.last_progress:<24} │
│ dev    {dev.icon}    step:{dev.current_step:<10}  │ {dev.last_progress:<24}  │
│ test   {test.icon}   step:{test.current_step:<10} │ {test.last_progress:<24} │
│ review {review.icon} step:{review.current_step:<10} │ {review.last_progress:<24} │
├───────────────────────────────────────────────────────────┤
│ 最近事件:                                                  │
│ {events[0]}                                                │
│ {events[1]}                                                │
│ {events[2]}                                                │
└───────────────────────────────────────────────────────────┘
```
```

- [ ] **Step 4: Write `commands/kdev-hud.md`**

```markdown
---
description: 查看 KDev 多智能体集群实时进度（4 组状态 + 最近事件 + 产物链接）
argument-hint: [markdown|box|watch]
---

# /kdev:hud

调用 `kdev-hud` skill，把 `$ARGUMENTS` 透传。

参数原文：`$ARGUMENTS`
```

- [ ] **Step 5: Write skill-md lint test**

```python
# plugins/kdev-cluster-x3/tests/test_skill_md_lint.py
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent


def test_all_skills_have_frontmatter():
    for skill_md in ROOT.glob("skills/*/SKILL.md"):
        text = skill_md.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
        assert m, f"{skill_md} missing yaml frontmatter"
        fm = dict(line.partition(":")[::2] for line in m.group(1).splitlines() if ":" in line)
        assert "name" in {k.strip() for k in fm}, f"{skill_md} missing name field"
        assert "description" in {k.strip() for k in fm}, f"{skill_md} missing description field"


def test_all_commands_have_frontmatter():
    for cmd_md in ROOT.glob("commands/*.md"):
        text = cmd_md.read_text(encoding="utf-8")
        assert text.startswith("---\n"), f"{cmd_md} missing yaml frontmatter"
        assert "description:" in text.split("---", 2)[1], f"{cmd_md} frontmatter missing description"
```

- [ ] **Step 6: Run tests; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_skill_md_lint.py -v`
Expected: 2 passed.

- [ ] **Step 7: Commit**

```bash
git add plugins/kdev-cluster-x3/skills/kdev-hud plugins/kdev-cluster-x3/commands/kdev-hud.md plugins/kdev-cluster-x3/tests/test_skill_md_lint.py
git commit -m "feat(cluster-x3): /kdev:hud — 3-mode HUD skill"
```

---

## Task 18: skills/kdev-status — 单点状态快照

**Files:**
- Create: `plugins/kdev-cluster-x3/skills/kdev-status/SKILL.md`
- Create: `plugins/kdev-cluster-x3/commands/kdev-status.md`

`/kdev:status` 与 `/kdev:hud` 的差异：前者短促一行，跟 statusline.sh 输出一致；后者输出完整面板。

- [ ] **Step 1: Write `skills/kdev-status/SKILL.md`**

```markdown
---
name: kdev-status
description: KDev 多智能体集群状态快照（与 CLI statusLine 等效，单行）。Use when 用户问"一句话告诉我现在到哪了 / 简短进度 / status"。输出格式：`KDev | reqs:icon dev:icon test:icon review:icon | <slug>`。
---

# kdev-status

## 工作流

跑 `plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md` 并把输出原样放到对话流。

\`\`\`bash
bash plugins/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh .kdev/state.md
\`\`\`

如果 `.kdev/state.md` 不存在 → 直接输出 `KDev | 还没启动任何 feature。用 /kdev:start-feature <需求> 开始。`
```

- [ ] **Step 2: Write `commands/kdev-status.md`**

```markdown
---
description: KDev 集群单行状态快照
argument-hint: (no args)
---

# /kdev:status

调用 `kdev-status` skill。
```

- [ ] **Step 3: Run skill-md lint; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_skill_md_lint.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-cluster-x3/skills/kdev-status plugins/kdev-cluster-x3/commands/kdev-status.md
git commit -m "feat(cluster-x3): /kdev:status — 单行状态快照"
```

---

## Task 19: skills/kdev-start-feature — 主入口编排 skill

**Files:**
- Create: `plugins/kdev-cluster-x3/skills/kdev-start-feature/SKILL.md`
- Create: `plugins/kdev-cluster-x3/skills/kdev-start-feature/references/main-orchestration.md`
- Create: `plugins/kdev-cluster-x3/commands/kdev-start-feature.md`

主入口：解析需求 → init .kdev/ → 通知用户 → 派需求澄清师 → 进入主控员主循环。这个 skill 本质上是**给主控员的开场白**。

- [ ] **Step 1: Write `skills/kdev-start-feature/SKILL.md`**

```markdown
---
name: kdev-start-feature
description: KDev 多智能体集群 X3 矩阵式入口。Use when 用户说"用 KDev 跑一个新需求 / 启动新 feature / start-feature <需求>"。本 skill 仅做初始化 + 派出需求组工作 agent（**主控员 = 当前 session**，不另起 agent）；后续阶段聚合 / 慢路径 / 异常应急走 agents/ 下的 30 个 agent definition。
---

# kdev-start-feature

> 这是 KDev cluster-x3 的入口 skill。本 skill 完成后，**当前 session 就是主控员**——按 `agents/主控员.md` 的工作流继续编排。

## 输入

`$ARGUMENTS` = 用户提供的原始需求文本（中文/英文均可）。

## 工作流（init + 第一派单）

### 1. 解析需求 → slug

```bash
slug=$(python -c "from kdev_cluster_x3.lib.slug import slugify; print(slugify('$ARGUMENTS'))")
```

### 2. 初始化 .kdev/

```bash
mkdir -p .kdev/handoffs/{reqs,dev,test,review}
python -c "
from datetime import datetime, timezone
from pathlib import Path
from kdev_cluster_x3.lib.state_md import StateMd
StateMd.init(
    Path('.kdev/state.md'),
    feature='$ARGUMENTS',
    slug='$slug',
    started_at=datetime.now(timezone.utc),
)
"
touch .kdev/events.log
```

### 3. 通知用户

输出到对话流（≤200 字）：
```
✅ feature 已启动
- slug: <slug>
- 状态文件: .kdev/state.md
- 事件流: .kdev/events.log

我会按 X3 矩阵式编排：
1. 先派需求澄清师做 IR 澄清
2. 然后规格师 / 拆解师 / 原型 / 方案设计 — 每个阻断节点会同步派评审员
3. 全 reqs 完成后调需求组长做阶段聚合 → 你确认后进 dev
4. 你随时可以问 `/kdev:hud` 看进度，或打断我换方向

⏳ 现在派需求澄清师……
```

### 4. 第一派单：需求澄清师

```
Agent({
  subagent_type: "需求澄清师",
  prompt: "feature_slug=<slug>\n原始需求：<$ARGUMENTS>\n参考项目 CLAUDE.md。完成后写 .kdev/handoffs/reqs/ir.md。",
  run_in_background: true
})
```

### 5. 进入主控员主循环

读 `agents/主控员.md` 的「工作流」段，按状态机继续编排。

## 关键约束

- 本 skill 只跑一次（init 期间）。后续不要重复进入。
- 如已存在 `.kdev/state.md`（同 slug），询问用户是续跑还是覆盖（参考主控员的「跨 session 续航」段）。
```

- [ ] **Step 2: Write `commands/kdev-start-feature.md`**

```markdown
---
description: 启动 KDev cluster-x3 多智能体编排，跑完一个新 feature（reqs → dev → test → review）
argument-hint: <需求描述>
---

# /kdev:start-feature

把需求交给 KDev 集群跑全流程。

调用 `kdev-start-feature` skill，把 `$ARGUMENTS` 透传。
```

- [ ] **Step 3: Run lint; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_skill_md_lint.py -v`
Expected: 2 passed.

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-cluster-x3/skills/kdev-start-feature plugins/kdev-cluster-x3/commands/kdev-start-feature.md
git commit -m "feat(cluster-x3): /kdev:start-feature — 主入口编排 skill"
```

---

## Task 20: plugin.json 升级 + .claude-plugin manifest

**Files:**
- Modify: `plugins/kdev-cluster-x3/.claude-plugin/plugin.json`

把 version bumped 到 0.1.0（Phase 2 完成），description 改为反映实际内容。

- [ ] **Step 1: Modify `plugin.json`**

```json
{
  "name": "kdev-cluster-x3",
  "description": "KDev 多智能体集群 X3 矩阵式 / 轻组长 / 顾问 PM 落地实现：1 主控员 + 4 组长 + 25 工作 agent + 13 评审节点 + events.log 驱动的 BLOCKED 自动应急 hook + state.md/handoffs 跨组数据总线。通信走扁平（2 跳），组长仅在阶段聚合 + 异常应急 + 标准维护时激活。Use /kdev:start-feature 启动 / /kdev:hud 看进度 / /kdev:status 单行快照。",
  "version": "0.1.0",
  "author": {"name": "ly"},
  "license": "MIT",
  "keywords": ["kdev", "multi-agent", "cluster", "x3", "matrix", "light-tl", "advisor"]
}
```

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-cluster-x3/.claude-plugin/plugin.json
git commit -m "chore(cluster-x3): bump 0.0.1 → 0.1.0 (Phase 2 complete)"
```

---

## Task 21: standards-lint test

**Files:**
- Create: `plugins/kdev-cluster-x3/lib/standards_lint.py`
- Create: `plugins/kdev-cluster-x3/tests/test_standards_lint.py`

简单 lint：每个 `standards/review/*-checklist.md` 必须包含 `verdict:` token（最小输出格式约定）。每个 `standards/*/system-prompt-template.md` 必须有 `## 聚合模板` + `## 应急模板` 段。

- [ ] **Step 1: Write failing test**

```python
# plugins/kdev-cluster-x3/tests/test_standards_lint.py
from pathlib import Path
from kdev_cluster_x3.lib.standards_lint import lint_standards_dir

ROOT = Path(__file__).parent.parent


def test_no_lint_issues_after_full_population():
    issues = lint_standards_dir(ROOT / "standards")
    assert issues == [], f"standards lint failed: {issues}"
```

- [ ] **Step 2: Implement `lib/standards_lint.py`**

```python
# plugins/kdev-cluster-x3/lib/standards_lint.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StandardsIssue:
    path: Path
    msg: str


def lint_standards_dir(root: Path) -> list[StandardsIssue]:
    root = Path(root)
    issues: list[StandardsIssue] = []
    if not root.exists():
        return issues
    # 1) all review checklists must have "verdict" token
    for md in sorted((root / "review").glob("*-checklist.md")):
        text = md.read_text(encoding="utf-8")
        if "verdict" not in text:
            issues.append(StandardsIssue(md, "checklist missing 'verdict' token"))
    # 2) all system-prompt-template.md must have aggregation + emergency sections
    for md in sorted(root.rglob("system-prompt-template.md")):
        text = md.read_text(encoding="utf-8")
        if "## 聚合模板" not in text:
            issues.append(StandardsIssue(md, "missing '## 聚合模板' section"))
        if "## 应急模板" not in text and "## 应急" not in text:
            issues.append(StandardsIssue(md, "missing '## 应急模板' section"))
    return issues
```

- [ ] **Step 3: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_standards_lint.py -v`
Expected: 1 passed.

If FAIL, the previous Task 13/14 sections of standards/ are incomplete — fix the missing section/token there and re-run.

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-cluster-x3/lib/standards_lint.py plugins/kdev-cluster-x3/tests/test_standards_lint.py
git commit -m "feat(cluster-x3): standards-lint test"
```

---

## Task 22: 集成 smoke — handoff dry-run

**Files:**
- Create: `plugins/kdev-cluster-x3/tests/test_smoke_handoff_dry_run.py`

模拟 reqs/dev/test/review 全流程的 handoff 落盘（不真实调 agent — 测的是底层 lib 之间的 wiring 没漏）。

- [ ] **Step 1: Write the smoke test**

```python
# plugins/kdev-cluster-x3/tests/test_smoke_handoff_dry_run.py
"""Smoke test: simulate the full state.md + events.log + handoffs/ lifecycle."""
from datetime import datetime, timezone
from pathlib import Path

from kdev_cluster_x3.lib.state_md import StateMd, GROUPS
from kdev_cluster_x3.lib.events_log import EventsLog, EventType
from kdev_cluster_x3.lib.handoffs import write_complete, read_complete
from kdev_cluster_x3.lib.ar_number import is_valid_ar


def test_full_lifecycle(tmp_kdev):
    started = datetime(2026, 5, 27, 16, 0, 0, tzinfo=timezone.utc)
    s = StateMd.init(tmp_kdev / "state.md", feature="产品管理三层", slug="chan-pin", started_at=started)
    log = EventsLog(tmp_kdev / "events.log")

    # reqs
    s.update_group("reqs", status="in_progress", current_step="ir")
    s.write(tmp_kdev / "state.md")
    log.append(agent="需求澄清师", event_type=EventType.STEP_COMPLETE, msg="IR 完成")
    assert is_valid_ar("AR-PROD_LINE-01.001.001")
    write_complete(
        tmp_kdev / "handoffs" / "reqs" / "COMPLETE.md",
        group="reqs", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", ar_count=12,
    )
    s = StateMd.read(tmp_kdev / "state.md")
    s.update_group("reqs", status="complete")
    s.write(tmp_kdev / "state.md")

    # dev
    s.update_group("dev", status="in_progress", current_step="node-6b")
    s.write(tmp_kdev / "state.md")
    write_complete(
        tmp_kdev / "handoffs" / "dev" / "COMPLETE.md",
        group="dev", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", commits_count=7,
    )

    # test
    write_complete(
        tmp_kdev / "handoffs" / "test" / "COMPLETE.md",
        group="test", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", total_cases=20, passed_cases=20,
    )

    # review
    write_complete(
        tmp_kdev / "handoffs" / "review" / "COMPLETE.md",
        group="review", completed_at=datetime.now(timezone.utc),
        feature_slug="chan-pin", verdict="pass",
    )

    # final assertions
    for g in GROUPS:
        meta = read_complete(tmp_kdev / "handoffs" / g / "COMPLETE.md")
        assert meta["group"] == g
        assert meta["status"] == "complete"

    # 6 events.log entries minimum (1 step_complete in this micro-test; real flow has many more)
    assert len(log.read_all()) >= 1
```

- [ ] **Step 2: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_smoke_handoff_dry_run.py -v`
Expected: 1 passed.

- [ ] **Step 3: Run full test suite to check for regressions**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest -v`
Expected: all tests across all files pass — sum should be roughly 30+ tests.

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-cluster-x3/tests/test_smoke_handoff_dry_run.py
git commit -m "test(cluster-x3): handoff dry-run smoke covering state+events+handoffs"
```

---

## Task 23: CLAUDE.md — 插件级使用指引

**Files:**
- Create: `plugins/kdev-cluster-x3/CLAUDE.md`

写一份**装上本插件的项目根 CLAUDE.md 应该包含什么**的范例 + 本插件的协议约束（避免与项目 CLAUDE.md 冲突）。

- [ ] **Step 1: Write `CLAUDE.md`**

```markdown
# kdev-cluster-x3 插件使用指引

## 装上插件后，项目根 CLAUDE.md 应包含

> 本段是给"装上 kdev-cluster-x3 的下游项目"的 CLAUDE.md 模板。这是**协议**——主控员 + 30 agent 都会在 prompt 里强制 Read 项目根 CLAUDE.md。

### 1. 项目硬约束

把项目的不可妥协规则写到 CLAUDE.md（如 UED 6.0 / 12 大原则 / 触发路由表）。**插件不在自身写规则**——所有 agent 顶部强制读项目 CLAUDE.md，把项目当规则源。

### 2. 启动命令

```
/kdev:start-feature <需求描述>
```

主控员（= 当前 session）按 X3 矩阵式编排 reqs → dev → test → review。

### 3. 查看进度

```
/kdev:hud           # 完整 markdown 面板
/kdev:status        # 单行快照
```

CLI 用户可以加 statusLine：
```jsonc
// .claude/settings.json
{
  "statusLine": {
    "type": "command",
    "command": "bash ${HOME}/.claude/plugins/cache/kdev-cluster-x3/skills/kdev-statusline/kdev-statusline.sh"
  }
}
```

### 4. 跨 session 续航

新 session 启动时说"继续上次的工作 / resume"。主控员会读 `.kdev/state.md` 报告"上次到哪里"。

## 协议约束

🔴 **铁规 1**：主控员 / 30 agent 不直接对话用户。用户只跟当前 session 的主控员说话。
🔴 **铁规 2**：`.kdev/` 目录由插件管理（state.md / events.log / handoffs/）。不要手动改 — 改了会被下次 agent 派单覆盖。
🔴 **铁规 3**：评审循环 3 轮上限。第 4 轮自动 events.log `blocked` 触发组长介入（on-blocked hook）。
🔴 **铁规 4**：AR 编号格式 `AR-{DOMAIN}-{MAJOR:02d}.{MINOR:03d}.{PATCH:03d}`。需求拆解师产出 ar.csv 时强校验。

## 故障 / 应急

| 症状 | 排查 |
|---|---|
| events.log 写了 blocked 但组长没派 | 检查 hooks/on-blocked.py 是否可执行；检查 hooks.json 已被 Claude Code 加载 |
| state.md 损坏 | rm `.kdev/state.md`，新 session 用 `/kdev:start-feature` 重启（之前的 handoffs/ 保留可参考）|
| 评审员意见冲突 | 主控员调审查组长（慢路径）做仲裁，参考 standards/review/conflict-arbitration.md |
| 跨 session 续航失败 | 检查 .kdev/state.md 的 4 组 section 是否完整；若损坏，从最近 events.log step_complete 重建 |
```

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-cluster-x3/CLAUDE.md
git commit -m "docs(cluster-x3): CLAUDE.md — 插件使用指引 + 协议约束"
```

---

## Task 24: CHANGELOG + README 更新

**Files:**
- Modify: `plugins/kdev-cluster-x3/README.md`
- Create: `plugins/kdev-cluster-x3/CHANGELOG.md`

README "状态" 表格改为 Phase 2 完成；CHANGELOG 起 v0.1.0 条目。

- [ ] **Step 1: Update README 状态表**

把 README.md 第一段「状态」表格里的 `Phase 1 骨架` → `Phase 2 实施完成（v0.1.0）`；下一步行改为「Phase 3：在 sop_test0518-x3 跑真实切片实测」。

- [ ] **Step 2: Update README "Agent 清单（待 Phase 2 填充）" 段**

去掉「（待 Phase 2 填充）」字样，确认 30 个 agent 名称与 `agents/` 目录下文件一一对应。

- [ ] **Step 3: Write `CHANGELOG.md`**

```markdown
# CHANGELOG

## v0.1.0 (2026-05-27)

Phase 2 实施完成：

### 新增

- 30 个 agent definitions（1 主控员 + 4 轻组长 + 25 工作 agent）
- 4 个 skill（/kdev:start-feature、/kdev:hud、/kdev:status、kdev-statusline.sh）
- 14 份 standards（4 组组长 system prompt template + 10 评审 checklist + conflict-arbitration）
- 1 个 hook（on-blocked.py — events.log → 派组长）
- Python lib（state_md / events_log / ar_number / handoffs / slug / agent_lint / standards_lint）
- 完整 pytest 套件（30+ tests）

### 已知遗留议题（v0.2 待细化）

参考 [X1 vs X3 对比文档 v0.2 §5.7](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md#57-待用户细化议题v02-填)：

1. IR 阶段（R1）是否需要独立评审员
2. D1 实施计划完成是阻断还是告警
3. TDD 增量（D2）的"增量颗粒度"细则
4. 终审聚合员（F2）额外评审标准
5. 评审循环 3 次后 BLOCKED 阈值是否合理
6. 评审员之间冲突（如代码评审员 vs 质量评审员）仲裁默认归属

### 下一步

- Phase 3：在 sop_test0518-x3 worktree 跑「产品管理三层模型」实测，按 [v0.2 §8 实测计划](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md#8-实测计划-worktree--sop_test0518) 收集 9 项对比指标。
```

- [ ] **Step 4: Commit**

```bash
git add plugins/kdev-cluster-x3/README.md plugins/kdev-cluster-x3/CHANGELOG.md
git commit -m "docs(cluster-x3): README/CHANGELOG → v0.1.0 (Phase 2 complete)"
```

---

## Task 25: 跨 session 续航 — 手动复测

**Files:**
- Modify: `plugins/kdev-cluster-x3/tests/test_smoke_handoff_dry_run.py`（已建，扩展）

加一个"模拟新 session 启动" 的子测试。

- [ ] **Step 1: Add resume test**

Append to `tests/test_smoke_handoff_dry_run.py`:

```python
def test_resume_after_interrupt(tmp_kdev):
    """Simulate: reqs complete, dev half-done (node-6b), then new session reads state and resumes."""
    from datetime import datetime, timezone
    from pathlib import Path
    from kdev_cluster_x3.lib.state_md import StateMd
    from kdev_cluster_x3.lib.events_log import EventsLog, EventType

    # "previous session": reqs done, dev stopped at node-6b
    s = StateMd.init(tmp_kdev / "state.md", feature="x", slug="x", started_at=datetime.now(timezone.utc))
    s.update_group("reqs", status="complete", current_step="-")
    s.update_group("dev", status="in_progress", current_step="node-6b", last_progress="TDD 实现员跑到一半")
    s.write(tmp_kdev / "state.md")
    log = EventsLog(tmp_kdev / "events.log")
    log.append(agent="TDD实现员", event_type=EventType.STEP_START, msg="开始 node-6b")
    # session crash here — no step_complete

    # "new session": read state.md, identify which group is mid-progress
    s2 = StateMd.read(tmp_kdev / "state.md")
    assert s2.groups["reqs"]["status"] == "complete"
    assert s2.groups["dev"]["status"] == "in_progress"
    assert s2.groups["dev"]["current_step"] == "node-6b"
    # main agent's recovery logic should now re-dispatch TDD实现员 starting at node-6b
    # (idempotency: it should detect step_start without matching step_complete in events.log)
    events = log.read_all()
    starts = [e for e in events if e.event_type == "step_start" and e.agent == "TDD实现员"]
    completes = [e for e in events if e.event_type == "step_complete" and e.agent == "TDD实现员"]
    assert len(starts) > len(completes), "should detect dangling step_start (= needs resume)"
```

- [ ] **Step 2: Run; expect PASS**

Run: `cd plugins/kdev-cluster-x3 && python -m pytest tests/test_smoke_handoff_dry_run.py -v`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add plugins/kdev-cluster-x3/tests/test_smoke_handoff_dry_run.py
git commit -m "test(cluster-x3): cross-session resume smoke"
```

---

## Task 26: 完整 pytest 套件最终回归

- [ ] **Step 1: Run the entire suite from a clean cwd**

```bash
cd plugins/kdev-cluster-x3 && python -m pytest -v --tb=short
```

Expected: **all** tests pass. Tally roughly:
- test_slug.py — 6
- test_state_md.py — 5
- test_events_log.py — 5
- test_ar_number.py — 10
- test_handoffs.py — 4
- test_agent_lint.py — 4
- test_on_blocked.py — 4
- test_statusline.py — 3
- test_skill_md_lint.py — 2
- test_standards_lint.py — 1
- test_smoke_handoff_dry_run.py — 2

Total ≈ 46 passing.

- [ ] **Step 2: If any test fails, fix the underlying file** (don't loosen the test). Loop until 0 failures.

- [ ] **Step 3: Sanity directory counts**

```bash
echo "agents: $(find plugins/kdev-cluster-x3/agents -name '*.md' | wc -l) (expect 30)"
echo "skills: $(find plugins/kdev-cluster-x3/skills -name 'SKILL.md' -o -name 'kdev-statusline.sh' | wc -l) (expect 4)"
echo "commands: $(find plugins/kdev-cluster-x3/commands -name '*.md' | wc -l) (expect 3)"
echo "standards-review: $(find plugins/kdev-cluster-x3/standards/review -name '*.md' | wc -l) (expect 11 — 10 checklist + conflict-arbitration)"
echo "standards-templates: $(find plugins/kdev-cluster-x3/standards -name 'system-prompt-template.md' | wc -l) (expect 4)"
echo "hooks: $(ls plugins/kdev-cluster-x3/hooks/*.py 2>/dev/null | wc -l) (expect 1)"
```

Expected: 30 / 4 / 3 / 11 / 4 / 1.

- [ ] **Step 4: No commit (just verification).**

---

## Task 27: 跨 worktree 合并准备（不合入 main，留给领导评审）

按 v0.2 §8.9「实测数据全部出来 → 领导评审 → 拍板 X1 或 X3 → winner 合并到 main」流程，**本计划完成时 X3 worktree 不合入 main**。

- [ ] **Step 1: Push worktree branch**

```bash
git push -u origin feature/cluster-x3
```

- [ ] **Step 2: 在 kdev-agents 主 worktree 用 `.kdev/memory/` 记录里程碑**

回到主 worktree（`/home/lyadmin/Projects/kdev-agents/`），在 `.kdev/memory/` 里加一条 Step 条目：

```markdown
## Step <N>: kdev-cluster-x3 v0.1.0 实施完成

时间：2026-XX-XX
分支：feature/cluster-x3（已 push）

产物：
- 30 个 agent definitions
- 4 skill + 3 命令 + 1 hook + 14 standards
- 46+ 个 pytest 测试全绿

下一步：
- 在 sop_test0518-x3（项目 clone）跑实测
- 按 v0.2 §8.6 收集 9 项对比指标
- 合并写入 docs/framework/01-design/2026-XX-XX-实测报告-X1-vs-X3.md
```

- [ ] **Step 3: 不开 PR / 不合并到 main**。

---

## Task 28: 遗留议题登记

**Files:**
- Modify: `plugins/kdev-cluster-x3/README.md`（追加 follow-ups 段）

把 v0.2 §5.7 + CHANGELOG 提到的 6 项议题登记到 README，等真实实测数据回来后回写。

- [ ] **Step 1: Append to README**

在 README 末尾追加：

```markdown
## 遗留议题（v0.1 → v0.2 待回写）

> 来源：[X1 vs X3 对比 v0.2 §5.7](../../docs/framework/01-design/2026-05-27-02-KDev多智能体集群-X1群组-vs-X3矩阵对比.md#57-待用户细化议题v02-填)。在 Phase 3 实测之前不强制回答，等实测真实数据回来后回写本节。

- [ ] IR 阶段（R1）是否需要独立评审员
- [ ] D1 实施计划完成是阻断还是告警
- [ ] TDD 增量（D2）的"增量颗粒度"——按 commit / 按 AR / 按 unit test 文件
- [ ] 终审聚合员（F2）额外评审标准
- [ ] 评审循环 3 次后 BLOCKED 阈值是否合理
- [ ] 评审员之间冲突（如代码评审员 vs 质量评审员）仲裁默认归属
```

- [ ] **Step 2: Commit**

```bash
git add plugins/kdev-cluster-x3/README.md
git commit -m "docs(cluster-x3): 登记 v0.1 → v0.2 遗留议题"
```

---

## Self-Review Notes

读完整个计划后做了一遍 spec coverage check：

| 来源章节 | 计划任务 |
|---|---|
| README §架构、§通信规则、§组长 4 meta 职责 | Task 7（主控员）+ Task 8（4 组长）|
| README §目录结构 | Task 1 + 各 Task 的 Files 段 |
| README §Agent 清单 | Task 7 + Task 8 + Task 9 + Task 10 + Task 11 + Task 12 |
| README §评审节点接入 | Task 12（10 评审员）+ Task 14（10 checklist）+ 各工作 agent 评审节点 |
| v0.2 §3.2 4 meta 职责 | Task 8（4 组长 agent 工作流）+ Task 13（standards templates）|
| v0.2 §3.4 A/B/C 三场景 | A → Task 7 快路径 + Task 9 评审派单；B → Task 8 聚合工作流 + Task 13 聚合模板；C → Task 15 on-blocked hook |
| v0.2 §3.5 4 决策 | Task 8（聚合）+ Task 15（hook）+ Task 13（standards 路径）+ Task 7（快/慢路径）|
| v0.2 §5 13 评审节点 | Task 7（速查表）+ Task 9/10/11（每个工作 agent 节点接入）+ Task 12（10 评审员） |
| v0.2 §5.6 评审调用规约 | Task 9 需求规格师工作流（同步派 SR评审员）+ 所有阻断节点 agent 同款 |
| v0.1 §3.1 AR 编号格式 | Task 4 lib/ar_number.py + Task 9 需求拆解师强校验 |
| v0.1 §3.2 handoffs/ 总线 | Task 5 lib/handoffs.py + 4 个 COMPLETE.md 模板 |
| v0.1 §3.3 state.md schema | Task 2 lib/state_md.py + Task 19 init |
| v0.1 §3.4 events.log 格式 | Task 3 lib/events_log.py |
| v0.1 §6 HUD 多形态 | Task 16 statusline + Task 17 hud + Task 18 status |
| v0.1 §7 跨 session 续航 | Task 25 resume smoke + Task 7 主控员"跨 session 续航"段 |

**Placeholder scan：** 我把每个 reviewer / 工作 agent 的 description / 工作流要点全部填到了表格里（Task 10/11/12），engineer 按表填即可，没有 "TBD" / "implement later" 字样。**唯一可争议**：Task 10/11/12 的 step 2-5/9 没有把所有 30 个 agent 全文展开（只展开 reqs 5 个为完整范例），其它套同骨架；这是为了避免重复同款 60 行 markdown × 23 次。如果 engineer 在执行时觉得这一节抽象度不够，可以回填到本计划。

**Type consistency：** `agent_to_group()` / `AGENT_GROUP` / `AGENT_TO_LEAD` 三个映射表是 30 个 agent 名的硬约束，三处必须同步。本计划 Task 3 + Task 15 + Task 12 都按同一组 30 中文名走。`StateMd.update_group()` / `write_complete()` / `EventType` 跨任务名字一致。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-27-kdev-cluster-x3.md`.** 两种执行方式：

**1. Subagent-Driven（推荐）** — 主控会派 fresh subagent 跑每个 Task，Task 之间审一审，迭代快。

**2. Inline Execution** — 当前 session 直接执行，按 task 分批 checkpoint。

**Which approach?**
