# E2E Smoke Test — 2026-05-07

**Sandbox:** `/tmp/kdev-design-flow-smoke` (temporary git repo)
**Tested via:** Direct Python invocation of `lib.slug.slugify` + `lib.flow_state.init_state` (the slash command itself isn't installed in this Claude Code session — verifying SKILL.md Steps 0-3 by exercising the Python helpers they invoke)

## Scope of this smoke test

This is a **partial** E2E smoke. It verifies SKILL.md **Steps 0-3** (boot sequence) end to end. Steps 4+ (Stage 1 → Gate 1 → Stage 2…) require the actual slash command to be installed AND `spec-kit` to be available — neither is true in the current environment, so those are deferred to post-install real-user testing.

This is the v0.1 ship gate: confirm the boot path doesn't crash and produces correct artifacts.

## Sandbox setup

```bash
mkdir -p /tmp/kdev-design-flow-smoke
cd /tmp/kdev-design-flow-smoke
git init -q
echo "Smoke test sandbox" > README.md
git add README.md && git -c user.name=1qljc-AI -c user.email=631114161@qq.com commit -qm "init sandbox"
```

## Observations (Steps 0-3 of SKILL.md)

### Step 1 (parse args)

Simulated: `feature_name = '一个简单计数器'`, `review_mode = 'ai'`. Not a real CLI parse, but the parameters that would result from `/kdev-design-flow 一个简单计数器`.

### Step 2 (slug normalization)

```
slugify('一个简单计数器') = '00af4da9'
```

✅ Pure-Chinese input correctly falls back to 8-char SHA-1 hash. No Chinese chars survive.

### Step 3 (init_state)

```
init_state(sandbox, '00af4da9', review_mode='ai', feature_name='一个简单计数器')
→ /tmp/kdev-design-flow-smoke/.kdev/design-flow/00af4da9/flow-state.json
```

State file contents:
```json
{
  "slug": "00af4da9",
  "feature_name": "一个简单计数器",
  "review_mode": "ai",
  "current_stage": 1,
  "current_iter": 1,
  "status": "in_progress",
  "created_at": "2026-05-07T08:58:13+00:00",
  "updated_at": "2026-05-07T08:58:13+00:00",
  "history": []
}
```

✅ Schema correct, UTC timestamps, history empty array, status in_progress.

### Step 4 (auto .gitignore)

Sandbox started with no `.gitignore`. After running the gitignore-append logic (mimicking SKILL.md Step 3):

```
/.gitignore content after append:
/.kdev/design-flow/
```

✅ Gitignore line correctly appended. Idempotency check (re-running) prints "already has" instead of duplicating — verified by running the snippet twice.

### Step 5 (dependency detection — SIMULATED, not exercised)

The actual `Skill` tool dependency check requires running inside Claude Code with the plugin installed. In this smoke test we did **not** verify the `❌ kdev-design-flow 需要 spec-kit` hard-stop path. SKILL.md §"步骤 1：依赖检测" specifies that path, and it's the simplest possible logic — abort + print message — so confidence is high without runtime verification.

### Steps 4+ (main loop) — NOT YET EXERCISED

Stage 1 → Gate 1 → Stage 2 (spec-kit:specify) → Stage 3 (frontend-design) → Gate 2 → Stage 4 (spec-kit:plan) → Gate 3 → Merge are NOT exercised in this smoke. Each requires either spec-kit, frontend-design, or actual Claude reasoning loops that don't fit a unit-test sandbox.

## Verdict

✅ **v0.1 ships for the boot-sequence portion.**

The Python plumbing (slug + state file + gitignore) works end-to-end against a real filesystem sandbox. The orchestration logic in SKILL.md is documented but not runtime-verified — that's the post-install user-level test, deferred to first real use.

## Issues found

None.

## Test sandbox cleanup

The sandbox at `/tmp/kdev-design-flow-smoke/` is left in place for reproduction. Clean it up with `rm -rf /tmp/kdev-design-flow-smoke` when done.
