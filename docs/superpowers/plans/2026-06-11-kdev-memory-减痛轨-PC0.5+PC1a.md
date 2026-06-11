# kdev-memory 减痛轨 P-C0.5（评分模式可配）+ P-C1a（brief 分级 + subagent 精简）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 kdev-memory 对主会话的"每 Step 必追问用户评分"硬闸门降为 `rating.mode` 三档可配（model-only / user-opt-in / user-required），并给 SessionStart brief 加 `brief.verbosity` 三档分级 + 让 step-recorder subagent 只回一行——合并为一次 v0.14.0 → v0.15.0 bump。

**Architecture:** 纯 stdlib，line-based config parser（flat dot-key 单层）。核心是给 `step_completeness` 加 `rating_mode` 形参（默认 `user-required` 保持现有测试字节级不变），调用方 hook（brief / stop-check）从 `config.yaml` 读模式后传入；`model-only`/`user-opt-in` 下"用户评分段空"不再算半残。`parse_steps` 补"读 header 内联 `status:`"（修历史 latent bug，让 voided-faded 销账真正生效）。一次性幂等迁移脚本批量给 Q-002 后的 ~45 条半残 Step 盖 `status: voided-faded`。

**Tech Stack:** Python 3 stdlib（re / pathlib / unittest / pytest）；hooks 经 importlib 动态加载 lib 模块；测试 `cd plugins/kdev-memory && python3 -m pytest tests/ -q`（基线 **291 passed**）。

**硬约束（全程不可破）：**
- 向后兼容：`rating.mode` 默认 `user-opt-in`、`brief.verbosity` 默认 `normal`；`user-required` = 现行行为**完整保留**。
- **model-only 绝不伪造用户评分**——用户评分段留空 `—` 骨架 + `status: voided-faded`，绝不拷自评分进去（污染 misalignment 切片）。对齐 Q-002。
- config 全用 **flat dot-key**（`rating.mode` / `brief.verbosity`），不用两级嵌套（`memory_config.py` parser 只支持单层）。
- 不预留 `peer_review` 字段（他评已 defer）。
- 不碰 P-C1b transcript 溯源（commit-tracker offset / step-recorder input 重写都不做）。
- `step_completeness` 的内部默认 `rating_mode="user-required"`，保证既有 11 个测试文件不被这次改动波及。

---

## File Structure

**改动文件清单（每文件单一责任；同一文件只在一个 task 内改，无并发冲突）：**

| 文件 | task | 责任 |
|---|---|---|
| `hooks/lib/memory_config.py` | A1 | 加 `read_rating_mode` / `rating_mode_configured` / `read_brief_verbosity` 三个 reader（flat dot-key）|
| `hooks/lib/step_completeness.py` | A2 | `check_step`/`run_check` 加 `rating_mode` 形参；`parse_steps` 补 header 内联 `status:` 解析 |
| `hooks/stop-check.py` | A3 | 按 `rating.mode` 降级半残检测：model-only 跳过、user-opt-in 软提醒不阻塞、user-required 现行 |
| `hooks/session-start-brief.py` | B1 | ① 首次（无 `rating.mode` 键）注入一次性 `<kdev-memory-rating-setup>`（marker 去重）② `brief.verbosity` 三档（compact 写 `brief-detail.md`）③ 给 `_step_hint` 传 `rating_mode` |
| `skills/kdev-memory/SKILL.md` | A4 | §"Step 完成硬闸门"动作链按 `rating.mode` 三分支重写 |
| `skills/kdev-memory/references/六类记录-schema.md` | A4 | 注明 model-only 下用户评分段留空 + voided-faded 标准做法 |
| `hooks/lib/migrate_void_faded.py`（新建）| A5 | 一次性幂等迁移：Q-002 后半残 Step 批量盖 `status: voided-faded` + 销账注释 |
| `agents/kdev-step-recorder.md` | B2 | ① model-only 下 Step 模板带 `status: voided-faded` + 留空用户评分段 ② Return format 砍 APPENDED_BLOCK，只回一行 + 极简审计字段 |
| `.claude-plugin/plugin.json` | 收尾 | version 0.14.0 → 0.15.0 |
| `CHANGELOG.md` | 收尾 | 0.15.0 条目 |

**新建测试：**
- `tests/test_rating_mode_config.py`（A1）
- `tests/test_brief_verbosity.py`（B1，含 rating-setup 一次性注入）
- `tests/test_stop_check.py`（A3，rating-mode 降级）
- `tests/test_migrate_void_faded.py`（A5）

**更新测试：**
- `tests/test_step_completeness.py`（A2，加 rating_mode 行为 + 内联 status 解析）

**项目侧产物（收尾，由编排主控执行 + 验证，非 subagent）：**
- `.kdev/memory/config.yaml` 加 `rating.mode: model-only`（必做）+ `brief.verbosity: compact`（可选，用户定）
- 在真实 `.kdev/memory/执行日志.md` 上跑迁移脚本（幂等）
- roadmap `docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md` §1.5.1 + 行 45 回写 P-C0.5 ✅ / P-C1a ✅

**依赖顺序：** A1 →（A2 独立）→ A3、B1 依赖 A1（读 config）+ A2（传 rating_mode）；A5 依赖 A2（check_step rating_mode + 内联 status）；A4、B2 文档可任意时点；收尾在全部之后。

---

