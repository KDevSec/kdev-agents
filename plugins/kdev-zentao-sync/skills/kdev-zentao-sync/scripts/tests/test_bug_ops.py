"""tests/test_bug_ops.py — bug_ops.py 纯函数单测（query 过滤 / junit 解析 / 回归对照）。"""
from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import bug_ops  # noqa: E402


# ---------------------------------------------------------------- 字段归一
def test_account_of_dict_and_str():
    assert bug_ops.account_of({"account": "alice", "realname": "A"}) == "alice"
    assert bug_ops.account_of({"realname": "A"}) == "A"
    assert bug_ops.account_of("bob") == "bob"
    assert bug_ops.account_of(None) == ""


# ---------------------------------------------------------------- TC 提取/规范化
def test_bug_tc_id_first_only():
    assert bug_ops.bug_tc_id("[TC-AR0100100-G3-003] 工具栏联动") == "TC-AR0100100-G3-003"
    assert bug_ops.bug_tc_id("[TC-API-AR0300100-G2-006/007/008] 分页") == "TC-API-AR0300100-G2-006/007/008"
    assert bug_ops.bug_tc_id("平台管理员登录，无 TC 前缀") == ""


def test_canon_bug_tcs_single():
    assert bug_ops.canon_bug_tcs("[TC-AR0100100-G3-003] x") == ["AR0100100-G3-003"]


def test_canon_bug_tcs_api_prefix_normalized():
    # API- 泳道标记被抹掉，与 UI 泳道同 AR-G-用例映射到同一 canonical。
    assert bug_ops.canon_bug_tcs("[TC-API-AR0100100-G3-003] x") == ["AR0100100-G3-003"]


def test_canon_bug_tcs_multi_range_expand():
    assert bug_ops.canon_bug_tcs("[TC-API-AR0300100-G2-006/007/008] 分页") == [
        "AR0300100-G2-006", "AR0300100-G2-007", "AR0300100-G2-008"]


def test_canon_bug_tcs_legacy_tc():
    assert bug_ops.canon_bug_tcs("[TC-032] 旧式") == ["TC32"]


def test_canon_node_ar_and_tc_and_none():
    assert bug_ops.canon_node("test_ar0100100_g3_003_toolbar_selection_linkage") == "AR0100100-G3-003"
    assert bug_ops.canon_node("test_ar0300100_g2_006_paging") == "AR0300100-G2-006"
    assert bug_ops.canon_node("test_tc032_something") == "TC32"
    assert bug_ops.canon_node("test_helper_not_a_case") is None


def test_canon_node_matches_bug_canonical():
    # 关键不变式：junit 节点 canonical == bug 标题 canonical（对照的地基）。
    assert bug_ops.canon_node("test_ar0100100_g3_003_x") == bug_ops.canon_bug_tcs("[TC-AR0100100-G3-003] y")[0]


# ---------------------------------------------------------------- query 过滤
_BUGS = [
    {"id": 13, "status": "resolved", "resolution": "fixed", "module": 8,
     "openedBy": "fanxiaotian01", "title": "[TC-AR0100100-G3-003] 工具栏联动"},
    {"id": 63, "status": "active", "resolution": "", "module": 8,
     "openedBy": {"account": "fanxiaotian01"}, "title": "产品线管理-删除按钮未置灰"},
    {"id": 70, "status": "active", "resolution": "", "module": 0,
     "openedBy": "fanxiaotian01", "title": "[TC-API-AR0300100-G2-006/007/008] 版本列表未分页"},
    {"id": 20, "status": "resolved", "resolution": "fixed", "module": 13,
     "openedBy": "fanxiaotian01", "title": "[TC-AR0300400-G1-005] CQ来源删除置灰"},
]


def test_filter_status_single_and_multi():
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, status="resolved")} == {13, 20}
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, status="active,resolved")} == {13, 63, 70, 20}


def test_filter_tc_prefix_lane_split():
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, tc_prefix="TC-AR")} == {13, 20}
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, tc_prefix="TC-API")} == {70}


def test_filter_module_and_resolution_and_contains():
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, module=8)} == {13, 63}
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, resolution="fixed")} == {13, 20}
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, title_contains="分页")} == {70}


def test_filter_opened_by_handles_dict():
    assert {b["id"] for b in bug_ops.filter_bugs(_BUGS, opened_by="fanxiaotian01")} == {13, 63, 70, 20}


