"""test step_completeness 识别褪色补录销账（v0.7 新增）

背景：v0.6 及以前 step_completeness.check_step 只看字面 "完成时间：—"
就报欠评，导致 iter 5~8 的 meta 回补条目（Step M-5~M-8）被反复报"待处理"。
v0.7 要求 check_step 在"空完成时间"命中后再扫销账信号，任一命中即跳过。
"""

import sys
from pathlib import Path

HOOK_LIB = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(HOOK_LIB))

import step_completeness  # noqa: E402


def _write_log(tmp_path: Path, content: str) -> Path:
    log = tmp_path / "执行日志.md"
    log.write_text(content, encoding="utf-8")
    return log


def test_faded_backfill_step_is_not_half_complete(tmp_path):
    """褪色补录 Step（含 **褪色补录** / 保留占位 / 非原生当场采集 任一标记）应被跳过。"""
    log = _write_log(tmp_path, """## Step M-5: iter-5 主控零评分兜底（回补 meta）

日期：2026-04-15

### 执行事实
- 工具调用：—
- 使用的 skill：kdev-memory

### 模型自评
- 顺畅度：—/5
- 扣分项：—

### 用户评分
- 完成时间：—
- 顺畅度：—/5（**褪色补录**，距今 6~7 天；保留占位不强求补）
- 用户评价：—

> 🔴 回补声明：非原生当场采集

### 评分差异分析
- 无原生评分 → 不计入差值
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"褪色补录 Step 应被识别为已销账，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_m_prefix_step_is_not_half_complete(tmp_path):
    """Step 标题含 M- 前缀（meta 回补标识）就应跳过，哪怕没有其他销账关键词。"""
    log = _write_log(tmp_path, """## Step M-7 meta 回补

日期：2026-04-19

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"M- 前缀 Step 应被识别为 meta 回补占位，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_genuine_open_step_still_reported(tmp_path):
    """真正欠评的 Step（没有任何销账标记）还是要报 —— 启发式不能过度跳过。"""
    log = _write_log(tmp_path, """## Step 20: collector v1.4 重构

日期：2026-04-24

### 模型自评
- 顺畅度：4/5
- 扣分项：一次 import 路径错

### 用户评分
- 完成时间：—
- 顺畅度：—/5
- 用户评价：—
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "has_half_complete", (
        f"真正欠评的 Step 应被报，当前 status: {result['status']}"
    )
    assert any(s["step_label"] == "Step 20" for s in result["half_complete_steps"])


def test_status_voided_faded_frontmatter_skipped(tmp_path):
    """Step body 里的 YAML frontmatter status: voided-faded 应直接跳过（不依赖启发式）。"""
    log = _write_log(tmp_path, """## Step M-6: iter-6（回补 meta）

---
status: voided-faded
---

日期：2026-04-17

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "ok", (
        f"status=voided-faded 应被直接跳过，当前 half_complete: "
        f"{result['half_complete_steps']}"
    )


def test_status_open_with_missing_fields_still_reported(tmp_path):
    """status=open 且真的字段缺 → 仍然要报（status=open 不是免死金牌）。"""
    log = _write_log(tmp_path, """## Step 21: 真正欠评

---
status: open
---

日期：2026-04-24

### 用户评分
- 完成时间：—
- 顺畅度：—/5
""")
    result = step_completeness.run_check(log, "2026-04-24")
    assert result["status"] == "has_half_complete"