## Task A1: memory_config 加三个 config reader

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/memory_config.py`
- Test: `plugins/kdev-memory/tests/test_rating_mode_config.py`（新建）

- [ ] **Step 1: 写失败测试**

新建 `plugins/kdev-memory/tests/test_rating_mode_config.py`：

```python
"""memory_config 评分模式 + brief verbosity reader 单测（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "memory_config.py"
_spec = importlib.util.spec_from_file_location("memory_config", _PATH)
assert _spec and _spec.loader
memory_config = importlib.util.module_from_spec(_spec)
sys.modules["memory_config"] = memory_config
_spec.loader.exec_module(memory_config)


def _write_config(tmp_path: Path, text: str) -> Path:
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True)
    (kdev / "config.yaml").write_text(text, encoding="utf-8")
    return kdev


def test_rating_mode_default_when_no_config(tmp_path):
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True)
    assert memory_config.read_rating_mode(kdev) == "user-opt-in"


def test_rating_mode_flat_dot_key(tmp_path):
    kdev = _write_config(tmp_path, "rating.mode: model-only\n")
    assert memory_config.read_rating_mode(kdev) == "model-only"


def test_rating_mode_nested_form(tmp_path):
    kdev = _write_config(tmp_path, "rating:\n  mode: user-required\n")
    assert memory_config.read_rating_mode(kdev) == "user-required"


def test_rating_mode_underscore_form(tmp_path):
    kdev = _write_config(tmp_path, "rating_mode: model-only\n")
    assert memory_config.read_rating_mode(kdev) == "model-only"


def test_rating_mode_invalid_falls_back_to_default(tmp_path):
    kdev = _write_config(tmp_path, "rating.mode: bogus\n")
    assert memory_config.read_rating_mode(kdev) == "user-opt-in"


def test_rating_mode_configured_true_false(tmp_path):
    kdev_no = tmp_path / "a" / ".kdev" / "memory"
    kdev_no.mkdir(parents=True)
    (kdev_no / "config.yaml").write_text("record_mode: hybrid\n", encoding="utf-8")
    assert memory_config.rating_mode_configured(kdev_no) is False

    kdev_yes = _write_config(tmp_path, "rating.mode: model-only\n")
    assert memory_config.rating_mode_configured(kdev_yes) is True


def test_brief_verbosity_default_and_values(tmp_path):
    kdev = tmp_path / ".kdev" / "memory"
    kdev.mkdir(parents=True)
    assert memory_config.read_brief_verbosity(kdev) == "normal"

    kdev2 = _write_config(tmp_path, "brief.verbosity: compact\n")
    assert memory_config.read_brief_verbosity(kdev2) == "compact"


def test_brief_verbosity_invalid_falls_back(tmp_path):
    kdev = _write_config(tmp_path, "brief.verbosity: loud\n")
    assert memory_config.read_brief_verbosity(kdev) == "normal"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_rating_mode_config.py -q`
Expected: FAIL — `AttributeError: module 'memory_config' has no attribute 'read_rating_mode'`

- [ ] **Step 3: 实现三个 reader**

在 `memory_config.py` 顶部 type alias 区（`VALID_DISTILL_MODES` 之后）加：

```python
RatingMode = Literal["model-only", "user-opt-in", "user-required"]
VALID_RATING_MODES: tuple[RatingMode, ...] = ("model-only", "user-opt-in", "user-required")
DEFAULT_RATING_MODE: RatingMode = "user-opt-in"

BriefVerbosity = Literal["compact", "normal", "verbose"]
VALID_BRIEF_VERBOSITY: tuple[BriefVerbosity, ...] = ("compact", "normal", "verbose")
DEFAULT_BRIEF_VERBOSITY: BriefVerbosity = "normal"
```

在 `read_distill_mode` 之后加三个函数：

```python
def read_rating_mode(kdev_dir: Path | str = ".kdev/memory") -> RatingMode:
    """读 rating.mode 字段。未配置 / 非法值 → user-opt-in（插件默认，温和）。

    承 Q-002：本项目 config 写 `rating.mode: model-only`（机读化"用户不再评分"决策）。
    兼容 flat dot-key（`rating.mode`）、嵌套（`rating:` + `mode:`）、下划线（`rating_mode`）。
    """
    config = _read_config(kdev_dir)
    value = (config.get("rating.mode") or config.get("rating_mode") or "").lower()
    if value in VALID_RATING_MODES:
        return value  # type: ignore[return-value]
    return DEFAULT_RATING_MODE


def rating_mode_configured(kdev_dir: Path | str = ".kdev/memory") -> bool:
    """config 是否显式写了 rating.mode 键（用于 brief 首次提示判断）。"""
    config = _read_config(kdev_dir)
    return ("rating.mode" in config) or ("rating_mode" in config)


def read_brief_verbosity(kdev_dir: Path | str = ".kdev/memory") -> BriefVerbosity:
    """读 brief.verbosity 字段。未配置 / 非法值 → normal（现行行为）。

    compact 只注入 WARN + pending_decisions + 今日进度一行，其余写 brief-detail.md；
    verbose 全量（不截断半残清单）。
    """
    config = _read_config(kdev_dir)
    value = (config.get("brief.verbosity") or config.get("brief_verbosity") or "").lower()
    if value in VALID_BRIEF_VERBOSITY:
        return value  # type: ignore[return-value]
    return DEFAULT_BRIEF_VERBOSITY
```

同时把 `main()` 的 `--all` 输出补上新字段（保持 CLI 自洽）：在 `out` dict 里加
`"rating_mode": read_rating_mode(kdev), "brief_verbosity": read_brief_verbosity(kdev),`。

- [ ] **Step 4: 跑测试确认通过 + 不回归**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_rating_mode_config.py -q && python3 -m pytest tests/ -q`
Expected: 新测试全 PASS；全量仍 ≥ 291 passed（+ 新增的 8 条）

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/memory_config.py plugins/kdev-memory/tests/test_rating_mode_config.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): config 加 rating.mode + brief.verbosity reader (flat dot-key)"
```

---

## Task A2: step_completeness 加 rating_mode 形参 + header 内联 status 解析

**Files:**
- Modify: `plugins/kdev-memory/hooks/lib/step_completeness.py`
- Test: `plugins/kdev-memory/tests/test_step_completeness.py`（追加）

**背景（必读）：** 当前 `parse_steps` 只从 `---`...`---` 围栏块读 `status:`，但真实日志里 Step 1/2/3 的 `status: voided-faded` 是写在 `## Step` 行下方的 header 伪 frontmatter（无围栏），**从未被解析**——这是 latent bug，也是迁移脚本盖的章要生效的前提。本 task 补内联解析；并给 `check_step`/`run_check` 加 `rating_mode` 形参（默认 `user-required` 保现状）。

- [ ] **Step 1: 写失败测试**

在 `tests/test_step_completeness.py` 末尾追加（沿用文件已用的 `step_completeness` 模块对象）：

```python
# ---------------------------------------------------------------------------
# P-C0.5: rating_mode 形参 + header 内联 status 解析
# ---------------------------------------------------------------------------

_RM_LOG = """# 执行日志

## Step main-30: 用户评分空但模型自评齐全
日期：2026-06-11

### 模型自评
- 顺畅度自评：4/5
- 扣分项：赶工漏一个边界

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""


def test_user_required_reports_empty_user_score():
    steps = step_completeness.parse_steps(_RM_LOG)
    issues = step_completeness.check_step(steps[0], rating_mode="user-required")
    assert any("用户评分段" in i for i in issues)


def test_model_only_exempts_empty_user_score():
    steps = step_completeness.parse_steps(_RM_LOG)
    issues = step_completeness.check_step(steps[0], rating_mode="model-only")
    assert issues == []


def test_user_opt_in_exempts_empty_user_score():
    steps = step_completeness.parse_steps(_RM_LOG)
    issues = step_completeness.check_step(steps[0], rating_mode="user-opt-in")
    assert issues == []


def test_deduction_still_checked_in_model_only():
    """扣分项缺失在所有模式都算半残（防讨好式满分，与评分模式无关）。"""
    log = """## Step main-31: 扣分项空
日期：2026-06-11

### 模型自评
- 顺畅度自评：5/5
- 扣分项：—

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""
    step = step_completeness.parse_steps(log)[0]
    issues = step_completeness.check_step(step, rating_mode="model-only")
    assert any("扣分项" in i for i in issues)


def test_run_check_threads_rating_mode():
    import tempfile
    from pathlib import Path
    d = Path(tempfile.mkdtemp())
    p = d / "执行日志.md"
    p.write_text(_RM_LOG, encoding="utf-8")
    assert step_completeness.run_check(p, "2026-06-11", rating_mode="user-required")["status"] == "has_half_complete"
    assert step_completeness.run_check(p, "2026-06-11", rating_mode="model-only")["status"] == "ok"


def test_default_rating_mode_is_user_required():
    """不传 rating_mode 时保持现行严格行为（既有 11 测试文件不被波及的保证）。"""
    steps = step_completeness.parse_steps(_RM_LOG)
    assert any("用户评分段" in i for i in step_completeness.check_step(steps[0]))


def test_inline_header_status_voided_is_parsed():
    """header 伪 frontmatter 里的内联 `status: voided-faded`（无 --- 围栏）应被解析并跳过。"""
    log = """## Step main-32: 内联 status 销账
status: voided-faded   # 半残销账 2026-06-11
日期：2026-06-11

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""
    steps = step_completeness.parse_steps(log)
    assert steps[0]["status"] == "voided-faded"
    # user-required 下也应跳过（status 优先级高于字段检查）
    assert step_completeness.check_step(steps[0], rating_mode="user-required") == []