# ---------------------------------------------------------------- junit 解析
_JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4">
  <testcase classname="tests.productline.test_productline_list"
            name="test_ar0100100_g3_004_empty_filter_state" time="1.0" />
  <testcase classname="tests.productline.test_productline_list"
            name="test_ar0100100_g3_003_toolbar_selection_linkage" time="2.0">
    <failure message="有下级删除应置灰 assert False">trace...</failure>
  </testcase>
  <testcase classname="tests.version.test_version_delete"
            name="test_ar0300400_g1_005_cq_source_delete_disabled" time="0.1">
    <skipped message="env 无 CQ 来源版本 —— 依赖型 skip">...</skipped>
  </testcase>
  <testcase classname="tests.util" name="test_helper_thing" time="0.1" />
</testsuite></testsuites>"""


def test_parse_junit_statuses():
    res = bug_ops.parse_junit_text(_JUNIT)
    assert res["AR0100100-G3-004"]["status"] == "passed"
    assert res["AR0100100-G3-003"]["status"] == "failed"
    assert "置灰" in res["AR0100100-G3-003"]["message"]
    assert res["AR0300400-G1-005"]["status"] == "skipped"
    assert "CQ" in res["AR0300400-G1-005"]["message"]
    # 非 AR/tc 命名的 helper 不纳入
    assert "test_helper_thing" not in res and bug_ops.junit_unmatched_count(_JUNIT) == 1


def test_parse_junit_error_is_failed():
    xml = ('<testsuites><testsuite><testcase name="test_ar0100100_g1_001_x">'
           '<error message="boom"/></testcase></testsuite></testsuites>')
    assert bug_ops.parse_junit_text(xml)["AR0100100-G1-001"]["status"] == "failed"


def test_parse_junit_worst_of_duplicates():
    xml = ('<testsuites><testsuite>'
           '<testcase name="test_ar0100100_g1_001_a" />'
           '<testcase name="test_ar0100100_g1_001_b"><failure message="x"/></testcase>'
           '</testsuite></testsuites>')
    # 两个 testcase 同 canonical（罕见）→ 取最坏（failed）
    assert bug_ops.parse_junit_text(xml)["AR0100100-G1-001"]["status"] == "failed"


# ---------------------------------------------------------------- 回归对照
def test_correlate_pass_fail_skip_missing_notc():
    results = bug_ops.parse_junit_text(_JUNIT)
    bugs = [
        {"id": 10, "status": "resolved", "title": "[TC-AR0100100-G3-004] 空态文案"},   # PASS
        {"id": 13, "status": "resolved", "title": "[TC-AR0100100-G3-003] 工具栏联动"},  # FAIL
        {"id": 20, "status": "resolved", "title": "[TC-AR0300400-G1-005] CQ删除置灰"},  # SKIP
        {"id": 99, "status": "resolved", "title": "[TC-AR0900900-G9-009] 不在本次结果"},  # MISSING
        {"id": 34, "status": "resolved", "title": "同步RDM二次确认数据未同步"},           # NO_TC
    ]
    got = {r["id"]: r["verdict_code"] for r in bug_ops.correlate_regression(bugs, results)}
    assert got == {10: "PASS", 13: "FAIL", 20: "SKIP", 99: "MISSING", 34: "NO_TC"}


def test_correlate_multi_tc_aggregate_worst():
    # 多 TC bug：一条 pass 一条 fail → 整体 FAIL（最坏态聚合）。
    xml = ('<testsuites><testsuite>'
           '<testcase name="test_ar0300100_g2_006_a" />'
           '<testcase name="test_ar0300100_g2_007_b"><failure message="x"/></testcase>'
           '<testcase name="test_ar0300100_g2_008_c" />'
           '</testsuite></testsuites>')
    results = bug_ops.parse_junit_text(xml)
    bug = [{"id": 70, "status": "resolved", "title": "[TC-API-AR0300100-G2-006/007/008] 分页"}]
    rec = bug_ops.correlate_regression(bug, results)[0]
    assert rec["verdict_code"] == "FAIL"
    assert len(rec["per_tc"]) == 3


def test_correlate_multi_tc_all_pass():
    xml = ('<testsuites><testsuite>'
           '<testcase name="test_ar0300100_g2_006_a" />'
           '<testcase name="test_ar0300100_g2_007_b" />'
           '<testcase name="test_ar0300100_g2_008_c" />'
           '</testsuite></testsuites>')
    results = bug_ops.parse_junit_text(xml)
    bug = [{"id": 70, "status": "resolved", "title": "[TC-API-AR0300100-G2-006/007/008] 分页"}]
    assert bug_ops.correlate_regression(bug, results)[0]["verdict_code"] == "PASS"
