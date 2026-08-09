---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
audience: Claude Design (+ Emma, final say on design/UX)
---

# Splendor — Design Kickoff Brief: SPL-S1 Vertical Slice

> **This is your kickoff, Claude Design.** It operationalizes the wiring contract in
> `CLAUDE_DESIGN_HANDOFF.md` into one concrete first deliverable: the UX for Splendor's v0 vertical slice.
> Design the *experience*; the wiring behind each surface is fixed (stated inline). Emma holds final say on
> design/UX; Claude Code (me) holds final say on how features behave and wires it to the real pillars on
> return.

## Read first (in this order)
1. `CLAUDE_DESIGN_HANDOFF.md` — the contract: surfaces, what each is wired to, ownership split, UX principles.
2. `../DECISIONS.md` — the 31 founding decisions (esp. D-1.2 PS1 look, D-1.3 AI-first-but-don't-alienate-pros).
3. `../architecture/SPLENDOR_ARCHITECTURE_SPEC.md` §4 — the v0 vertical slice you're designing.
4. `../../.agentile/planset/02_HIC_MODEL.md` — the HIC ladder; the autonomy surface is a design requirement.

## The one flow to design (SPL-S1)
**"Prompt → PS1 asset → eval → export/mint," end to end, inside Splendor.** Design the full happy path AND
its honest failure/approval states — never a fake-success screen (Rule 1). The steps, each mapped to a
surface from the handoff §2:

| Step | What the user experiences | Surface(s) | Wired to (fixed) |
|------|---------------------------|-----------|------------------|
| 1. Describe | User types "a low-poly PS1-style health potion, ≤500 tris, 16-color palette." | **Chat Modal** (feature-scoped, not a global bot) | DSL intent emitter → Router |
| 2. Plan (governed) | User sees what the agent will do before it does it; autonomy level visible. | **HIC Control Bar** | HIC gate; verdict proceed/require-approval/deny |
| 3. Build | A real PS1-look mesh appears in the viewport; retro budget HUD updates live (soft warnings only, D-6.3). | **Viewport + Retro Target HUD** | retro nodes/ops; deterministic criteria |
| 4. Score | The result is evaluated — tri budget, palette adherence, "reads as PS1?" — shown honestly. | **Eval / Leaderboard View** | Eval SDK output |
| 5. Approve mint | Before anything on-chain, an explicit HIC-1 approval (chain/mint defaults to ApproveEach). | **HIC Control Bar (approval)** | policy engine; AA sign-in |
| 6. Ship | Export glTF + retro variant; provenance-attest + mint to testnet with the eval score embedded; asset pinned. | **Deploy Panel** | chain adapter; Citrate pinning; smart account |

## The prime directive (non-negotiable — from handoff §1)
- **A returning Blender user must feel at home in 5 seconds.** Preserve Blender's editors, shortcuts, node
  editors, timeline, and visual language. Splendor's identity is additive, not a reskin that fights muscle memory.
- **Complexity is click-into, never in-your-face.** The same feature is reachable at three depths:
  a button → the chat modal → the underlying node graph. A pro can ignore all AI surfaces entirely.
- **No AI surface may steal focus or eat the viewport mid-edit.** Chat modals are summoned, dismissible, and
  scoped; they do not hijack the pro workflow.
- **Legible autonomy.** The user always knows what the agent is about to do, is doing, and did. `require-approval`
  is inline and non-blocking where possible; `ungoverned` is visible, never silent.

## States you must design (not just the happy path)
- **Honest error** (e.g. offline + a cloud-only route selected → "backend unavailable," not a hang or fake result).
- **require-approval** and **ungoverned** HIC states.
- **Eval below threshold** (the potion is 900 tris / 20 colors) — shown truthfully, with the click-into fix path.
- **Unbuilt-but-named** surfaces — anything not in SPL-S1 is labeled honestly ("Coming in SPL-Sx"), never faked.

## Deliverables (from handoff §5)
1. **A clickable prototype** of the six-step flow above, including the non-happy states.
2. **A component inventory** mapping each handoff §2 surface to reusable components that respect Blender's
   theme tokens/editor conventions while feeling distinctly Splendor.
3. **A complexity-disclosure map** for 3–4 core features (button → chat → node-graph depth ladder).

## Constraints
- **Theme-aware** (Blender ships light/dark; respect both). Match Blender's density and editor chrome.
- **No fabricated data as if live.** Static mockups are fine, but they must represent *real* states (including
  errors/approvals), and nothing may imply a capability that won't exist in the wired product (D-8.2).
- **Accessibility**: keyboard-first (Blender users live on shortcuts), sufficient contrast, no color-only signals.
- **PS1 delight is the payoff** — the retro look should feel immediate and authentic in the viewport, not
  buried behind AI ceremony.

## Review loop & acceptance
- Claude Design produces the prototype → **Emma** reviews (final say on design/UX + real game-maker fit) →
  **Claude Code** reviews for behavioral wiring feasibility → returns to Claude Code to wire to the real
  pillars mid-build. Design is "done for UX" only after Emma's sign-off; behavior stays my call.
- A surface is accepted only if every element maps to something real in the wiring table (no orphan UI).

## Open questions for Emma (please answer inline or in a decision record)
1. Default screen on launch: Blender-familiar default, or a Splendor "start" with the chat modal one click away?
2. Where does the Harness Panel live — a dockable editor (like the Outliner) or a summonable overlay?
3. For vibe creators, how much of the node graph do we reveal by default vs. keep one click down?
4. Retro HUD: always-on budget readout, or summoned? (D-6.3 says soft/optional — your call on default.)