def test_inline_status_with_trailing_comment_token():
    """`status: voided-faded   # 注释` 应只取第一个非空 token。"""
    log = "## Step main-33: x\nstatus: voided-faded   # note\n日期：2026-06-11\n"
    assert step_completeness.parse_steps(log)[0]["status"] == "voided-faded"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_step_completeness.py -q`
Expected: FAIL — `check_step() got an unexpected keyword argument 'rating_mode'` + 内联 status 断言失败

- [ ] **Step 3: 实现 — parse_steps 内联 status + check_step/run_check rating_mode**

(3a) 在 `step_completeness.py` 加内联 status 解析 helper（放在 `parse_steps` 之前）：

```python
def _extract_inline_status(body: str) -> str | None:
    """读 Step header 伪 frontmatter 里的内联 `status:`（`## Step` 行下方、首个空行/###/> 之前）。

    真实日志的 status 多写在 header（无 --- 围栏），历史上未被解析——本函数补这个口子。
    只取冒号后第一个非空 token（容忍行尾 `# 注释`）。
    """
    lines = body.splitlines()
    for line in lines[1:]:  # lines[0] 是 "## Step ..." 标题行
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">"):
            break
        m = re.match(r"^status\s*:\s*(\S+)", s)
        if m:
            return m.group(1).strip()
    return None
```

(3b) 在 `parse_steps` 里，`entry_status` 计算处改为围栏优先、内联兜底：

把现有：
```python
        entry_status = None
        if status_m:
            fm_text = status_m.group(1)
            sf = re.search(r"^\s*status\s*:\s*(\S+)", fm_text, re.MULTILINE)
            if sf:
                entry_status = sf.group(1).strip()
```
改为：
```python
        entry_status = None
        if status_m:
            fm_text = status_m.group(1)
            sf = re.search(r"^\s*status\s*:\s*(\S+)", fm_text, re.MULTILINE)
            if sf:
                entry_status = sf.group(1).strip()
        if entry_status is None:
            entry_status = _extract_inline_status(body)
```

(3c) `check_step` 加 `rating_mode` 形参，把"用户评分段"整块用 `user-required` 守卫（扣分项检查保持无条件）：

把签名 `def check_step(step: dict[str, Any]) -> list[str]:` 改为
`def check_step(step: dict[str, Any], rating_mode: str = "user-required") -> list[str]:`

把"# 1. 用户评分段"那一整块（从 `user_section = _extract_section(...)` 到 `issues.append("有模型自评段但无用户评分段（Step 未完整闭环）")` 结束）整体包进：
```python
    # 1. 用户评分段（仅 user-required 模式检查；model-only / user-opt-in 视空为正常）
    if rating_mode == "user-required":
        user_section = _extract_section(body, "### 用户评分") or _extract_section(body, "## 用户评分")
        if user_section is not None:
            ts = _extract_field(user_section, "完成时间")
            score = _extract_field(user_section, "顺畅度")
            if ts is None or _is_placeholder(ts):
                issues.append(f"用户评分段「完成时间」为 {_describe_placeholder(ts)}")
            if score is None or _is_placeholder(score):
                issues.append(f"用户评分段「顺畅度」为 {_describe_placeholder(score)}")
        elif (
            "## 用户评分" not in body
            and "### 用户评分" not in body
            and _has_model_self_review(body)
        ):
            issues.append("有模型自评段但无用户评分段（Step 未完整闭环）")
```
"# 2. 模型自评段的扣分项" 块**保持原样无条件执行**（所有模式都查扣分项）。

(3d) `run_check` 加 `rating_mode` 形参并透传：

签名 `def run_check(log_path: Path, today: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> dict[str, Any]:`
改为 `def run_check(log_path: Path, today: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS, rating_mode: str = "user-required") -> dict[str, Any]:`
循环里 `issues = check_step(step)` 改为 `issues = check_step(step, rating_mode=rating_mode)`。

- [ ] **Step 4: 跑测试确认通过 + 不回归**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_step_completeness.py tests/test_step_completeness_voided.py -q && python3 -m pytest tests/ -q`
Expected: 全 PASS（既有 voided/字段测试不受影响，因默认 rating_mode=user-required）；全量绿

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/step_completeness.py plugins/kdev-memory/tests/test_step_completeness.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): step_completeness 加 rating_mode 形参 + header 内联 status 解析"
```

---

## Task A3: stop-check 按 rating.mode 降级半残检测

**Files:**
- Modify: `plugins/kdev-memory/hooks/stop-check.py`
- Test: `plugins/kdev-memory/tests/test_stop_check.py`（新建）

**目标行为（spec §3.2 + §4.3）：**
| `rating.mode` | stop-check 半残行为 |
|---|---|
| `model-only` | **跳过半残检测**（不软提醒、不阻塞）；只查汇总/跨期 |
| `user-opt-in` | 半残只软提醒（stdout），**永不**strict 阻塞 |
| `user-required` | 现行（soft + strict 阻塞）|

- [ ] **Step 1: 写失败测试**

新建 `plugins/kdev-memory/tests/test_stop_check.py`：

```python
"""test stop-check.py 按 rating.mode 降级半残检测（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "stop-check.py"

# 今日半残 Step（用户评分空 + 扣分项齐全）；日期占位 __TODAY__ 运行时替换
_HALF_STEP = """# 执行日志

## Step main-40: 今日半残
日期：__TODAY__

### 模型自评
- 顺畅度自评：4/5
- 扣分项：赶工漏边界

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""


def _setup(tmp_path: Path, rating_line: str | None, strict: bool) -> Path:
    import datetime
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    mem = repo / ".kdev" / "memory"
    (mem / "state").mkdir(parents=True)
    today = datetime.date.today().isoformat()
    (mem / "执行日志.md").write_text(_HALF_STEP.replace("__TODAY__", today), encoding="utf-8")
    # 今日汇总写上，避免 "今天无汇总" 噪声干扰断言
    (mem / "每日汇总").mkdir()
    (mem / "每日汇总" / f"{today}.md").write_text("# 汇总\n", encoding="utf-8")
    if rating_line is not None:
        (mem / "config.yaml").write_text(rating_line + "\n", encoding="utf-8")
    if strict:
        (mem / "strict").write_text("", encoding="utf-8")
    return repo


