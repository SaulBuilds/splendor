# Splendor — Claude Design Handoff & Wiring Contract (v0.1, draft)

> The interface between **feature wiring (owned by Claude Code)** and **UX/design expression (owned by
> Claude Design, with Emma holding final design/UX say)** [D-8.3/8.5]. This document tells Claude Design
> *what each surface must be wired to and what it must do*; Claude Design decides *how it looks and feels*.
> I (Claude Code) hold final say on **feature behavior**; Emma holds final say on **design/UX**. Prototype
> comes back to me mid-build to wire up.

Referenced decisions map to `docs/DECISIONS.md` as `[D-x.y]`.

---

## 1. The prime directive (non-negotiable design constraint)
**Excite Blender users; never alienate them.** Splendor must do everything Blender does, the way Blender
does it, *plus* AI. That means:
- **Preserve Blender's proven core UX** — the editors, the modal operators, the shortcuts, the node
  editors, the timeline. A returning Blender user must feel at home in the first 5 seconds.
- **Progressive obfuscation of complexity** [D-1.3/6.2] — AI power is available but *click-into*, never in
  the face of a pro. Depth is opt-in; the default screen is calm.
- **The AI must never degrade the pro modeler/animator workflow** [D-8.5] — no modal steals focus mid-edit,
  no chat panel eats the viewport, no AI action fires without the governance surface making it legible.
- Newcomers get a natural-language on-ramp and starter workflows/tutorials; pros can ignore all of it.

---

## 2. Surfaces to design (each lists what it is wired to)
Claude Design owns the look/interaction; the **"wired to"** column is fixed by the architecture.

| Surface | Purpose | Wired to (fixed) |
|---|---|---|
| **Harness Panel** | Home of the in-app agent: goals, active loops, workflow runs, run history. | `splendor.ai` runtime; `splendor.graph` workflows; HIC status per run. |
| **Chat Modals** [D-8.5] | Feature-scoped conversational entry points (e.g. "describe this asset", "fix this topology", "make it more N64"). Pop up *for specific features*, not a global chatbot. | DSL intent emitter (`splendor.graph`); Router (`splendor.models`); HIC gate. |
| **Retro Target HUD** | Live budget readout (tris/palette/texres) + preset picker. Soft warnings only [D-6.3]. | `splendor.retro` targets/presets; eval deterministic criteria (P4). |
| **HIC Control Bar** | Shows/sets the current autonomy level; surfaces `require-approval` prompts inline. | `splendor.hic` ladder (0/1/2/3/X) + policy verdicts. |
| **Eval/Leaderboard View** | Per-run scores; model/backend benchmark leaderboard; regression/drift. | `splendor.eval` SDK outputs. |
| **Model/Backend Manager** | Pick/pull/configure backends; see capabilities; set local-first vs cloud policy. | `splendor.models` adapters + capability contract. |
| **Node/Edge Editor extensions** | Retro nodes, behavior nodes, agent-workflow nodes, deploy nodes — inside Blender's node editor. | `splendor.graph` (⇄ LangGraph serialization). |
| **Deploy Panel** | Export to engines/formats; publish to web; mint/attest/pin/license on-chain. | `splendor.deploy`; smart-account sign-in [D-5.4]. |
| **Training Panel** | Kick off diffusion/LLM/3D LoRA training + workflow capture; pick compute (local/cloud/DePIN). | `splendor.models` compute providers [D-3.2]; `splendor.eval` datasets. |

---

## 3. UX principles for the AI/chat surfaces
1. **Legible autonomy.** The user always knows the current HIC level and can see, at a glance, what the
   agent is about to do, is doing, and did. `require-approval` is an inline, non-blocking-where-possible
   prompt — never a surprise.
2. **Reviewable actions.** Because the AI acts through the DSL/operators, every AI action is undoable and
   shows up in history like any human edit. Design should make the "AI did this" provenance visible but
   quiet.
3. **Two front doors, one behavior.** In-app chat modals and external MCP agents drive the *same* action
   API. Nothing the AI can do in chat is unavailable to a pro doing it by hand.
4. **Newcomer→pro gradient.** Starter workflows and NL prompts on the surface; full node graphs and DSL
   underneath. The same feature is reachable at three depths (button → chat → node graph).
5. **Retro-first delight.** The creative payoff (the PS1 look) should feel immediate and authentic in the
   viewport, not hidden behind AI ceremony.

---

## 4. Division of ownership
- **Claude Code (me) owns:** feature behavior, the DSL/action API, pillar wiring, acceptance criteria,
  what each surface is connected to, and final say on how a feature *works*.
- **Claude Design owns:** visual design, interaction design, layout, motion, the expression of each surface
  above — how it *looks and feels*.
- **Emma owns:** final say on design/UX and on whether functionality serves real game-designer/maker
  workflows.
- **Loop:** I hand this contract + the architecture spec → Claude Design produces a robust prototype →
  Emma + I review → prototype returns to me mid-build to wire to the real pillars → iterate.

---

## 5. What Claude Design should produce first (proposed)
1. A **prototype** of the v0 vertical-slice UX [D-8.1]: the chat modal that turns "a PS1 health potion" into
   a governed run, the HIC control bar during that run, the retro HUD, the eval readout, and the deploy/mint
   step — as a clickable flow.
2. A **component inventory** mapping each surface in §2 to reusable UI components that respect Blender's
   visual language (theme tokens, editor conventions) while feeling distinctly Splendor.
3. A **complexity-disclosure map**: for 3–4 core features, the button → chat → node-graph depth ladder.

Design must be self-contained enough to review, but wired to nothing yet — I connect it to the pillars on
return. Anything that would look real but do nothing in the final product is out of bounds [D-8.2].
