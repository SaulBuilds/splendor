---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
repo: splendor
tier: T1
---

# Agent Entry — Splendor

> Start here whenever you (human or AI) are working in **Splendor**.

## What this repo is

**A hard fork of Blender for AI-first retro creators.** Splendor does everything Blender does, and adds an
AI harness that plans and acts through a typed intent DSL, a model-agnostic backend, a first-class
eval/benchmark SDK, HIC governance, a node/edge language that unifies Blender nodes with LangGraph agent
workflows, and a deploy layer that ships work to the web and CitrateNetwork (provenance, mint, licensing,
pinned storage). Local-first, spec-driven, wired end-to-end on the first pass — **no mocks**.

Primary user: **AI-first "vibe" creators** making **PS1-era low-poly** 3D animation and game assets.
Must excite Blender pros without alienating them.

Repo tier: **T1** — keys/identity (AA), on-chain money, binary distribution, agent governance.

## Fork status

Fork: **https://github.com/SaulBuilds/splendor** (from `blender/blender`, the official GitHub mirror of the
canonical `projects.blender.org` repo). **Not yet cloned locally** ([D-8.6]) — the ~1.3 GB pull is deferred
to the start of implementation (Sprint SPL-S0). This workspace currently holds **planning artifacts only**;
`docs/` + `.agentile/` fold into the fork checkout when it lands (see "Reconciling with the fork" below).

## What to read, in order

1. **This file** (you're here).
2. **`../README.md`** — honest current status.
3. **`../CLAUDE.md`** — the hard rules. Rules 1, 2, 4, 5, 8 are the ones people get wrong.
4. **`../docs/DECISIONS.md`** — canonical decision ledger (the 31 founding decisions + business §9).
5. **`../docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md`** — the 7 pillars, data flow, v0 slice, grounded
   in Blender's real extension surface.
6. **`planset/`** — `09_DECISIONS_LOCKED.md` first (supersedes), then `00_OVERVIEW.md`, `02_HIC_MODEL.md`
   (normative — read before writing anything that lets an agent act), `03_ACCEPTANCE_FRAMEWORK.md`,
   `01_PILLARS_AND_EPICS.md`.
7. **`../docs/business/BUSINESS_MODEL_AND_GPL.md`** — the GPL boundary that constrains what code may be closed.
8. **The active sprint** — `sprints/active/sprint-spl-s0/SCOPE.md`.
9. **`../docs/handoff/CLAUDE_DESIGN_HANDOFF.md`** — the wiring contract for Claude Design + Emma.

## Core invariants

- **I-1 (one action API):** the in-app agent and external MCP clients drive the *same* governed DSL/operator
  surface. There is no second, ungoverned path. A source-scan test should assert it.
- **I-2 (gate before act):** every AI action passes the HIC policy gate **before execution** and emits a
  decision record. Prompt-level instructions are not controls.
- **I-3 (HIC per action):** every record carries principal, grant, and HIC level. No live grant → recorded
  `ungoverned` and surfaced.
- **I-4 (no mocks):** every shipped surface is wired to a real model call, operator, chain method, or an
  honest error. Nothing renders fabricated data.
- **I-5 (model-agnostic):** no feature names a model/provider; everything routes through the backend
  capability contract + Router. The Router works offline (local-first).
- **I-6 (eval is load-bearing):** outputs are scored by the Eval SDK; scores are traceable and, when
  deployed, attestable. A claim of quality without an eval record is not a claim.
- **I-7 (minimal fork tax):** default to Python/extensions; every C/C++ diff is justified in its PR and
  tracked as cost against upstream.

## Where the code will live (planned)

- Fork core (C/C++): render passes, GPU retro shaders, DNA structs, embedded MCP/agent bridge — only where
  an extension genuinely cannot.
- `scripts/addons/splendor_*` (Python/extensions): retro nodes, DSL, in-app agent, node/edge language,
  eval SDK, deploy adapters — the bulk of Splendor.
- Non-GPL server code (services, at arm's length, [D-9.8]) lives in **separate repos**, not here.

## Before you write code

Ask: **does this let an agent do something?** If yes, the policy gate, the grant check, and the decision
record are part of the *same* PR — not a follow-up. Then ask: **could this be a Python extension instead of
a C diff?** If yes, do that. Then ask: **what is the objective, negative-controlled acceptance criterion?**
(`planset/03_ACCEPTANCE_FRAMEWORK.md`) — write it before the code.

## Reconciling with the fork (one-time, at SPL-S0 start)

The fork has its own git history. Cleanest path when implementation begins:
1. `git clone https://github.com/SaulBuilds/splendor.git` into a fresh checkout.
2. Copy this workspace's `docs/`, `.agentile/`, `CLAUDE.md`, `README.md` into it on a branch.
3. PR the planning layer onto the fork; the owner merges. From then on, this workspace *is* the fork.
Until then, treat this workspace as the planning source of truth.
