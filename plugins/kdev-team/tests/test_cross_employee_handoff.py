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


def test_routing_req_architect_n8_writes_delivery_handoff():
    """node-agent-routing req-architect n8-merge 行：编排自做 + 写交付 handoff。"""
    t = _t(ROUTING)
    # 取 req-architect 路由段（"# req-architect" 标题之后）
    start = t.index("req-architect（需求架构师）design-flow 路由")
    sec = t[start:]
    assert "n8-merge" in sec
    assert "handoff-write" in sec
    assert "--node n8-merge" in sec


def test_routing_dev_engineer_reads_upstream_at_n0_and_n3():
    """dev-engineer n0-env / n3-plan 上下文列加「读上游 req-architect 交付」。"""
    t = _t(ROUTING)
    # dev-engineer 段在 req-architect 段之前（文件上半部）
    end = t.index("req-architect（需求架构师）design-flow 路由")
    dev_sec = t[:end]
    assert "handoff-read" in dev_sec
    assert "req-architect" in dev_sec
    # 读发生在入口节点
    assert "n0-env" in dev_sec and "n3-plan" in dev_sec


def test_dev_env_agent_reads_upstream_sr():
    """dev-engineer-env persona：读上游 req-architect 交付（SR+背景），缺失裸任务。"""
    t = _t(DEV_ENV)
    assert "handoff-read" in t
    assert "req-architect" in t
    assert ("裸任务" in t) or ("缺失" in t)


def test_dev_plan_agent_seeds_increments_from_upstream_ar():
    """dev-engineer-plan persona：上游 AR/方案在则以其用户故事/迭代切增量。"""
    t = _t(DEV_PLAN)
    assert "handoff-read" in t
    assert "req-architect" in t
    assert ("AR" in t) or ("用户故事" in t)