def _run(repo: Path) -> tuple[int, str]:
    r = subprocess.run([sys.executable, str(HOOK)], cwd=str(repo),
                       input="{}", capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def test_model_only_skips_half_reminder(tmp_path):
    repo = _setup(tmp_path, "rating.mode: model-only", strict=False)
    rc, out = _run(repo)
    assert rc == 0
    assert "半残" not in out


def test_user_required_soft_reminds_half(tmp_path):
    repo = _setup(tmp_path, "rating.mode: user-required", strict=False)
    rc, out = _run(repo)
    assert rc == 0
    assert "半残" in out


def test_user_opt_in_no_strict_block(tmp_path):
    """user-opt-in + strict flag：半残不得 exit 2 阻塞。"""
    repo = _setup(tmp_path, "rating.mode: user-opt-in", strict=True)
    rc, _ = _run(repo)
    assert rc == 0


def test_model_only_no_strict_block(tmp_path):
    repo = _setup(tmp_path, "rating.mode: model-only", strict=True)
    rc, _ = _run(repo)
    assert rc == 0


def test_user_required_strict_blocks_half(tmp_path):
    """user-required + strict + 今日半残 → exit 2 阻塞（现行行为保留）。"""
    repo = _setup(tmp_path, "rating.mode: user-required", strict=True)
    rc, out = _run(repo)
    assert rc == 2
    assert "strict" in out
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_stop_check.py -q`
Expected: FAIL — model-only 仍输出半残提醒 / user-opt-in 仍 exit 2（当前无 rating.mode 分支）

- [ ] **Step 3: 实现降级逻辑**

(3a) `stop-check.py` 顶部 import 区（`from scope import shared_dir` 行下方）加：
```python
from memory_config import read_rating_mode  # noqa: E402
```

(3b) `_step_completeness_scan` 加 `rating_mode` 形参并透传 `run_check`：

签名 `def _step_completeness_scan(log_path: Path, today: str) -> Tuple[int, str]:`
改为 `def _step_completeness_scan(log_path: Path, today: str, rating_mode: str) -> Tuple[int, str]:`
其中 `result = mod.run_check(log_path, today)` 改为 `result = mod.run_check(log_path, today, rating_mode=rating_mode)`。

(3c) `main()` 在 `today = date.today().isoformat()` 之后读模式：
```python
    rating_mode = read_rating_mode(kdev_dir)
```

(3d) "# 7. Step 完整度扫描" 块按模式降级：

把：
```python
    # 7. Step 完整度扫描
    step_today_half, step_hint = _step_completeness_scan(log_file, today)
    if step_hint:
        reminders.append(step_hint)
```
改为：
```python
    # 7. Step 完整度扫描（按 rating.mode 降级）
    #   model-only：完全跳过半残检测；user-opt-in / user-required：照扫
    if rating_mode == "model-only":
        step_today_half, step_hint = 0, ""
    else:
        step_today_half, step_hint = _step_completeness_scan(log_file, today, rating_mode)
        if step_hint:
            reminders.append(step_hint)
```

(3e) strict 半残阻塞块只在 user-required 下触发。把：
```python
    if not stop_hook_active and strict_flag and step_today_half > 0:
```
改为：
```python
    if not stop_hook_active and strict_flag and step_today_half > 0 and rating_mode == "user-required":
```
（"执行日志今天空"的 strict 阻塞块不动——与评分模式无关。）

- [ ] **Step 4: 跑测试确认通过 + 不回归**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_stop_check.py tests/test_stop_check_pending.py -q && python3 -m pytest tests/ -q`
Expected: 全 PASS；全量绿

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/stop-check.py plugins/kdev-memory/tests/test_stop_check.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): stop-check 按 rating.mode 降级半残检测"
```

---

## Task B1: session-start-brief — 首次评分提示 + verbosity 三档

**Files:**
- Modify: `plugins/kdev-memory/hooks/session-start-brief.py`
- Test: `plugins/kdev-memory/tests/test_brief_verbosity.py`（新建）

**⚠️ 本文件一次性做完两件事（spec §3.4 + §4.1），别分两轮：**
1. **首次提示**：config 无 `rating.mode` 键 + 无 marker → brief 追加一次性 `<kdev-memory-rating-setup>`，并写 marker `state/.rating-setup-shown` 去重。
2. **verbosity 三档**：`compact` 只注入 WARN + pending_decisions + 今日进度一行，其余写 `.kdev/memory/brief-detail.md`；`normal` 现行；`verbose` 全量（半残清单不截断）。
3. 顺带给 `_step_hint` 传 `rating_mode`（model-only 下半残不进 brief）。

- [ ] **Step 1: 写失败测试**

新建 `plugins/kdev-memory/tests/test_brief_verbosity.py`：

```python
"""test session-start-brief：rating-setup 一次性提示 + brief.verbosity 三档（P-C0.5 / P-C1a）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-start-brief.py"


def _init(tmp_path: Path, config_text: str | None = None) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "init"],
        cwd=repo, check=True,
    )
    mem = repo / ".kdev" / "memory"
    (mem / "state").mkdir(parents=True)
    (mem / "执行日志.md").write_text("# 执行日志\n", encoding="utf-8")
    (mem / "当前状态.md").write_text(
        "---\nphase: t\npending_decisions: [开 P-X]\n---\n", encoding="utf-8")
    if config_text is not None:
        (mem / "config.yaml").write_text(config_text, encoding="utf-8")
    return repo


def _ctx(repo: Path) -> str:
    r = subprocess.run([sys.executable, str(HOOK)], cwd=str(repo),
                       input=json.dumps({"source": "startup"}),
                       capture_output=True, text=True)
    out = json.loads(r.stdout) if r.stdout.strip() else {}
    return out.get("hookSpecificOutput", {}).get("additionalContext", "")


def test_rating_setup_prompt_shown_once_when_unconfigured(tmp_path):
    repo = _init(tmp_path, config_text=None)  # 无 rating.mode 键
    first = _ctx(repo)
    assert "<kdev-memory-rating-setup>" in first
    assert (repo / ".kdev" / "memory" / "state" / ".rating-setup-shown").is_file()
    # 第二次不再出现（marker 去重）
    second = _ctx(repo)
    assert "<kdev-memory-rating-setup>" not in second


def test_rating_setup_prompt_absent_when_configured(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\n")
    assert "<kdev-memory-rating-setup>" not in _ctx(repo)


def test_verbosity_compact_writes_detail_and_trims(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: compact\n")
    ctx = _ctx(repo)
    # compact：含今日进度 + pending_decisions + brief-detail 指针；不含"最近条目"全量块
    assert "brief-detail.md" in ctx
    assert "pending_decisions" in ctx or "开 P-X" in ctx
    assert "📝 **最近条目**" not in ctx
    assert (repo / ".kdev" / "memory" / "brief-detail.md").is_file()
    detail = (repo / ".kdev" / "memory" / "brief-detail.md").read_text(encoding="utf-8")
    assert "今日进度" in detail


def test_verbosity_normal_is_full(tmp_path):
    repo = _init(tmp_path, config_text="rating.mode: model-only\nbrief.verbosity: normal\n")
    ctx = _ctx(repo)
    assert "📊 **今日进度**" in ctx
    assert "brief-detail.md" not in ctx
    assert not (repo / ".kdev" / "memory" / "brief-detail.md").is_file()
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_brief_verbosity.py -q`
Expected: FAIL — 无 `<kdev-memory-rating-setup>` 注入 / compact 未写 brief-detail.md

- [ ] **Step 3a: import + 读 config**

`session-start-brief.py` 顶部 import 区（`from scope import ...` 行下方）加：
```python
from memory_config import read_rating_mode, rating_mode_configured, read_brief_verbosity  # noqa: E402
```

`main()` 里 `shared = shared_dir(kdev_dir)` 之后加：
```python
    rating_mode = read_rating_mode(kdev_dir)
    verbosity = read_brief_verbosity(kdev_dir)
    rating_setup_hint = _rating_setup_hint(kdev_dir)
```

`_step_hint(log_file, today)` 调用改为透传 rating_mode（见 3c）。

- [ ] **Step 3b: rating-setup 一次性提示 helper**

在 `_step_hint` 函数之后加：
```python
def _rating_setup_hint(kdev_dir: Path) -> str:
    """首次（config 无 rating.mode 键、且未提示过）→ 返回一次性评分模式设置提示。

    用 state/.rating-setup-shown marker 去重，保证"一次性"。已配置或已提示过 → 空串。
    """
    if rating_mode_configured(kdev_dir):
        return ""
    marker = kdev_dir / "state" / ".rating-setup-shown"
    if marker.is_file():
        return ""
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("", encoding="utf-8")
    except OSError:
        pass
    return (
        "<kdev-memory-rating-setup>\n"
        "kdev-memory 评分模式可配置。当前默认 user-opt-in（自评后轻提一句，不回应就过）。\n"
        "• 说\"关掉评分\"→ model-only（只模型自评，零追问）\n"
        "• 说\"严格评分\"→ user-required（每 Step 必追问）\n"
        "• 随时一句话切换，Claude 改 config.yaml 立即生效。\n"
        "</kdev-memory-rating-setup>"
    )
```

- [ ] **Step 3c: _step_hint 传 rating_mode + verbose 不截断**

`_step_hint` 签名改为：
```python
def _step_hint(log_file: Path, today: str, rating_mode: str = "user-required", max_list: int = 5) -> str:
```
内部 `result = mod.run_check(log_file, today)` 改为
`result = mod.run_check(log_file, today, rating_mode=rating_mode)`；
`return mod.format_hint_for_brief(result) or ""` 改为
`return mod.format_hint_for_brief(result, max_list=max_list) or ""`。

`main()` 里 `step_hint = _step_hint(log_file, today)` 改为：
```python
    step_hint = _step_hint(log_file, today, rating_mode=rating_mode,
                           max_list=999 if verbosity == "verbose" else 5)
```

- [ ] **Step 3d: _build_brief 接 rating_setup_hint + verbosity；compact 分支**

`_build_brief` 签名末尾加两个形参：`rating_setup_hint: str = "", verbosity: str = "normal"`。

在 startup/clear/default 分支（`else:` 块）**最前面**（`parts.append(f"项目有 .kdev/ 工程记忆...")` 之前）加 compact 早退：
```python
        if verbosity == "compact":
            cparts: List[str] = [f"项目有 .kdev/ 工程记忆（brief.verbosity=compact）。当前（{today}）："]
            for w in warn_files:
                cparts.append(f"🔴 {w}")
            if step_hint and "今日" in step_hint:
                cparts.append("🔴 " + step_hint)
            if state_pending:
                cparts.append(f"- pending_decisions: {state_pending}")
            prog_one = f"📊 今日进度：执行日志 {log_today}；汇总 {summary_today_status}"
            if git_branch:
                prog_one += f"；分支 {git_branch}"
            cparts.append(prog_one)
            cparts.append("🗂 完整 brief（项目状态/最近条目/半残/distill/promote）已写入 "
                          ".kdev/memory/brief-detail.md，按需 Read。")
            if rating_setup_hint:
                cparts.append("\n" + rating_setup_hint)
            return "\n".join(cparts)
```

在该 `else` 分支**末尾**（现有 `parts.append("\n💡 **建议**...")` 之后）加 rating_setup_hint 追加：
```python
        if rating_setup_hint:
            parts.append("\n" + rating_setup_hint)
```
同理在 `resume` 与 `compact`(source) 两个分支末尾也各加同样三行（首次提示在任何 source 都该露出一次）。

- [ ] **Step 3e: main() 写 brief-detail.md + 传参**

`_build_brief(...)` 调用补两个实参 `rating_setup_hint=rating_setup_hint, verbosity=verbosity`。

紧接 `brief = _build_brief(...)` 之后、`if not brief.strip():` 之前，加 compact 落盘：
```python
    if verbosity == "compact" and source in ("startup", "clear", "default", ""):
        # 把"全量 normal brief"写盘供主动查阅（compact 注入的是裁剪版）
        detail = _build_brief(
            mode="startup", today=today, git_branch=git_branch, warn_files=warn_files,
            checkpoint_files=checkpoint_files, log_today=log_today,
            summary_today_status=summary_today_status, missing_past=missing_past,
            drift_hint=drift_hint, step_hint=step_hint, promote_hint=promote_hint,
            distill_hint=distill_hint, state_phase=state_phase, state_iter=state_iter,
            state_step=state_step, state_last=state_last, state_pending=state_pending,
            state_unresolved=state_unresolved, recent_step=recent_step, recent_q=recent_q,
            recent_g=recent_g, pending_hint=pending_hint or "", skill_drift_hint=skill_drift_hint,
            staff_block=staff_block, rating_setup_hint="", verbosity="normal",
        )
        try:
            (kdev_dir / "brief-detail.md").write_text(
                f"# kdev-memory brief-detail（{today} 全量）\n\n{detail}\n", encoding="utf-8")
        except OSError:
            pass
```

- [ ] **Step 4: 跑测试确认通过 + 不回归**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_brief_verbosity.py tests/test_session_start_brief_prefix.py tests/test_session_start_brief_scope.py -q && python3 -m pytest tests/ -q`
Expected: 全 PASS（现有 brief 前缀/scope 测试不受影响，因默认 verbosity=normal + 它们无 config.yaml→rating 默认会注入 setup 提示，但那些测试只断言"含 main- 前缀"/"含 pending"，不排斥额外块，故仍绿）；全量绿

> ⚠️ 自检：`test_session_start_brief_prefix.py` 的 repo 无 config.yaml → 会触发 rating-setup 提示注入。确认那些断言都是 `assert X in ctx` 而非 `==`，不会因多出 setup 块而失败（已核对：全是 `in`）。

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/session-start-brief.py plugins/kdev-memory/tests/test_brief_verbosity.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): brief 首次评分提示 + brief.verbosity 三档(compact 写 brief-detail.md)"
```

---

## Task A4: SKILL.md 动作链三分支重写 + schema 注明 model-only 留空

**Files:**
- Modify: `plugins/kdev-memory/skills/kdev-memory/SKILL.md`（§"Step 完成硬闸门"动作链）
- Modify: `plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md`（用户评分段后）

纯文档，无自动测试。改完用 `grep` 自检关键字在场。

- [ ] **Step 1: SKILL.md 重写动作链**

把 SKILL.md 现有"### 动作链（每步完成后的强制流程）"到"**严禁**：默默把 Step 当\"完成\"过了..."整段（约 94–114 行）替换为：

````markdown
### 动作链（按 `rating.mode` 三分支）

评分模式由 `.kdev/memory/config.yaml` 的 **`rating.mode`**（flat dot-key 单层）决定：
`model-only` | `user-opt-in`（插件默认）| `user-required`。**一句话即时切换**——用户说"关掉评分"→ 写 `rating.mode: model-only`；"严格评分"→ `user-required`。

**三档共性（与模式无关）**：执行事实段 + 模型自评段必填，**模型自评扣分项所有模式都必填**（防讨好式满分）。

**`user-required`（现行硬闸门）**
```
模型做完一步 → 写执行事实段 + 模型自评段（含扣分项）
            → 【公布自评分给用户】→【主动追问用户评分】
            → 用户回答后填用户评分段 + 锁定两段时分戳 → 生成评分差异分析段 → Step 完成
```

**`user-opt-in`（插件默认，温和）**
```
模型做完一步 → 写执行事实段 + 模型自评段（含扣分项）→ 公布自评分
            → 轻提一句"如要补用户评分随时说"，不追问、不等待
            → 用户不回应即 Step 完成（用户评分段留空不算半残）
```

**`model-only`（= 本项目 Q-002 机读化，零追问）**
```
模型做完一步 → 写执行事实段 + 模型自评段（含扣分项）
            → 用户评分段留空 `—` 骨架 + 标 status: voided-faded + 销账注释
            → 直接 Step 完成（不公布、不追问）
```
⚠️ **model-only 绝不把自评分拷进用户评分段**——那是伪造用户评分，污染下游 misalignment 数据。
用户评分段保留 `—` 骨架，用户随时主动给分 → 当场回填 + 改 `status: scored` 恢复闭环。

### 用户临时说"跳过评分直接下一步"（仅 user-required 模式）

若处于 `user-required` 且用户一次性说"先别采集评分，开下一步"——这是**开 R-NNN 销账**的情形：
- Step 末尾追加 `> 半残销账：用户明确要求跳过评分，YYYY-MM-DD`
- 改进建议.md 开 R-NNN 记录这次半残事件

（长期不想评分 → 直接切 `rating.mode: model-only`，无需每次 R-NNN。）

**严禁**：在 user-required 下默默把 Step 当"完成"过了（"模型写完自评就认为 Step 完成"是反模式）。
````

（其下 iter-7 eval 注脚那段 `> iter-7 discriminating eval...` 保留不动。）

- [ ] **Step 2: 六类记录-schema.md 注明 model-only 留空做法**

在 schema 文件"### 用户评分"示例代码块闭合 ```` ``` ```` 之后、"### about 字段（subject 归属）"之前，插入新小节：

````markdown
### model-only 下的用户评分段（rating.mode）

当 `.kdev/memory/config.yaml` 设 `rating.mode: model-only`（机读化 Q-002）时，用户评分段**留空骨架 + 标销账**，**绝不拷自评分伪填**（伪填 = 假用户评分，污染 misalignment 切片）：

```markdown
## Step <id>: <title>
status: voided-faded   # 半残销账：rating.mode=model-only（承 Q-002），用户评分段不主动采集
...
### 用户评分
- 完成时间：—
- 顺畅度：—/5
- 用户评价：
> 半残销账：rating.mode=model-only（承 Q-002），用户评分段保留骨架不主动采集

### 评分差异分析
- n/a（model-only 跳过用户评分）
```

Step header 内联 `status: voided-faded` 即让 `step_completeness` 跳过欠评扫描（v0.15+ 起内联 status 也被解析）。`user-opt-in` 同样不追问，但**不**盖 voided（用户随时可填）；`model-only`/`user-opt-in` 下"用户评分段空"由 hook 读 `rating.mode` 豁免，不算半残。
````

- [ ] **Step 3: 自检关键字在场**

Run:
```bash
cd plugins/kdev-memory
grep -q "rating.mode" skills/kdev-memory/SKILL.md && \
grep -q "model-only（= 本项目 Q-002" skills/kdev-memory/SKILL.md && \
grep -q "绝不把自评分拷进用户评分段" skills/kdev-memory/SKILL.md && \
grep -q "model-only 下的用户评分段" skills/kdev-memory/references/六类记录-schema.md && \
echo "OK: SKILL + schema 关键字齐全"
```
Expected: `OK: SKILL + schema 关键字齐全`

- [ ] **Step 4: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/skills/kdev-memory/SKILL.md plugins/kdev-memory/skills/kdev-memory/references/六类记录-schema.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "docs(kdev-memory): 评分动作链按 rating.mode 三分支重写 + schema 注明 model-only 留空"
```

---

## Task A5: 一次性幂等迁移脚本 — Q-002 后半残 Step 批量销账

**Files:**
- Create: `plugins/kdev-memory/hooks/lib/migrate_void_faded.py`
- Test: `plugins/kdev-memory/tests/test_migrate_void_faded.py`（新建）

**逻辑：** 对 `date >= cutoff`（默认 `2026-05-27` = Q-002 拍板日）、**无 status**、且"仅因用户评分空才半残"（`check_step(user-required)` 非空 **AND** `check_step(model-only)` 空——排除扣分项缺失这类真问题）的 Step，在 `## Step` 标题行后插一行内联 `status: voided-faded   # 半残销账 ...`。幂等（已有 status → 跳过）。

- [ ] **Step 1: 写失败测试**

新建 `plugins/kdev-memory/tests/test_migrate_void_faded.py`：

```python
"""test migrate_void_faded：Q-002 后半残 Step 批量盖 voided-faded（幂等）。"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parents[1] / "hooks" / "lib" / "migrate_void_faded.py"
_spec = importlib.util.spec_from_file_location("migrate_void_faded", _PATH)
assert _spec and _spec.loader
mvf = importlib.util.module_from_spec(_spec)
sys.modules["migrate_void_faded"] = mvf
_spec.loader.exec_module(mvf)

