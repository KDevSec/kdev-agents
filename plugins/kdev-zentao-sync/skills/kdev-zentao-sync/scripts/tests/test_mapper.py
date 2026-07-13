# scripts/tests/test_mapper.py
from case_md_parser import CaseRecord
from mapper import (case_to_testcase_payload, bug_row_to_payload,
                    testtask_payload, build_case_title, base_ar)


def _rec():
    return CaseRecord(tc_id="TC-AR3-001", title="标题X", case_kind="异常流",
                      module="密钥升级加固", pri="2",
                      preconditions=["操作人员：运维", "存在记录"],
                      steps=["步骤一", "步骤二", "步骤三"],
                      expects=["预期一", "预期二"])


def test_steps_not_index_aligned_expects_on_last():
    p = case_to_testcase_payload(_rec(), product=1, module_id=7)
    # 3 步 → 3 个 step 行；2 条预期合并挂最后一步 expect（不按序号配对）
    assert len(p["steps"]) == 3
    assert p["steps"][0]["expect"] == ""
    assert "预期一" in p["steps"][-1]["expect"]
    assert "预期二" in p["steps"][-1]["expect"]


def test_case_payload_core_fields():
    p = case_to_testcase_payload(_rec(), product=1, module_id=7)
    assert p["product"] == 1 and p["module"] == 7
    assert p["pri"] == 2 and p["type"] == "feature"
    assert p["title"] == "标题X"
    assert "TC-AR3-001" in p["keywords"]           # TC-ID 入 keywords 供溯源/去重
    assert "操作人员：运维" in p["precondition"]


def test_title_truncated_255():
    rec = _rec(); rec.title = "长" * 400
    assert len(build_case_title(rec)) <= 255


def test_bug_payload_matches_legacy_shape():
    row = {"用例ID": "TC-1", "用例名称": "n", "用例函数": "f",
           "原因分类": "真实-后端", "失败摘要": "boom", "时间": "t", "截图": "", "日志文件": ""}
    p = bug_row_to_payload(row, product=1, build="trunk")
    assert p["product"] == 1 and p["type"] == "codeerror"
    assert p["severity"] == 3 and p["pri"] == 3
    assert p["title"].startswith("[TC-1]") and p["openedBuild"] == "trunk"
    assert "boom" in p["steps"]
    # 本实例 v1 丢 steps → 分诊信息(原因分类/失败摘要)必须也打进 title(唯一持久字段)
    assert "真实-后端" in p["title"] and "boom" in p["title"]


def test_bug_title_truncated_255_tc_id_intact():
    row = {"用例ID": "TC-9", "用例名称": "名" * 300, "原因分类": "真实-后端",
           "失败摘要": "x", "用例函数": "", "时间": "", "截图": "", "日志文件": ""}
    p = bug_row_to_payload(row, product=1, build="trunk")
    assert len(p["title"]) <= 255
    assert p["title"].startswith("[TC-9]")   # 去重锚点恒在最前,截断只切尾


def test_bug_payload_records_screenshot_path_not_attachment():
    # v1 无文件上传端点（实测 404）→ 截图按路径据实写入 bug 描述，不假装"见附件"
    row = {"用例ID": "TC-2", "用例名称": "n", "用例函数": "f", "原因分类": "真实-后端",
           "失败摘要": "boom", "时间": "t", "截图": "screenshots/x.png", "日志文件": ""}
    p = bug_row_to_payload(row, product=1, build="trunk")
    assert "screenshots/x.png" in p["steps"]      # 路径据实留存
    assert "见附件" not in p["steps"]              # 不误导成"已附件"


def test_testtask_payload():
    p = testtask_payload(name="冒烟单", product=1, project=2, build="trunk",
                         owner="admin", begin="2026-06-20", end="2026-06-27", desc="d")
    assert p["name"] == "冒烟单" and p["product"] == 1 and p["build"] == "trunk"


