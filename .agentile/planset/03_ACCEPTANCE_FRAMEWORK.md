---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# 03 — Acceptance Framework (normative)

> The mechanism that makes [D-8.2] real: *everything wired end-to-end on the first pass, no fluff/mock
> features, acceptance criteria that forbid misinterpretation.* This is how a Splendor work package is
> declared done. If a criterion here is inconvenient at the gate, that is the framework working.

## 1. The work-package (WP) contract

A WP is a **vertical slice**, not a horizontal layer. It cuts through every pillar it touches — UI →
DSL/operator → governance gate → model/engine → eval → (deploy, where relevant) — and leaves each end
real. "Backend now, UI later" is not a WP; it is two half-features that each lie about the other.

**A WP is not done until:**
1. Its acceptance criteria are **objective** — a reviewer can check them without asking the author what was
   meant (§2).
2. Its check **fails on a deliberately broken build** — the *negative control* (§3). A check that cannot
   fail proves nothing.
3. It is **wired end-to-end** — no mock data, no stub that renders as if live (Rule 1). If a dependency
   isn't ready, the surface shows an honest error, not fabricated success.
4. Its **governance is in the same PR**, if it lets an agent act (I-2): the gate, the grant check, the
   decision record — not a follow-up.
5. Its **data sources are traceable** (Rule 11): every number it renders names its origin.

## 2. Writing a criterion that forbids interpretation

Bad (interpretable / mockable) → Good (objective / negative-controllable):

| ❌ Bad | ✅ Good |
|--------|--------|
| "A mint button exists." | "Minting produces a token whose metadata URI resolves to a pinned glTF whose SHA-256 equals the exported file's, and whose JSON embeds the recorded eval-score object." |
| "The agent can make a PS1 asset." | "Given the prompt fixture P-1, the agent emits a DSL intent that compiles to a mesh with ≤500 tris, affine mapping on, and a ≤16-color palette — asserted by the deterministic scorer, and the negative control (palette=17) fails." |
| "Eval scoring works." | "For golden set G-retro-v1, the harness returns a score per item; swapping the reference image drops the similarity metric below threshold (negative control) and the run is reproducible under a fixed seed." |
| "Local models are supported." | "With the network disabled, a text plan completes via the llama.cpp backend; enabling a cloud-only route while offline yields an honest 'backend unavailable' error, not a hang or a fake result." |

Rule of thumb: a good criterion names **the input**, **the observable output**, **the threshold/assertion**,
and **the broken variant that must fail**.

## 3. Negative controls (the anti-mock)

Every WP ships at least one negative control: a deliberately broken input/build that the WP's own check
**must reject**. Examples: mismatched CREATE2 code reverts; palette-over-budget fails the scorer; a removed
governance grant flips the action to `require-approval`; a corrupted pinned asset fails hash verification.
The negative control is the evidence the test tests something. WPs without one are not accepted.

## 4. Exit gates — measured against reality *before* building

Before a sprint's SCOPE is written, its assumptions are checked against the actual code/chain/tooling and
recorded in a **"Measured against reality"** table (see the SPL-S0 SCOPE for the pattern). This is the
"half a gate is not a gate" discipline: write down the honest state *before* it becomes inconvenient. A gate
criterion is defined precisely in the SCOPE, not left to interpretation at close.

## 5. The AI-specific traps (proof-critical pillar — D-3.3)

Because AI/Eval is the differentiator, it gets extra scrutiny:

- **A check that cannot fail is an anti-control.** A VLM-as-judge that scores everything "PS1: yes" is
  worse than none — it manufactures confidence. Judges and metrics get **meta-eval**: a labeled set where
  the judge must disagree with bad output.
- **Reproducibility is a criterion, not a hope.** Seedable runs; same prompt+seed+model → same result;
  drift across versions/model-swaps alarms.
- **Eval score is provenance.** A quality claim without an eval record attached is not a claim (I-6). When
  deployed on-chain, the score travels with the work.
- **Model-agnostic means tested across backends.** A WP that touches inference asserts on at least a local
  (llama.cpp/Ollama) *and* one other backend via the capability contract — never one hardcoded model.

## 6. The honest-status obligation (Rule 1)

Every sprint close reports "what didn't work" with the same weight as "what worked" (RETRO.md). A surface
that is half-built ships **named honestly** ("Coming in SPL-Sx") or does not ship. Fluff is not a
placeholder; it is a defect that lies to the next reader.
