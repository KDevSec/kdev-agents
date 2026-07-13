# scripts/tests/test_case_md_parser.py
from pathlib import Path
from case_md_parser import parse_cases, CaseRecord

FIX = Path(__file__).parent / "fixtures" / "sample_cases.md"

def test_parses_two_blocks():
    cases = parse_cases(FIX.read_text(encoding="utf-8"))
    assert len(cases) == 2

def test_scalar_fields():
    c = parse_cases(FIX.read_text(encoding="utf-8"))[0]
    assert c.tc_id == "TC-AR3-001"
    assert c.title == "运维人员-存在未加密记录-配置双模式-执行migrate"
    assert c.ar == "AR-3"
    assert c.case_kind == "基本流"
    assert c.module == "密钥升级加固"
    assert c.pri == "1"

def test_list_fields_independent_counts():
    c = parse_cases(FIX.read_text(encoding="utf-8"))[0]
    # 步骤与预期条数不同 —— 这是订正后的关键不变量
    assert len(c.steps) == 5
    assert len(c.expects) == 2
    assert c.steps[0] == "验证存在未加密记录"
    assert c.expects[1] == "生成新密钥版本号"
    assert len(c.preconditions) == 2

def test_remark_captured_raw():
    c = parse_cases(FIX.read_text(encoding="utf-8"))[0]
    assert "准入：是" in c.remark