# ── 对应需求(story) 按 AR 关联 + 所属模块(module) 按名映射 ──────────────────

def test_base_ar_strips_description_and_whitespace():
    # WHY：需求库 story 标题是「AR编号：描述」，用例 需求编号 是纯 AR；
    #      映射前必须归一到 AR 主键，否则永远对不上 story。
    assert base_ar("AR-PRL-FUN-01.001.00：查看产品线列表") == "AR-PRL-FUN-01.001.00"
    assert base_ar("AR-PRL-FUN-01.001.00") == "AR-PRL-FUN-01.001.00"
    assert base_ar("  AR-X-1  ") == "AR-X-1"
    assert base_ar("") == ""


def test_story_linked_when_ar_hits_map():
    # WHY：用例『对应需求』空 = 影响面/需求覆盖追溯断链；命中 AR 必须写 story。
    rec = _rec(); rec.ar = "AR-PRL-FUN-01.001.00"
    p = case_to_testcase_payload(rec, product=1, module_id=0,
                                 ar2story={"AR-PRL-FUN-01.001.00": 1})
    assert p["story"] == 1


def test_story_omitted_when_ar_misses_map():
    # WHY：未命中不能瞎填 story（错关联比不关联更坏）→ 干脆不发 story 字段。
    rec = _rec(); rec.ar = "AR-UNKNOWN-99.999.99"
    p = case_to_testcase_payload(rec, product=1, module_id=0,
                                 ar2story={"AR-PRL-FUN-01.001.00": 1})
    assert "story" not in p


def test_module_mapped_by_name_overrides_default():
    # WHY：module_id 兜底是「根 0」；只要 md 模块名能映射到 id，就按名归位而非落根。
    rec = _rec(); rec.module = "产品管理中心"
    p = case_to_testcase_payload(rec, product=1, module_id=0,
                                 name2module={"产品管理中心": 2, "系统管理": 3})
    assert p["module"] == 2


def test_module_falls_back_to_story_module_when_name_unmapped():
    # WHY：禅道无模块 GET API，但 story 带 module 且用例库与 story 共用同一棵树 →
    # md 模块名没 --module-map 时，用例自动归到「其对应需求所在模块」，绕开 /browse 查 id。
    rec = _rec(); rec.ar = "AR-VER-FUN-03.002.00"; rec.module = "产品管理中心/版本管理"
    p = case_to_testcase_payload(rec, product=1, module_id=0,
                                 ar2module={"AR-VER-FUN-03.002.00": 13})
    assert p["module"] == 13


def test_module_map_name_takes_priority_over_story_module():
    # WHY：--module-map 是人显式给的，优先级必须高于 story.module 自动反推。
    rec = _rec(); rec.ar = "AR-VER-FUN-03.002.00"; rec.module = "产品管理中心/版本管理"
    p = case_to_testcase_payload(rec, product=1, module_id=0,
                                 name2module={"产品管理中心/版本管理": 99},
                                 ar2module={"AR-VER-FUN-03.002.00": 13})
    assert p["module"] == 99


def test_module_falls_back_to_default_when_no_map_and_no_story_module():
    # WHY：既无 --module-map 命中、对应需求 story 也无模块 → 用兜底 module_id，绝不瞎归。
    rec = _rec(); rec.ar = "AR-UNKNOWN-99.999.99"; rec.module = "未知模块"
    p = case_to_testcase_payload(rec, product=1, module_id=7,
                                 ar2module={"AR-VER-FUN-03.002.00": 13})
    assert p["module"] == 7


def test_module_falls_back_when_name_unmapped():
    # WHY：模块名未在 map 里 → 回退 module_id（不静默丢、也不乱挂别的模块）。
    rec = _rec(); rec.module = "未登记模块"
    p = case_to_testcase_payload(rec, product=1, module_id=9,
                                 name2module={"产品管理中心": 2})
    assert p["module"] == 9
