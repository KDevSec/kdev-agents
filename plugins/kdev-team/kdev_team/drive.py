"""把冻结 delivery-plan 转成有序 drive 步骤（纯函数；真调 flow-driver/写事件留 SKILL.md）。"""

_HUMAN_GATE = {
    "req-architect": "after-req",
    "dev-engineer": "after-dev",
    "test-engineer": "after-test",
}


def build_sequence(plan) -> list:
    slug = plan["slug"]
    human_gates = set(plan.get("human_gates") or [])
    out = []
    for i, s in enumerate([s for s in plan["stages"] if s.get("on")], 1):
        emp, flow = s["emp"], s["flow"]
        did = f"{slug}#{i}-{emp}"
        gate = _HUMAN_GATE.get(emp)
        out.append({
            "stage_index": i,
            "emp": emp,
            "flow": flow,
            "dispatch_id": did,
            "handoff_from": s.get("handoff_from"),
            "driver_cmd": f"/kdev-flow-driver {emp} --task {slug} --slug {slug}",
            "dispatch_start_cmd": [
                "dispatch-start", flow, slug, "--emp", emp,
                "--dispatch-id", did, "--stage-index", str(i)],
            "dispatch_done_cmd": [
                "dispatch-done", flow, slug, "--emp", emp,
                "--dispatch-id", did, "--status", "done"],
            "human_gate_after": gate if gate in human_gates else None,
        })
    return out
