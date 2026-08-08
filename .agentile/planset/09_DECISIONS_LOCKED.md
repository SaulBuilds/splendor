---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# 09 — Decisions Locked

> **This file is the supersession pointer.** The canonical, authoritative decision record is
> **`../../docs/DECISIONS.md`**. Where any planset doc, SCOPE, essay, or code comment conflicts with
> `docs/DECISIONS.md`, **`docs/DECISIONS.md` wins.** Amend decisions there (by dated edit), not here.

## Why the canonical ledger lives in `docs/`, not the planset

Rule 9 (link, don't copy). The 31 founding decisions + the resolved business model (§9) were captured in
`docs/DECISIONS.md` during the founding interview and business memo. The planset *points* at them so there
is exactly one source of truth. Copying them here would create drift.

## Locked as of 2026-08-08

All 8 interview themes (D-1 … D-8) and the business model (D-9) are **locked** per `docs/DECISIONS.md`.
The load-bearing ones an agent must not silently contradict:

- **D-1.1** Hard fork, own identity. **D-1.2** PS1 low-poly is the north star. **D-1.3** AI-first vibe
  creators are the tip of the spear (without alienating Blender pros).
- **D-2.3** Hybrid DSL over nodes+ops is the AI action surface. **D-2.4** Local-first, router-ready.
- **D-3.3** Eval is a first-class pillar + shipped SDK. **D-4** HIC (not HITL), levels HIC-0…3 + X.
- **D-5.2** CitrateNetwork-first via a composable chain interface. **D-5.4** Account-abstraction identity.
- **D-6.2** One node/edge language ⇄ LangGraph, spanning the node editor and the MCP harness.
- **D-7.1** MCP transport + LangGraph-compatible graph format.
- **D-8.2** Fully spec-driven; everything wired end-to-end on the first pass; no fluff/mock features.
- **D-9** Open GPL app + Zone-B services + Zone-C Citrate protocol; token off-table (counsel-gated).

## Open (not locked) — require an owner call before they bind

- Business-model regulatory items D-9.6 / 9.7 / 9.8 / 9.9 are **directional intent gated on counsel**, not
  cleared facts. Do not treat them as legally settled.
- Per-sprint Blender subsystem code walks (owed) — each sprint grounds itself against the real code before
  scoping (see `03_ACCEPTANCE_FRAMEWORK.md`, "measured against reality").
