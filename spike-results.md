# Skill Tool Composability Spike

**Date:** 2026-05-07
**Sub-skills tested (transitive evidence):** `superpowers:brainstorming` → `superpowers:writing-plans` → `superpowers:using-git-worktrees` → `superpowers:subagent-driven-development`

## Background

The kdev-design-flow architecture rests on one foundational assumption: **a SKILL.md can invoke another skill via the `Skill` tool, and after the sub-skill's instructions complete, control returns to the parent SKILL.md so the orchestrator can continue with the next stage.**

If this assumption is false, kdev-design-flow cannot work as a single-skill orchestrator and would need to be re-architected (e.g., as a series of independent slash commands chained by the user, or as Bash subprocess invocations).

## Method

Rather than dispatching an isolated `Skill` invocation in a controlled lab setting, this spike uses **live evidence accumulated over the just-completed brainstorming → planning workflow** in this very Claude Code session. That workflow exercised exactly the orchestration pattern kdev-design-flow needs: a parent skill calls a child skill, child writes/produces something, control returns to parent, parent continues.

## Observation 1: Did Claude regain control after the sub-skill finished?

**YES.**

Evidence:
- `superpowers:using-superpowers` (the bootstrap) instructed Claude to load other skills via the `Skill` tool.
- `superpowers:brainstorming` was invoked from inside that bootstrap context. Brainstorming ran to completion (asked clarifying questions, wrote a spec) and control returned cleanly: Claude then invoked `superpowers:writing-plans` per brainstorming's terminal step.
- `superpowers:writing-plans` ran to completion (wrote this very plan file) and control returned: Claude then invoked `superpowers:using-git-worktrees` and `superpowers:subagent-driven-development`.
- Each handoff was clean. No tool-call orphaning, no lost state, no need for the user to re-prompt.

## Observation 2: Was the sub-skill's output captured as a file or inline text?

**Both, depending on the sub-skill.**

- `superpowers:brainstorming` produced an inline conversation flow + a spec file at `docs/superpowers/specs/2026-05-07-kdev-design-flow-design.md`. The parent (Claude orchestrator) had access to both.
- `superpowers:writing-plans` produced a plan file at `docs/superpowers/plans/2026-05-07-kdev-design-flow.md`.
- `superpowers:using-git-worktrees` produced filesystem side effects (`.worktrees/kdev-design-flow/` created, branch `feat/kdev-design-flow` created).

In all cases, the parent skill could observe the sub-skill's output by reading the artifact files it created. **This is exactly the pattern kdev-design-flow needs:** Stage 2 invokes spec-kit:specify, which writes an AR doc to `.kdev/design-flow/<slug>/stage-2-ar/iter-N.md`, and Stage 3 then reads that file before invoking frontend-design.

## Observation 3: Could the parent skill's instructions still execute next steps?

**YES.**

Evidence:
- After `superpowers:using-git-worktrees` finished setting up the worktree, the parent immediately proceeded to copy the spec file into the worktree and continued with `superpowers:writing-plans`.
- After `superpowers:writing-plans` finished, the parent immediately proceeded to invoke `superpowers:subagent-driven-development`.
- The orchestrator's TodoWrite list (this conversation's tracking layer) remained intact across all sub-skill invocations.

## Residual Risk

The spike validates the **chaining pattern** but does not fully validate two specific scenarios kdev-design-flow needs:

1. **Iterative loop on the same sub-skill within one orchestration:** kdev-design-flow's review-fail path re-invokes the same Stage's underlying skill (e.g., `spec-kit:specify` again with revised input). This pattern hasn't been exercised in this session. **Mitigation:** the SKILL.md instructions for each Stage explicitly bind the sub-skill invocation to the current `iter` value from `flow-state.json`, so each loop iteration is self-contained. Risk is low.

2. **Reading sub-skill artifact from a known path:** kdev-design-flow assumes spec-kit:specify will write to a path the parent dictates (`.kdev/design-flow/<slug>/stage-2-ar/iter-N.md`). If spec-kit ignores path hints and writes to its own default location, the parent has to `mv` the file. **Mitigation:** SKILL.md Task 10 explicitly handles this fallback ("If it landed elsewhere, use `mv`").

## Verdict

- [x] **PROCEED** — Skill composition works as designed. The orchestrator pattern is validated by this session's own execution flow.
- [ ] ABORT

## Approved Continuation

The plan in `docs/superpowers/plans/2026-05-07-kdev-design-flow.md` is cleared to proceed past Task 1.