CUTOFF = "2026-05-27"

_LOG = """# 执行日志

## Step main-10: Q-002 后半残（应盖章）
日期：2026-05-28

### 模型自评
- 顺畅度自评：4/5
- 扣分项：赶工

### 用户评分
- 完成时间：—
- 顺畅度：—/5

## Step 1: Q-002 前的半残（不动）
日期：2026-05-20

### 模型自评
- 顺畅度自评：4/5
- 扣分项：x

### 用户评分
- 完成时间：—
- 顺畅度：—/5

## Step main-11: 已 voided（幂等跳过）
status: voided-faded
日期：2026-05-29

### 用户评分
- 完成时间：—
- 顺畅度：—/5

## Step main-12: 真完整（不动）
日期：2026-05-30

### 模型自评
- 顺畅度自评：4/5
- 扣分项：x

### 用户评分
- 完成时间：2026-05-30 10:00
- 顺畅度：4/5
- 用户评价：OK

## Step main-13: 扣分项也空（真问题，不盖章）
日期：2026-05-31

### 模型自评
- 顺畅度自评：5/5
- 扣分项：—

### 用户评分
- 完成时间：—
- 顺畅度：—/5
"""


def test_stamps_only_post_cutoff_userscore_half():
    new_text, stamped = mvf.void_faded_backlog(_LOG, CUTOFF, "2026-06-11")
    assert stamped == ["Step main-10"]
    assert "## Step main-10: Q-002 后半残（应盖章）\nstatus: voided-faded" in new_text


