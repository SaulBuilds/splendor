---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# 00 — Planset Overview

> The planset is the bridge from the canonical decisions/architecture (`docs/`) to executable sprints. It
> does **not** restate the architecture — read `docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md` for that.
> It adds the three things sprints need: the normative HIC model, the acceptance framework, and the
> pillar→epic decomposition.

## Mission (one sentence)

Make Splendor the tool an AI-first creator reaches for to turn an idea into an authentic PS1-era 3D
animation or game asset — and to deploy it to the web and the chain — with governance, model-agnosticism,
and rigorous evaluation built into the grain of the software.

## The planset documents

| Doc | What it is | Normative? |
|-----|-----------|------------|
| `09_DECISIONS_LOCKED.md` | Supersession pointer to `docs/DECISIONS.md`. | **Yes** (points at canonical) |
| `00_OVERVIEW.md` | This map. | No |
| `02_HIC_MODEL.md` | The HIC governance model for Splendor's AI harness. | **Yes** |
| `03_ACCEPTANCE_FRAMEWORK.md` | How acceptance criteria are written so they forbid mocks/fluff (D-8.2). | **Yes** |
| `01_PILLARS_AND_EPICS.md` | The 7 pillars decomposed into epics + a sprint sequence. | Planning (advisory) |

## Reading order for a new contributor

`../AGENT_ENTRY.md` → `../../docs/DECISIONS.md` → `../../docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md`
→ `09_DECISIONS_LOCKED.md` → `02_HIC_MODEL.md` → `03_ACCEPTANCE_FRAMEWORK.md` → `01_PILLARS_AND_EPICS.md`
→ the active sprint SCOPE.

## The spec-driven contract (D-8.2)

No feature is more important than another; all seven pillars ship in the same v1 release and are tested.
Everything is **wired end-to-end on the first full sprint pass** — there is no "we'll wire it later" phase.
AI/Eval + governance is proof-critical (the rest of the stack is proven in the existing Citrate
architecture) and gets the most rigor. Acceptance criteria forbid misinterpretation and mock features
(`03_ACCEPTANCE_FRAMEWORK.md`).

## The design loop (D-8.5)

Claude Code (behavior/wiring, final say on how features work) → Claude Design (expression, prototype) →
Emma (final say on design/UX and whether it serves real game-maker workflows) → back to Claude Code to wire
to the real pillars. The contract is `../../docs/handoff/CLAUDE_DESIGN_HANDOFF.md`.
