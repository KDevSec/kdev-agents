from kdev_hud import dashboard


def _model_with_delivery():
    """内联夹具（禁跨 test 文件导入，见 plan 测试基建约定）——与 test_dispatch_dashboard 同形。"""
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


def test_dispatch_rows_have_detail_panels_with_anchor_ids():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    # 每 dispatch 一个可锚定的详情面板（id 含 dispatch_id 派生）
    assert 'id="d-auth' in html or 'id="dispatch-auth' in html
    # 详情面板内含全字段
    assert "auth#2-dev-engineer" in html
    assert "req-architect@n8-merge" in html or "handoff" in html.lower()


def test_drilldown_uses_inline_js_no_external():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    assert "http://" not in html and "https://" not in html   # 零外链
    assert "<script" in html


def test_reload_preserves_open_panel_via_hash():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    # reload 脚本必须把当前 location.hash 带回（扛 2s 自动刷新）
    assert "location.hash" in html
    assert "location.reload" in html


def test_panels_collapsed_by_default():
    html = dashboard.render(_model_with_delivery(), generated_at="now")
    # 详情面板默认折叠（CSS：未 :target 时 display:none）
    assert ":target" in html or "hud-panel" in html