def test_pre_cutoff_untouched():
    _, stamped = mvf.void_faded_backlog(_LOG, CUTOFF, "2026-06-11")
    assert "Step 1" not in stamped


def test_deduction_empty_not_stamped():
    _, stamped = mvf.void_faded_backlog(_LOG, CUTOFF, "2026-06-11")
    assert "Step main-13" not in stamped


def test_complete_step_not_stamped():
    _, stamped = mvf.void_faded_backlog(_LOG, CUTOFF, "2026-06-11")
    assert "Step main-12" not in stamped


def test_idempotent():
    once, s1 = mvf.void_faded_backlog(_LOG, CUTOFF, "2026-06-11")
    twice, s2 = mvf.void_faded_backlog(once, CUTOFF, "2026-06-11")
    assert s2 == []
    assert twice == once
```

- [ ] **Step 2: 跑测试确认失败**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_migrate_void_faded.py -q`
Expected: FAIL — `No module named 'migrate_void_faded'`

- [ ] **Step 3: 实现迁移脚本**

新建 `plugins/kdev-memory/hooks/lib/migrate_void_faded.py`：

```python
"""kdev-memory P-C0.5 一次性迁移：Q-002 后半残 Step 批量盖 `status: voided-faded`。

承接 Q-002（本项目 2026-05-27 拍板"用户不再评分"）。旧版无 rating.mode 机制时
recorder 写的 Step 用户评分段留 `—` 但没盖 status → step_completeness 一直当半残 nag。
本脚本对"仅因用户评分空才半残"（扣分项等真问题不动）的 post-cutoff Step 盖章销账。

幂等：已有 status（围栏或内联）的 Step 跳过；可反复跑。
只读写传入文本/文件，不碰其它 .kdev/memory/ 文件。

CLI: python3 migrate_void_faded.py [--log .kdev/memory/执行日志.md] [--cutoff 2026-05-27]
                                    [--today YYYY-MM-DD] [--apply]
默认 dry-run（打印将盖章的 Step）；--apply 才落盘。
"""

from __future__ import annotations

import argparse
import sys
from datetime import date as _date
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from step_completeness import parse_steps, check_step  # noqa: E402

DEFAULT_CUTOFF = "2026-05-27"  # Q-002 拍板日


def void_faded_backlog(log_text: str, cutoff_date: str, today: str) -> Tuple[str, List[str]]:
    """返回 (new_text, stamped_labels)。

    盖章条件（全满足）：
      - step.status is None（未盖过；幂等）
      - date >= cutoff_date
      - check_step(user-required) 非空 AND check_step(model-only) 空
        （即半残纯由用户评分空导致；扣分项等真问题保留 nag）
    """
    steps = parse_steps(log_text)
    text = log_text
    stamped: List[str] = []
    for step in steps:
        if step.get("status") is not None:
            continue
        d = step.get("date") or ""
        if d < cutoff_date:
            continue
        half_strict = check_step(step, rating_mode="user-required")
        half_model = check_step(step, rating_mode="model-only")
        if not (half_strict and not half_model):
            continue
        heading_line = step["body"].splitlines()[0]  # "## Step <label>: <title>"
        status_line = (
            f"status: voided-faded   # 半残销账 {today}: "
            f"rating.mode=model-only（承 Q-002，用户评分段保留骨架不主动采集）"
        )
        old = heading_line + "\n"
        new = heading_line + "\n" + status_line + "\n"
        if old in text:
            text = text.replace(old, new, 1)
            stamped.append(step["label"])
    return text, stamped


def main() -> int:
    parser = argparse.ArgumentParser(description="Q-002 后半残 Step 批量销账（幂等）")
    parser.add_argument("--log", default=".kdev/memory/执行日志.md")
    parser.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    parser.add_argument("--today", default=_date.today().isoformat())
    parser.add_argument("--apply", action="store_true", help="落盘（默认 dry-run 只打印）")
    args = parser.parse_args()

    log_path = Path(args.log)
    if not log_path.is_file():
        print(f"[migrate_void_faded] 找不到 {log_path}", file=sys.stderr)
        return 1
    text = log_path.read_text(encoding="utf-8")
    new_text, stamped = void_faded_backlog(text, args.cutoff, args.today)
    if not stamped:
        print("[migrate_void_faded] 无需盖章（已全部销账或无 post-cutoff 半残）")
        return 0
    print(f"[migrate_void_faded] {'已盖章' if args.apply else 'DRY-RUN 将盖章'} "
          f"{len(stamped)} 条：{', '.join(stamped)}")
    if args.apply:
        log_path.write_text(new_text, encoding="utf-8")
        print(f"[migrate_void_faded] 已写回 {log_path}")
    else:
        print("[migrate_void_faded] 这是 dry-run；加 --apply 落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 跑测试确认通过 + 不回归**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/test_migrate_void_faded.py -q && python3 -m pytest tests/ -q`
