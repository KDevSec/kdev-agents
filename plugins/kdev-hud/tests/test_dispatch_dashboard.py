from kdev_hud import dashboard


def _model_with_delivery():
    primary = {
        "slug": "auth", "display_name": "用户认证", "feature_status": "active",
        "stories": [], "stories_done": 0, "stories_total": 0, "completion_pct": 0,
        "active": None, "runs": [], "gates": [], "alerts": [], "alert_count": 0,
        "events": [], "updated_at": "2026-01-01T00:00:00+00:00",
        "delivery": {
            "template_id": "full-delivery", "slug": "auth", "goal": "做认证",
            "stages": [
                {"emp": "req-architect", "flow": "design-flow", "on": True, "handoff_from": None},
                {"emp": "dev-engineer", "flow": "coding-flow", "on": True, "handoff_from": "req-architect@n8-merge"},
                {"emp": "test-engineer", "flow": "test-design-flow", "on": True, "handoff_from": "req-architect@n8-merge"},
            ],
            "total_on": 3, "done_count": 1, "progress_label": "链进度 1/3",
        },
        "dispatches": [
            {"dispatch_id": "auth#1-req-architect", "emp": "req-architect", "flow": "design-flow",
             "stage_index": 1, "status": "done", "started_at": "t0", "done_at": "t1",
             "subagent_tokens": 500, "tool_uses": 8, "duration_s": 60, "running": False},
            {"dispatch_id": "auth#2-dev-engineer", "emp": "dev-engineer", "flow": "coding-flow",
             "stage_index": 2, "status": "running", "started_at": "t2", "done_at": None,
             "subagent_tokens": None, "tool_uses": None, "duration_s": None, "running": True},
        ],
        "employee_activity": [
            {"emp": "req-architect", "busy": False, "dispatch_id": "auth#1-req-architect"},
            {"emp": "dev-engineer", "busy": True, "dispatch_id": "auth#2-dev-engineer"},
        ],
    }
    return {"features": [primary], "feature_count": 1, "primary": primary}


def test_render_shows_chain_progress():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    assert "链进度 1/3" in html
    assert "full-delivery" in html


def test_render_shows_dispatch_flow_with_emp_and_status():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    assert "开发工程师" in html or "dev-engineer" in html
    assert "running" in html or "进行中" in html
    assert "500" in html        # usage tokens 渲染


def test_render_marks_busy_employee():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    # 忙闲条：dev busy
    assert "忙" in html or "busy" in html.lower()


def test_render_without_delivery_omits_chain_block():
    model = _model_with_delivery()
    model["primary"]["delivery"] = None
    model["primary"]["dispatches"] = []
    model["primary"]["employee_activity"] = []
    html = dashboard.render(model, generated_at="now")
    assert "链进度" not in html       # 无 delivery 不渲染
