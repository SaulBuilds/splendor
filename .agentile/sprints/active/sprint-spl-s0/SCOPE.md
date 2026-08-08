---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: planned
sprint: SPL-S0
---

# Sprint SPL-S0 — Spine: fork build + the seven seams

> **Sprint goal.** Turn the architecture from a document into a *buildable skeleton*: Splendor builds from
> the fork on all three platforms, and each of the seven pillars has a **thin but real** seam — an
> interface exercised by one honest end-to-end path and one negative control — so every later feature has a
> real thing to plug into. **No feature is finished here; every seam is real, none is mocked.**

Normative spec: `../../../../docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md`. Decisions:
`../../../../docs/DECISIONS.md`. Acceptance rules: `../../planset/03_ACCEPTANCE_FRAMEWORK.md`.

**Status: `planned`** — this SCOPE is written; it flips to `active` when the fork is cloned (WP-0) and the
owner greenlights. The measured-reality table below is filled as WP-0 lands.

## Measured against reality before writing this

| What the plan assumes | What is actually true (to be checked in WP-0) |
|---|---|
| The fork is cloneable + buildable locally | Fork exists (`SaulBuilds/splendor`, ~1.3 GB). **Not yet cloned** ([D-8.6]). Blender's CMake build + `lib/` deps not yet fetched/verified on this Linux/NVIDIA box. **Unverified.** |
| We can add a Python extension without a C diff | Blender's extensions platform (4.2+) supports this; **to confirm against the exact fork revision.** |
| An embedded MCP/agent bridge may need a C-level hook | Unknown until we see where a long-lived in-process server can live without fighting Blender's event loop. **To investigate in WP-3.** |
| Local models are reachable offline | llama.cpp/Ollama present on dev box? **To verify.** OpenAI-compatible shape assumed as the local lingua franca. |
| CitrateNetwork testnet + pinning are reachable | Endpoints/credentials for testnet + Citrate pinning **to confirm** before any P7 seam claims liveness. |

> Per the framework (§4), each row above is resolved to a fact in WP-0 and the table updated **before** the
> dependent WP is built. A seam may not claim liveness against a dependency whose reachability is unverified.

## Work packages — each a real seam with a negative control

Each WP is a vertical sliver, not a layer. "Done" = objective criterion met **and** its negative control
fails on a broken build (`03_ACCEPTANCE_FRAMEWORK.md` §3). None of these is a full feature.

| # | WP | Deliverable (thin but real) | Negative control | Status |
|---|---|---|---|---|
| **S0.0** | Clone + reconcile | Fork cloned; `docs/` + `.agentile/` folded onto a branch; owner merges. Reconciliation per AGENT_ENTRY. | — (enabling) | ☐ |
| **S0.1** | Build on 3 platforms + CI | Splendor builds on Linux/Windows/macOS; a CI job produces artifacts; GPL source-publish step present. | A build with the retro shader syntactically broken **fails CI**, not silently skips. | ☐ |
| **S0.2** | One retro shader (P1 seam) | A single real retro effect (palette quantize *or* affine warp) as a GPU pass toggled in the viewport. | Palette set to 17 on a "≤16" target is detectable by the deterministic scorer (feeds S0.6). | ☐ |
| **S0.3** | Governed action API + HIC gate (P2/P6 seam) | One typed DSL intent (`set_palette`/`snap_vertices`) routed through the single action API; every call passes the HIC gate and emits a decision record. | Removing the grant flips the action to `require-approval`; a second, un-gated code path is caught by a source-scan test (I-1). | ☐ |
| **S0.4** | MCP server + client (P2 seam) | Splendor exposes the S0.3 intent as one MCP tool (external Claude Code can call it) **and** consumes one external MCP tool. Same governed path as in-app. | Calling the MCP tool without a grant yields the same `ungoverned`/`require-approval` behavior as in-app — not a bypass. | ☐ |
| **S0.5** | Backend Router seam (P3 seam) | A text plan runs through the Router → llama.cpp/Ollama via the OpenAI-compatible shape; capability contract in place; **works offline** ([D-2.4]). | Offline + cloud-only route selected → honest "backend unavailable" error, not a hang or fabricated result (framework §2). | ☐ |
| **S0.6** | Eval SDK boundary (P4 seam) | The Eval SDK, importable standalone, scores one output with one deterministic criterion (tri/palette) and records it reproducibly under a seed. | Corrupting the reference/criterion drops the score below threshold; a fixed-seed rerun is bit-identical (repro criterion). | ☐ |
| **S0.7** | Node/edge ⇄ LangGraph seam (P5 seam) | One agent-workflow node graph (prompt→model→eval) serializes to a LangGraph-compatible artifact and round-trips back to the same graph. | A hand-edited invalid graph fails validation on import rather than loading a broken graph. | ☐ |
| **S0.8** | Chain/pinning/identity adapter interface (P7 seam) | The composable chain interface + a pin/attest call against **Citrate testnet + pinning** (or an honest error if unreachable per WP-0). AA sign-in stubbed *honestly* (named "not yet", not faked). | A tampered asset fails hash verification on retrieval; an unreachable endpoint shows an honest error, never a fake success. | ☐ |
| **S0.9** | Upstream-diff surface report | A report of the C/C++ diff introduced vs upstream Blender (Rule 7 cost tracking) + justification per diff. | — (a file, not a claim: the report exists and lists each C change) | ☐ |

## Exit gate (defined now, not at close)

- Splendor **builds and launches** on Linux/Windows/macOS from the fork (S0.1).
- **Every** pillar seam S0.2–S0.8 has one honest end-to-end path **and** a passing negative control.
- The **single governed action API** is the only way an agent acts, asserted by a source-scan test (I-1).
- The Router **works offline** (S0.5); no feature hardcodes a model (Rule 6).
- The upstream C-diff report exists (S0.9); no undocumented C change.
- No mocked surface anywhere; anything unbuilt is named honestly (Rule 1).

## Explicitly NOT in this sprint

- Any *complete* feature: the retro engine, the agent's real planning loops, training, the leaderboard, the
  web runtime, real mint/marketplace flows. Those are SPL-S1+. S0 ships seams, not products.
- The v0 vertical slice as a user-facing flow — that is **SPL-S1**; S0 only proves the seams it will use.
- Any counsel-gated surface (mint/marketplace/token/custody) beyond a testnet provenance/pin call ([D-9.7]).
- Design polish — S0 surfaces are functional stubs pending the Claude Design/Emma loop (E-X2).

## Risks

| # | Risk | Mitigation |
|---|---|---|
| R-A | Blender's build on this exact fork rev may fight the toolchain/deps | WP-0 verifies the full CMake+`lib/` build before any dependent WP; unverified = not claimed live. |
| R-B | An in-process MCP/agent server may conflict with Blender's event loop | WP-3 investigates placement (thread/sidecar/embedded) before committing a C diff; prefer the smallest surface (Rule 7). |
| R-C | "Thin seam" tempts mock stubs that look real | The framework forbids it: each seam has a negative control and an honest-error path; source-scan asserts one action API (Rule 1, I-1). |
| R-D | CitrateNetwork testnet/pinning may be unreachable during S0 | S0.8 shows an honest error rather than faking success; liveness claimed only after WP-0 confirms endpoints. |
| R-E | Scope creep from "wire everything" into "finish everything" | Explicit NOT-in-scope list; S0 is seams-only; features are SPL-S1+. |
