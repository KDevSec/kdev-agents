"""test scope.recorder_target_jsonl: flat + scoped 两种布局路径都验。

镜像 recorder_target_log 的 scope 分支拓扑，扩展名 .jsonl（Q-20260617 基座层）。
"""
from __future__ import annotations

import sys
from pathlib import Path

LIB_DIR = Path(__file__).parent.parent / "hooks" / "lib"
sys.path.insert(0, str(LIB_DIR))

from scope import recorder_target_jsonl, recorder_target_log  # noqa: E402


def test_jsonl_flat_shared(tmp_path):
    """flat 布局，shared/None scope → root/执行日志.jsonl。"""
    assert recorder_target_jsonl(None, tmp_path) == tmp_path / "执行日志.jsonl"
    assert recorder_target_jsonl("shared", tmp_path) == tmp_path / "执行日志.jsonl"
    assert recorder_target_jsonl("project", tmp_path) == tmp_path / "执行日志.jsonl"


def test_jsonl_flat_staff_falls_back_to_root(tmp_path):
    """flat 布局（无 shared/ 目录），员工 scope 兜底回 root（镜像 recorder_target_log）。"""
    assert recorder_target_jsonl("dev-engineer", tmp_path) == tmp_path / "执行日志.jsonl"


def test_jsonl_scoped_shared(tmp_path):
    """scoped 布局，shared/None scope → root/shared/执行日志.jsonl。"""
    (tmp_path / "shared").mkdir()
    assert recorder_target_jsonl(None, tmp_path) == tmp_path / "shared" / "执行日志.jsonl"


def test_jsonl_scoped_staff(tmp_path):
    """scoped 布局，员工 canonical id → root/staff/<id>/执行日志.jsonl。"""
    (tmp_path / "shared").mkdir()
    assert recorder_target_jsonl("dev-engineer", tmp_path) == tmp_path / "staff" / "dev-engineer" / "执行日志.jsonl"


def test_jsonl_mirrors_log_topology(tmp_path):
    """与 recorder_target_log 同 scope 拓扑，只换扩展名（.md → .jsonl）。"""
    (tmp_path / "shared").mkdir()
    for scope in (None, "shared", "project", "dev-engineer", "req-architect"):
        md = recorder_target_log(scope, tmp_path)
        jsonl = recorder_target_jsonl(scope, tmp_path)
        assert jsonl == md.with_name("执行日志.jsonl")
        assert jsonl.parent == md.parent  # 同目录，仅扩展名异