Expected: 全 PASS；全量绿

- [ ] **Step 5: Commit**

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/hooks/lib/migrate_void_faded.py plugins/kdev-memory/tests/test_migrate_void_faded.py
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): 加 Q-002 后半残 Step 批量销账迁移脚本(幂等)"
```

---

## Task B2: kdev-step-recorder agent — model-only 留空 + 输出精简

**Files:**
- Modify: `plugins/kdev-memory/agents/kdev-step-recorder.md`

纯 agent prompt，无自动测试（lib 级契约已被 `test_step_recorder_e2e.py` 覆盖，不变）。改两处：

- [ ] **Step 1: step 1 python 片段加读 rating.mode**

把 "Action sequence" 第 1 步的 python 片段里 `from scope import resolve_step_slug, recorder_target_log` 行下方加：
```python
from memory_config import read_rating_mode
```
并在 print 区加：
```python
print('RATING_MODE:', read_rating_mode())
```
正文补一句：`Capture RATING_MODE：决定用户评分段的写法（见 step 2）。`

- [ ] **Step 2: step 2 模板按 rating.mode 分支**

把 "2. Compose 4-section Step entry" 的模板块里"用户评分 + 评分差异分析"两段（现为固定 `—` + Q-002 注释）改为按 RATING_MODE 写：

````markdown
**用户评分段 + 评分差异分析段（按 RATING_MODE）**：

- `model-only`：在 `## Step <ID>` 标题行下方加内联 `status: voided-faded`，用户评分段留 `—` 骨架 + 销账注释，**绝不拷自评分**：
  ```markdown
  ## Step <ID>: <title>
  status: voided-faded   # 半残销账：rating.mode=model-only（承 Q-002），用户评分段不主动采集
  triggers: [...]
  日期：<today>
  about: <about value>
  ...（执行事实 + 模型自评同下）...
  ### 用户评分
  - 完成时间：—
  - 顺畅度：—/5
  - 用户评价：
  > 半残销账：rating.mode=model-only（承 Q-002），用户评分段保留骨架不主动采集
  ### 评分差异分析
  - n/a（model-only 跳过用户评分）
  ```
- `user-opt-in`：用户评分段留 `—` 骨架（**不**盖 status，用户随时可填），无销账注释；评分差异分析写 `- 待用户补分后生成`。
- `user-required`：用户评分段留 `—` 骨架（现行），主会话负责当场追问回填。
````

（执行事实段 + 模型自评段模板不变。）

- [ ] **Step 3: Return format 精简（砍 APPENDED_BLOCK）**

把 "## Return format" 的 "On success" 块替换为：
````markdown
On success（**只回一行确认 + 极简审计字段，不再回传 APPENDED_BLOCK 长文**——详细内容已写进 执行日志.md 文件本身）:
```
STATUS: DONE
MINTED_ID: Step main-NN
COUNTER: NN
SCOPE: <scope>
RATING_MODE: <model-only|user-opt-in|user-required>
TARGET: <执行日志 path appended to>
```
````
（"On reject" 块不动。）

并把 "## Constraints" 末尾加一条：
`- 返回精简：成功时只回上述 6 行审计字段，**不要**把写入的 4 段内容再贴回 stdout（主会话已知意图，详情在文件里）。`

- [ ] **Step 4: 自检 + Commit**

Run:
```bash
cd plugins/kdev-memory
grep -q "RATING_MODE" agents/kdev-step-recorder.md && \
! grep -q "APPENDED_BLOCK: |" agents/kdev-step-recorder.md && \
echo "OK: recorder 已读 rating.mode 且砍了 APPENDED_BLOCK"
```
Expected: `OK: recorder 已读 rating.mode 且砍了 APPENDED_BLOCK`

```bash
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/agents/kdev-step-recorder.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "feat(kdev-memory): step-recorder 按 rating.mode 写用户评分段 + Return 精简为一行"
```

---

## 收尾 Task: bump v0.15.0 + CHANGELOG + 项目 config + 跑迁移 + roadmap 回写

**由编排主控执行（非 subagent）——涉及真实 repo 状态变更 + 验证。**

- [ ] **Step 1: 全量测试绿（最终门禁）**

Run: `cd plugins/kdev-memory && python3 -m pytest tests/ -q`
Expected: 全部 passed（基线 291 + 新增约 30 条）

- [ ] **Step 2: bump plugin.json version**

`plugins/kdev-memory/.claude-plugin/plugin.json` 的 `"version": "0.14.0"` 改为 `"0.15.0"`。

- [ ] **Step 3: CHANGELOG 加 0.15.0 条目**

在 `plugins/kdev-memory/CHANGELOG.md` 顶部（`# kdev-memory CHANGELOG` 之后、`## [0.14.0]` 之前）插入：

