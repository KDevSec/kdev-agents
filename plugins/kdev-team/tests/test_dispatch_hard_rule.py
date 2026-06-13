"""跨员工直接发函硬规（v1.5 硬规 2/7）落在 runtime 层 + caller 对称 prose 的硬校验。

钉三不变量：① who→whom（编排↔编排不经 CEO=硬规2；能力不直接对外、跨员工走编排=硬规4/5）
② 发函=结构化 request（非自由对话，走 B 轨文件交接）③ 边界=建议非拦截、处置权+入账在 caller。
守 G-008：编排走通用 driver，reviewer callee 不复用 driver/不 own flow。
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/kdev-flow-driver/SKILL.md"
NAR = ROOT / "skills/kdev-flow-driver/references/node-agent-routing.md"
STAFF = ROOT / "staff.yml"
DEV_ORCH = ROOT / "agents/dev-engineer-orchestrator.md"
REQ_ORCH = ROOT / "agents/req-architect-orchestrator.md"

SECTION_ANCHOR = "2.4quater"


def _t(p):
    return p.read_text(encoding="utf-8")


def _section():
    """取 SKILL §2.4quater 整段（到下一节 §2.5 前）。"""
    t = _t(SKILL)
    assert SECTION_ANCHOR in t, "SKILL 缺 §2.4quater 跨员工发函硬规节"
    start = t.index(SECTION_ANCHOR)
    end = t.index("### 2.5", start)
    return t[start:end]


def test_skill_has_consolidated_dispatch_hard_rule_section():
    """SKILL 有统一的「跨员工直接发函硬规」节，标题点名 v1.5 硬规 2/7。"""
    sec = _section()
    assert "跨员工" in sec and "发函" in sec and "硬规" in sec
    assert "2/7" in sec  # 显式 v1.5 硬规编号


def test_invariant_1_who_to_whom():
    """不变量①：编排↔编排不经 CEO（硬规2）；能力不直接对外、跨员工走编排（硬规4/5）。"""
    sec = _section()
    assert "硬规 2" in sec and "硬规 4" in sec and "硬规 5" in sec
    assert "不经 CEO" in sec
    assert "编排" in sec and ("不直接对外" in sec or "不能能力直连" in sec)
    # 发函只 dispatch 对方 orchestrator，caller 不直接派对方 cap
    assert "orchestrator" in sec
    assert ("不直接派" in sec) or ("不直接派对方" in sec) or ("不直接 dispatch" in sec)


def test_invariant_2_structured_not_freeform():
    """不变量②：发函=结构化 request（caller+caps+产物指针），走 B 轨，非自由对话。"""
    sec = _section()
    assert "结构化" in sec
    assert "request" in sec.lower()
    assert ("非自由对话" in sec) or ("不是" in sec and "自然语言" in sec)
    assert "B 轨" in sec
    # 结构化字段三件：谁发给谁 + 评什么 + 产物指针
    assert "caller" in sec
    assert ("caps" in sec) or ("target_paths" in sec)
    assert ("产物指针" in sec) or ("standards_refs" in sec) or ("artifacts" in sec)


def test_invariant_3_advice_not_block_caller_decides():
    """不变量③：评审给建议非拦截；处置权+入账在 caller；🔴经双重条件走有界回流。"""
    sec = _section()
    assert ("建议" in sec) and ("非拦截" in sec or "不直接命令" in sec or "不自己 halt" in sec)
    assert "caller 自主判断" in sec or "自主判断" in sec
    assert "处置权" in sec
    assert "record-gate" in sec  # 入账归 caller
    assert "双重通过条件" in sec or "双重条件" in sec
    assert "有界回流" in sec


def test_section_guards_g008_callee_not_own_flow():
    """守 G-008：编排走通用 kdev-flow-driver；callee 不复用 driver、不 own flow-state。"""
    sec = _section()
    assert "G-008" in sec
    assert "kdev-flow-driver" in sec
    assert "不复用" in sec
    assert "flow-state" in sec or "不 own flow" in sec or "不持有" in sec


def test_section_links_canonical_hard_rule_declaration():
    """硬规节回链 canonical 声明（概念合稿 §10.1），防 runtime 与设计稿漂移。"""
    sec = _section()
    assert "10.1" in sec  # 合稿 §10.1 通信硬规
    assert "合稿" in sec or "概念模型" in sec


def test_node_routing_points_to_hard_rule_section():
    """node-agent-routing reviewer 发函段交叉指向 §2.4quater（防硬规散落漂移）。"""
    t = _t(NAR)
    assert SECTION_ANCHOR in t


def test_staff_yml_notes_callee_dispatch_semantics():
    """staff.yml 头注释钉一句：callee=被发函、不 own flow。"""
    t = _t(STAFF)
    head = t[: t.index("employees:")]
    assert "发函" in head
    assert "callee" in head
    assert "不 own flow" in head or "不持有 flow" in head or "无自有 flow" in head


def test_caller_orchestrators_have_dispatch_boundary_prose():
    """两 caller 编排 Principles 有对称发函边界：结构化请求 + 处置权在本编排。"""
    for orch in (DEV_ORCH, REQ_ORCH):
        t = _t(orch)
        assert "结构化" in t, f"{orch.name} 缺『结构化请求』边界"
        assert "处置权" in t, f"{orch.name} 缺『处置权在本编排』边界"
        assert "2.4quater" in t, f"{orch.name} 未指向硬规节"
