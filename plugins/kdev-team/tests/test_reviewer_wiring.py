import json
from pathlib import Path

import pytest

TEAM = Path(__file__).resolve().parents[1]
REF = TEAM / "skills/kdev-flow-driver/references"
GDL = REF / "gate-decision-logic.md"
NAR = REF / "node-agent-routing.md"
SKILL = TEAM / "skills/kdev-flow-driver/SKILL.md"
ORCH = TEAM / "agents/reviewer-orchestrator.md"
DEV_ORCH = TEAM / "agents/dev-engineer-orchestrator.md"

# reviewer-episode 裸文件 token（≠ CLI flow-state handoff 的 <node_id>.handoff.json）
REVIEWER_FILE_TOKENS = ("<gate>.handoff.json", "<gate>.request.json")
CLI_HANDOFF_VERBS = ("handoff-read", "handoff-write")
# 禁止指令 = "用 CLI 读裸文件"；但显式禁用句（"绝不可用…"）允许同行共现
NEGATION_MARKERS = ("绝不", "不可", "不走", "非 CLI", "非CLI", "勿用", "别用", "≠", "不是 CLI")
REVIEWER_DOCS = (ORCH, DEV_ORCH, SKILL, GDL, NAR)


def test_gate_logic_dev_gates_no_longer_deferred():
    text = GDL.read_text(encoding="utf-8")
    # dev3 不再「全 deferred」；出现真发函语义
    assert "reviewer-orchestrator" in text
    assert "发函" in text or "dispatch" in text
    # 不再把 g-code-review 当 deferred PASS
    assert "deferred:阶段3-评审专家" not in text or "已兑现" in text


def test_node_routing_has_reviewer_dispatch_section():
    text = NAR.read_text(encoding="utf-8")
    assert "reviewer" in text.lower()
    assert "kdev-team:reviewer-orchestrator" in text
    assert "handoffs/reviewer/" in text


# ---- Q 候选 2：reviewer 回函契约（裸文件交接，非 CLI flow-state handoff）----

def test_reviewer_return_is_naked_file_rejected_by_cli_flow_reader(tmp_path):
    """钉死契约方向：reviewer 回函裸 schema 用普通 Read(json) 取 verdict 通；
    同一文件喂 kdev-core flow-state reader 必 FlowStateError（两者不同物，防回归方案 A）。"""
    from kdev_core import flow_state  # conftest 已把 kdev-core 上 sys.path

    payload = {
        "verdict": "PASS",
        "scores": ["n9a-code-review.code.score.md"],
        "counts": {"🔴": 0, "🟡": 1, "⚪": 2},
        "revisions": [],
        "by": "reviewer-expert",
        "request_id": "n9a-code-review",
    }
    feat = tmp_path / ".kdev" / "features" / "demo" / "handoffs" / "reviewer"
    feat.mkdir(parents=True)
    p = feat / "n9a-code-review.handoff.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    # caller 路径 = 普通 Read + json：取得 verdict
    assert json.loads(p.read_text(encoding="utf-8"))["verdict"] == "PASS"

    # CLI flow-state reader 路径：缺 node_id/employee/status/summary → 必失败
    with pytest.raises(flow_state.FlowStateError) as exc:
        flow_state.read_handoff_status(str(tmp_path), "demo", "reviewer",
                                       "n9a-code-review")
    assert "node_id" in str(exc.value)


def test_no_doc_couples_cli_handoff_verb_with_reviewer_file():
    """没有文档把 reviewer 裸文件 token 与 CLI handoff-read/write 写同一行（契约混用根因）。"""
    offenders = []
    for path in REVIEWER_DOCS:
        text = path.read_text(encoding="utf-8")
        for i, line in enumerate(text.splitlines(), 1):
            has_tok = any(tok in line for tok in REVIEWER_FILE_TOKENS)
            has_verb = any(verb in line for verb in CLI_HANDOFF_VERBS)
            negated = any(m in line for m in NEGATION_MARKERS)
            if has_tok and has_verb and not negated:
                offenders.append(f"{path.name}:{i}: {line.strip()}")
    assert not offenders, \
        "reviewer 裸文件不可指令 CLI handoff 动词读写:\n" + "\n".join(offenders)


def test_verdict_read_step_uses_plain_read():
    """SKILL/NAR 的发函步骤里『读 <gate>.handoff.json 取 verdict』那行用 Read（非 CLI handoff-read）。"""
    for path in (SKILL, NAR):
        text = path.read_text(encoding="utf-8")
        # 仅「读取动作」行（含 取 + verdict + 文件名）——排除产物落位枚举/写回行
        hits = [ln for ln in text.splitlines()
                if "<gate>.handoff.json" in ln and "verdict" in ln and "取" in ln]
        assert hits, f"{path.name}: 找不到读 verdict 的步骤行"
        for ln in hits:
            assert "Read" in ln and "handoff-read" not in ln, \
                f"{path.name}: verdict 读取应为 Read 非 CLI: {ln.strip()}"


def test_reviewer_naked_file_contract_note_present():
    """node-agent-routing reviewer 发函段有契约注：裸文件交接、禁用 kdev_core handoff-read。"""
    nar = NAR.read_text(encoding="utf-8")
    assert "裸文件" in nar
    assert "kdev_core handoff-read" in nar  # 明示禁用 CLI reader 读 reviewer 文件


# ---- G 候选 3：callee anomaly 留痕通道（不碰 caller events.jsonl）----

def test_reviewer_callee_does_not_write_caller_events():
    """reviewer 是 callee，不往 caller events.jsonl 留痕（无写入通道，原指令悬空）。"""
    orch = ORCH.read_text(encoding="utf-8")
    bad = [ln.strip() for ln in orch.splitlines()
           if "events.jsonl" in ln and "留痕" in ln]
    assert not bad, "callee 不写 caller events.jsonl:\n" + "\n".join(bad)


def test_reviewer_anomaly_routes_to_arbitration_and_return_field():
    """元评审异常走 arbitration.md + 回函 anomaly 字段，由 caller 决定是否转事件。"""
    orch = ORCH.read_text(encoding="utf-8")
    assert "arbitration.md" in orch
    assert "anomaly" in orch
