from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/kdev-flow-driver/SKILL.md"
ROUTING = ROOT / "skills/kdev-flow-driver/references/node-agent-routing.md"
DEV_ENV = ROOT / "agents/dev-engineer-env.md"
DEV_PLAN = ROOT / "agents/dev-engineer-plan.md"
REQ_ORCH = ROOT / "agents/req-architect-orchestrator.md"

# 跨员工交付契约常量：生产方 req-architect 在 n8-merge 落交付 handoff，
# 消费方 dev-engineer 同 slug 读。consumer/producer 两侧必须引用同一节点 id。
DELIVERY_NODE = "n8-merge"
PRODUCER = "req-architect"


def _t(p):
    return p.read_text(encoding="utf-8")


def test_skill_has_cross_employee_handoff_section():
    """SKILL 新增 §2.4ter 跨员工 handoff 段（区别于 §2.4bis 同流交接）。"""
    t = _t(SKILL)
    assert "2.4ter" in t
    assert "跨员工" in t


def test_skill_cross_section_documents_producer_consumer_contract():
    """§2.4ter 必含：生产方写交付 + 消费方读 + 同 slug join + 裸任务回退。"""
    t = _t(SKILL)
    start = t.index("2.4ter")
    end = t.index("### 2.5")
    sec = t[start:end]
    assert "handoff-write" in sec      # 生产方落交付
    assert "handoff-read" in sec       # 消费方读
    assert PRODUCER in sec             # req-architect
    assert DELIVERY_NODE in sec        # n8-merge 交付节点
    assert "slug" in sec               # 同 slug join
    assert ("裸任务" in sec) or ("回退" in sec)  # 上游缺失回退


def test_skill_maps_producer_to_delivery_node():
    """SKILL 明确生产方→交付节点映射（req-architect → n8-merge），消费方据此读。"""
    t = _t(SKILL)
    start = t.index("2.4ter")
    end = t.index("### 2.5")
    sec = t[start:end]
    # 映射行同时出现生产方与其交付节点
    assert PRODUCER in sec and DELIVERY_NODE in sec
