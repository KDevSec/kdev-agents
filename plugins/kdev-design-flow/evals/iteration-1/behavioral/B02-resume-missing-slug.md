# B02: --resume on missing slug

## Steps observed

1. **Step 0 parse:** `--resume` flag correctly identified; mode set to "resume"; slug extracted as `zzzz9999-fake-slug`. No `feature_name` required (SKILL.md says `--resume` skips the slugify step). Parse: CORRECT.

2. **Resume mode entered:** Yes — SKILL.md Step 0 says "如果 `--resume <slug>`：跳到'恢复模式'段", so execution jumps directly to the "恢复模式" section, skipping Steps 1–4 (dep check, init, .gitignore, main loop entry).

3. **read_state attempt result:**
   ```
   Got error: FlowStateError: no flow-state.json at /tmp/kdev-design-flow-eval-b02/.kdev/design-flow/zzzz9999-fake-slug/flow-state.json
   ```

## What the skill outputs to the user

The SKILL.md "恢复模式" section only specifies two branches after `read_state`:
- `status == "in_progress"` → continue from `current_stage` + `current_iter`
- `status == "aborted"` → prompt user to manually edit status field

It does **not** specify what to do when `read_state` raises `FlowStateError` (i.e., the file does not exist at all). The skill has no explicit catch/fallback for this case.

**Expected graceful output (what should happen):**

```
❌ 找不到流程记录：slug "zzzz9999-fake-slug" 不存在。
路径：/path/to/.kdev/design-flow/zzzz9999-fake-slug/flow-state.json

请检查 slug 是否拼写正确。可用 slug 列表：
  （当前工作目录下 .kdev/design-flow/ 中无任何已有流程）

如需新建流程，请去掉 --resume 并提供 feature_name：
  /kdev-design-flow <feature_name>
```

**What actually happens (current SKILL.md):** The skill will hit an unhandled `FlowStateError` exception from `read_state` — no branch in the resume section catches it. Behavior is undefined: the skill will likely surface a raw Python traceback or silently fail, giving the user no actionable guidance.

## Verdict

- [ ] PASS — graceful failure with helpful message
- [x] FAIL — crashed / unhelpful error / created state when it shouldn't

**Reason:** SKILL.md's "恢复模式" section has no guard for the case where `flow-state.json` does not exist. `read_state` raises `FlowStateError` immediately, and the skill provides no catch path, no user-facing message, and no suggested remediation for a missing slug.

## Issues

1. **Missing error branch in "恢复模式":** The section jumps straight to checking `status`, but never handles the prerequisite failure: the file not existing. A third branch is needed before the status checks:

   > **Suggested addition to SKILL.md "恢复模式" section (insert as new item 0 / before item 1):**
   >
   > ```
   > 0. 用 read_state 读取 flow-state.json。若抛出 FlowStateError（文件不存在）：
   >    向用户输出：
   >    ❌ 找不到 slug "{{slug}}" 的流程记录，请确认 slug 拼写是否正确。
   >    （可在 .kdev/design-flow/ 目录下查看已有的 slug 列表）
   >    然后停止，不再继续执行。
   > ```

2. **No slug discovery helper:** The skill gives no way for the user to know what slugs are available. A `--list` flag or a hint to `ls .kdev/design-flow/` would dramatically improve the UX for resume-on-typo cases.

3. **SKILL.md ordering ambiguity:** Step 0 says "如果 `--resume <slug>`：跳到恢复模式段" which implies the dep check (Step 1) is skipped in resume mode. This may be intentional (no new stages will be launched yet) but should be explicitly stated — if the resume drops back into Stage 2/3/4, those sub-skills (`spec-kit:specify`, `spec-kit:plan`) will be needed and the dep check should still run.
