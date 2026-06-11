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


def test_duplicate_headings_each_stamped_independently():
    log = (
        "# 执行日志\n\n"
        "## Step dup-1: 同名\n日期：2026-05-28\n\n"
        "### 模型自评\n- 顺畅度自评：4/5\n- 扣分项：x\n\n"
        "### 用户评分\n- 完成时间：—\n- 顺畅度：—/5\n\n"
        "## Step dup-1: 同名\n日期：2026-05-29\n\n"
        "### 模型自评\n- 顺畅度自评：4/5\n- 扣分项：y\n\n"
        "### 用户评分\n- 完成时间：—\n- 顺畅度：—/5\n"
    )
    new_text, stamped = mvf.void_faded_backlog(log, CUTOFF, "2026-06-11")
    # 两条同名 Step 都应各自盖一次章
    assert new_text.count("status: voided-faded") == 2
    assert len(stamped) == 2
    # 幂等：再跑不重复盖
    twice, s2 = mvf.void_faded_backlog(new_text, CUTOFF, "2026-06-11")
    assert s2 == []
    assert twice.count("status: voided-faded") == 2