```markdown
## [0.15.0] — 2026-06-11

**kdev-memory 减痛轨 P-C0.5 + P-C1a：评分模式可配 + brief 分级 + subagent 输出精简。**

### ✨ 新增

- **`rating.mode`（config.yaml，flat dot-key）** — 评分三档：`model-only`（零追问，= Q-002 机读化）/ `user-opt-in`（插件默认，轻提一句不阻塞）/ `user-required`（现行硬闸门）。`memory_config.read_rating_mode` / `rating_mode_configured`。
- **`brief.verbosity`（config.yaml）** — SessionStart brief 三档：`compact`（只注入 WARN + pending_decisions + 今日进度一行，其余写 `.kdev/memory/brief-detail.md`）/ `normal`（现行）/ `verbose`（全量不截断）。`memory_config.read_brief_verbosity`。
- **首次评分提示** — config 无 `rating.mode` 键时 brief 注入一次性 `<kdev-memory-rating-setup>`（`state/.rating-setup-shown` marker 去重）。
- **`hooks/lib/migrate_void_faded.py`** — Q-002 后"仅因用户评分空"的半残 Step 批量盖 `status: voided-faded` + 销账注释（幂等，dry-run 默认 / `--apply` 落盘）。

### 🔄 变更

- **`step_completeness`** — `check_step`/`run_check` 加 `rating_mode` 形参（默认 `user-required` 保现状）：`model-only`/`user-opt-in` 下"用户评分段空"不算半残；扣分项缺失**所有模式仍查**（防讨好式满分）。`parse_steps` 补 header 内联 `status:` 解析（修历史 latent bug——Step 1/2/3 的内联 voided-faded 此前从未生效）。
- **`stop-check`** — 按 `rating.mode` 降级：`model-only` 跳过半残检测、`user-opt-in` 软提醒不阻塞、`user-required` 现行（soft + strict 阻塞）。
- **`session-start-brief`** — verbosity 分级 + 首次评分提示 + 给半残扫描传 `rating_mode`。
- **`agents/kdev-step-recorder.md`** — 读 `rating.mode` 决定用户评分段写法（model-only 留空 + 内联 `status: voided-faded` + 销账注释，**绝不伪填自评分**）；Return format 砍 `APPENDED_BLOCK`，只回 6 行审计字段。
- **`SKILL.md` / `六类记录-schema.md`** — 评分动作链按 `rating.mode` 三分支重写；schema 注明 model-only 留空 + voided-faded 标准做法。

### 🧱 向后兼容 / 约束

- **默认温和**：`rating.mode` 默认 `user-opt-in`、`brief.verbosity` 默认 `normal`；`user-required` = 现行行为完整保留。
- **不伪造用户评分**：model-only 用户评分段留空 + voided-faded，绝不拷自评分（污染 misalignment 切片）。
- **不预留** `peer_review`（他评 defer）；**不碰** P-C1b transcript 溯源（commit-tracker offset / step-recorder input 重写均未做）。
- **测试**：新增 `test_rating_mode_config` / `test_brief_verbosity` / `test_stop_check` / `test_migrate_void_faded`，更新 `test_step_completeness`；全量绿。
- **G-004 提醒**：本版 bump `0.14.0 → 0.15.0`，用户侧需刷 marketplace（`/plugin` 更新/重装）+ 重启 session 才生效。
```

- [ ] **Step 4: 本项目 config 设 model-only（必做）+ 询问 compact（可选）**

`.kdev/memory/config.yaml` 在 `record_mode: hybrid` 之后加：
```yaml

# 评分模式：model-only（本项目 = Q-002，零追问）| user-opt-in（插件默认）| user-required
rating.mode: model-only
```
`brief.verbosity: compact` 为可选（spec 标"由用户定"）——收尾时一句话问用户是否要（要则补 `brief.verbosity: compact`）。

- [ ] **Step 5: 在真实执行日志上跑迁移（先 dry-run 再 apply）**

```bash
cd /home/lyadmin/Projects/kdev-agents
python3 plugins/kdev-memory/hooks/lib/migrate_void_faded.py --log .kdev/memory/执行日志.md --cutoff 2026-05-27
# 核对 dry-run 输出的盖章清单合理后：
python3 plugins/kdev-memory/hooks/lib/migrate_void_faded.py --log .kdev/memory/执行日志.md --cutoff 2026-05-27 --apply
```
**验证**：迁移后用 step_completeness 在 model-only 下扫，确认半残归零：
```bash
cd plugins/kdev-memory && python3 -c "
import sys; sys.path.insert(0,'hooks/lib')
from step_completeness import run_check
from pathlib import Path
r = run_check(Path('../../.kdev/memory/执行日志.md'), '2026-06-11', rating_mode='model-only')
print('model-only status:', r['status'], 'half:', len(r['half_complete_steps']))
"
```
Expected: `model-only status: ok half: 0`（或仅剩扣分项真问题的极少数）。

- [ ] **Step 6: roadmap 回写 P-C0.5 ✅ / P-C1a ✅**

`docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md`：
- 行 45：`kdev-memory减痛轨 P-C0.5/1a/1b（spec done）⏳` 改为 `kdev-memory减痛轨 ✅ P-C0.5(评分可配)/✅ P-C1a(brief分级+subagent精简) done(v0.15.0) · P-C1b(transcript溯源)⏳ defer`。
- §1.5.1 第 64 行 `P-C0.5 评分模式可配(机读化 Q-002) → P-C1a brief分级+subagent精简 → P-C1b Step落盘 transcript溯源` 改为
  `✅ P-C0.5 评分模式可配(机读化 Q-002, v0.15.0) → ✅ P-C1a brief分级+subagent精简(v0.15.0) → P-C1b Step落盘 transcript溯源 ⏳ defer`。

- [ ] **Step 7: 收尾 commit**

```bash
cd /home/lyadmin/Projects/kdev-agents
git -c user.name=ly-AI -c user.email=ly1989abc@126.com add plugins/kdev-memory/.claude-plugin/plugin.json plugins/kdev-memory/CHANGELOG.md docs/framework/01-design/2026-06-06-01-数字员工整体设计路线图roadmap-v1.0.md
git -c user.name=ly-AI -c user.email=ly1989abc@126.com commit -m "release(kdev-memory): v0.15.0 减痛轨 P-C0.5+P-C1a + roadmap 回写"
# .kdev/memory/ 由 kdev-sync hook 自托管，config.yaml + 执行日志迁移随 SessionEnd 推送，无需手动 commit 进框架仓
```

> ⚠️ 不 push（本项目约定）。`.kdev/` 是 nested 记忆仓，config + 迁移后的执行日志走 kdev-sync 自托管，不进框架仓 commit。

---

## Self-Review（plan 作者自查，已执行）

**1. Spec 覆盖：**
- §3.1 config rating.mode → A1 ✓；§3.2 三档行为 → A2(step_completeness)+A3(stop-check)+B1(brief) ✓；§3.3 model-only 留空 voided-faded → A2(内联 status)+B2(recorder)+A4(schema) ✓；§3.4 首次提示 → B1 ✓；§3.5 批量销账 → A5 + 收尾 Step5 ✓；§3.6 文件清单 → 全覆盖 ✓
- §4.1 brief verbosity → B1 ✓；§4.2 subagent 一行 → B2 ✓；§4.3 stop-check 降级 → A3 ✓
- 任务清单 1–16 全覆盖（11/12 brief 两改合一在 B1；13 recorder 在 B2；14 = A3 已覆盖；15 bump + 16 可选 compact 在收尾）✓

**2. Placeholder 扫描：** 每个 code step 都给了完整代码/精确锚点替换文本，无 TBD/TODO/"类似上面"。✓

**3. 类型一致性：** `rating_mode` 形参贯穿 `read_rating_mode`→`run_check`→`check_step` 同名；`read_brief_verbosity` 返回值 `compact|normal|verbose` 与 brief 分支字面量一致；`void_faded_backlog(log_text, cutoff_date, today)` 签名在 lib 与 test 一致；marker 路径 `state/.rating-setup-shown` 在 helper 与 test 一致。✓

**4. 向后兼容自查：** `step_completeness` 内部默认 `user-required` → 既有 11 测试文件零波及；`read_rating_mode` 默认 `user-opt-in` 仅影响 hook 实际行为（= 期望的去 nag）；`brief` 默认 normal；`test_session_start_brief_prefix` 无 config → 会多注入 setup 块，但其断言全是 `in` 不是 `==`，不破。✓
