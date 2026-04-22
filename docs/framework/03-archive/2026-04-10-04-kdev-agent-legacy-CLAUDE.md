# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KDev-Agent is an AI-driven agile development workflow framework. Core philosophy: "AI主导执行，人来主导规则" (AI drives execution, humans define rules). It fuses multiple open-source frameworks (BMAD, OMC, Superpowers, Gstack, etc.) into a six-layer architecture with Compound Engineering at its core.

**Current status**: Design & documentation phase, entering Sprint 0. No source code yet — all deliverables are architecture documents in `docs/`. The authoritative documents are:
- **Architecture**: `docs/01-design/2026-04-08-03-KDev融合架构设计.md` (v3.0.1)
- **Sprint 0 Plan**: `docs/01-design/2026-04-10-01-Sprint0计划.md`
- **Reference workflow**: `/home/lyadmin/Projects/kdev-skill/docs/standardized-dev-flow.md` (IR→SR→AR→TDD)

## Repository Structure

```
docs/
├── 00-research/    # Framework comparison, ecosystem analysis (9 docs)
├── 01-design/      # Architecture & design decisions (6 docs, v3.0.1 + Sprint 0 plan)
├── 02-reviews/     # Multi-model review reports (7 docs)
├── 03-archive/     # Superseded implementation plans (3 docs)
└── 04-references/  # BMAD usage guide, reference workflow
```

All documentation is in Chinese (Mandarin) with technical English terms. Naming convention: `YYYY-MM-DD-NN-Title.md`.

## Six-Layer Fusion Architecture

| Layer | Name | Purpose | Source Frameworks |
|-------|------|---------|-------------------|
| 1 | Spec Engine (规格引擎) | Requirements clarification, spec generation | BMAD + Superpowers |
| 2 | Planning Engine (计划引擎) | Task decomposition, TDD planning | BMAD + Superpowers |
| 3 | Execution Gate (执行门控) | HARD-GATE: user approval before implementation | Superpowers |
| 4 | Execution Engine (执行引擎) | Subagent TDD loops, code implementation | Superpowers + OMC |
| 5 | Quality Assurance (质量保障) | UT/IT/E2E testing, security audit | Superpowers + Gstack |
| 6 | Memory System (记忆系统) | Knowledge persistence, compound learning | OMC + Gstack + KDev |

## Command System (14 commands, aligned with IR→SR→AR flow)

### Phase 1 Planning
| Command | Purpose | Deliverable |
|---------|---------|-------------|
| `/kdev:ir` | Collect initial requirements | IR doc |
| `/kdev:sr` | Break down story requirements + coarse AR | SR CSV + coarse AR CSV |
| `/kdev:prototype` | Overview UI prototype | HTML prototype |
| `/kdev:review` | Human review gate (SR + AR + prototype) | Review approval |
| `/kdev:plan` | Output iteration plan | Iteration plan doc |

### Phase 2 Execution (per iteration)
| Command | Purpose | Deliverable |
|---------|---------|-------------|
| `/kdev:ar` | Detailed AR + high-fidelity prototype + tech design | AR CSV + HTML + design doc |
| `/kdev:align` | Requirements alignment (O-S-U-R-A) + revision | Alignment confirmation |
| `/kdev:dev` | TDD full cycle (Red→Green→Refactor) | Tests + implementation code |
| `/kdev:e2e` | E2E system testing | Test report |
| `/kdev:accept` | System acceptance + code review | Acceptance report |

### Cross-cutting
| Command | Purpose |
|---------|---------|
| `/kdev:start` | Entry point: check state.md, select phase |
| `/kdev:ship` | Release |
| `/kdev:recap` | Retrospective + knowledge distillation |
| `/kdev:security` | Security audit |

### State Machine
```
Phase 1: INIT → P1-IR → P1-SR → P1-PROTOTYPE → P1-REVIEW → P1-PLAN
                                                     ↑
                                                [Human gate]

Phase 2: E1-AR → E2-ALIGN → E4-DEV → E6-E2E → E7-ACCEPT → NEXT-ITERATION
```

## Key Design Concepts

### HARD-GATE
No code, no scaffolding, no implementation skills invoked until user approves the design. Located between Phase 1 (Planning) and Phase 2 (Execution).

### Compound Engineering
`Plan (80%) → Work (20%) → Review → Compound → Repeat`. Every bug fix, decision, and pattern is captured so each iteration makes the next easier.

### Three-Layer Requirements (IR→SR→AR)
- **IR** (Initial Requirements): Raw user needs, collected via brainstorming
- **SR** (Story Requirements): Structured stories with acceptance criteria, priority, story points
- **AR** (Acceptance Requirements): Detailed GWT scenarios, UI prototypes, tech design — produced per iteration

### Five-Level Memory Architecture
- **Level 0**: Runtime memory (session-scoped, ephemeral)
- **Level 1**: Knowledge graph (`.kdev/knowledge-graph/`)
- **Level 2**: Learning deposits (`.kdev/learnings/`)
- **Level 3**: Project memory — `questions-log.md`, `gotchas.md`, `state.md`, `daily-logs/`
- **Level 4**: Skill library (`.kdev/skills/`)
- **Level 5**: Global memory (`~/.kdev/`)

## Current Phase: Sprint 0

Sprint 0 validates v3.0.1 architecture design using token-statistics as the dogfood project, manually orchestrating existing plugins (BMAD + Gstack + Superpowers). See `docs/01-design/2026-04-10-01-Sprint0计划.md` for full details.

**Approach**: Minimal recording framework (`.kdev/` with state.md, questions-log, gotchas, journal) + manual plugin orchestration through the full workflow.

**After Sprint 0**: Review report → revise v3.0.1 design → decide tech form factor → implement first batch of KDev features → use KDev to develop kdevsec (1→N validation).

## Framework Integration Roles

| Framework | Role in KDev |
|-----------|-------------|
| **BMAD** | Core workflow backbone — agile phases, gating, artifacts |
| **OMC** (oh-my-claudecode) | Technical infra — hooks, state machine, cross-session persistence |
| **Superpowers** | Execution quality — TDD, brainstorming, writing-plans, subagent-driven-dev, HARD-GATE |
| **Gstack** | Multi-role stage reviews at every phase + /qa + /cso + /ship + /learn |

## Planned Tech Stack (from .gitignore)

- **Runtime**: Node.js / TypeScript
- **Build output**: `dist/`, `bridge/*.cjs`
- **Testing**: vitest (UT), supertest (IT), Playwright (E2E)
- **Project state**: `.kdev/` directory (memory, state, skills)
- **Global config**: `~/.kdev/` (user preferences)

## Documentation Conventions

- All docs are Markdown in Chinese with date-number prefix naming
- `docs/01-design/` is the active design — `03-archive/` contains superseded docs
- Review documents in `02-reviews/` track version evolution: v1.0 → v2.0 → v3.0 → v3.0.1
