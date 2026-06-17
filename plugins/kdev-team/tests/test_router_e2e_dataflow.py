# plugins/kdev-team/tests/test_router_e2e_dataflow.py
import sys
from pathlib import Path

# kdev-hud 不在默认 path，显式加
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "kdev-hud"))

from kdev_team import lifecycle, lint, delivery_plan as dp
from kdev_core import events
from kdev_hud import datasource


def test_full_delivery_dataflow_renders_chain_progress(tmp_path):
    ws = str(tmp_path)
    # 1. 分类：照 full-delivery 模板产 plan
    t = lifecycle.load_template("full-delivery")
    plan = dp.parse(f"""
template_id: full-delivery
slug: e2e-auth
goal: 做认证
confidence: 0.9
reasoning: r
stages:
  - {{emp: req-architect, flow: design-flow, on: true, handoff_from: null}}
  - {{emp: dev-engineer, flow: coding-flow, on: true, handoff_from: req-architect@n8-merge}}
  - {{emp: test-engineer, flow: test-design-flow, on: true, handoff_from: req-architect@n8-merge}}
human_gates: [after-req]
""")
    # 2. lint 过
    assert lint.validate(plan) == []
    # 3. 冻结
    dp.write(ws, plan)
    # 4. 写 dispatch 事件：req done, dev running
    events.append_event(ws, "e2e-auth", events.dispatch_event(
        phase="start", slug="e2e-auth", flow="design-flow", emp="req-architect",
        dispatch_id="e2e-auth#1-req-architect", stage_index=1))
    events.append_event(ws, "e2e-auth", events.dispatch_event(
        phase="done", slug="e2e-auth", flow="design-flow", emp="req-architect",
        dispatch_id="e2e-auth#1-req-architect", status="done"))
    events.append_event(ws, "e2e-auth", events.dispatch_event(
        phase="start", slug="e2e-auth", flow="coding-flow", emp="dev-engineer",
        dispatch_id="e2e-auth#2-dev-engineer", stage_index=2))
    # HUD 需要 flow-state.json 才认 feature
    fs = Path(ws) / ".kdev" / "features" / "e2e-auth" / "flow-state.json"
    fs.parent.mkdir(parents=True, exist_ok=True)
    fs.write_text('{"slug":"e2e-auth","stories":[]}', encoding="utf-8")
    # 5. HUD 渲染链进度
    v = datasource.build_feature_view(ws, "e2e-auth")
    assert v["delivery"]["progress_label"] == "链进度 1/3"
    busy = {a["emp"]: a["busy"] for a in v["employee_activity"]}
    assert busy["dev-engineer"] is True and busy["req-architect"] is False
