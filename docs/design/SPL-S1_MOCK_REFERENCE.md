---
created: 2026-08-08
branch: feat/spl-s1-ui-wiring
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# SPL-S1 — Design reference & surface→bpy wiring

Source: Claude Design project `96eaa583-e9a8-4252-9201-048d4fb894cd` (`Splendor SPL-S1.dc.html`),
built on the **Citrate design system**. This doc records the design decisions and how each mock
surface maps to the in-Blender implementation (`scripts/addons_core/splendor_harness/`). The mock
itself lives in the Claude Design project (not vendored here — it embeds Citrate brand assets).

## Locked design decisions (from the mock)
- **Chrome = stock Blender dark/light.** **Citrate green `#8ecc09` replaces Blender's blue** as the
  active/select accent (`theme.apply_accent`). Chain-native from the first pixel.
- **Citrate paper aesthetic only at the chain boundary** (Deploy · attest · mint). The **GPL line is
  visible**: export + provenance = FREE · IN-APP; mint + pin = PROTOCOL FEE.
- **6-step flow:** Describe → Plan → Build → Score → Approve → Ship.
- **Legible autonomy:** HIC Control Bar in the header (level pill; inline `require-approval`; visible
  `ungoverned`).
- **Complexity disclosure:** every feature reachable at button → chat → node-graph depth; one action API.
- **PS1 payoff:** dithered, low-res-poly, affine warp, faceted flat shading (retro engine, P1).

## Surface → bpy → seam wiring
| Mock surface | bpy implementation | Wired to |
|---|---|---|
| HIC Control Bar (header) | `panels.draw_hic_header` on `VIEW3D_HT_header` + `Scene.splendor_hic_level` | `splendor.hic` ladder |
| Harness Panel (6-step flow) | `SPLENDOR_PT_harness` (N-panel, "Splendor") | run state + all ops |
| Chat / Describe modal | `SPLENDOR_OT_describe` (`invoke_props_dialog`) | `splendor.action_api` + `splendor.dsl` |
| Eval scorecard | `SPLENDOR_PT_eval` + `SPLENDOR_OT_score` | `splendor_eval` (TriBudget, PaletteAdherence) |
| Deploy Panel (Citrate boundary) | `SPLENDOR_PT_deploy` + `SPLENDOR_OT_ship` | `splendor.deploy` (provenance, pinning, chain, mint gate) |
| Accent (green replaces blue) | `SPLENDOR_OT_apply_accent` | `theme.apply_accent` |

## Verified (headless, real binary) — `tests/splendor/test_spl_s1_ui.py`
22 checks PASS: registration; Describe→governed build; **HIC-1 blocks the build (gate before act)**;
Score→real eval digest; Ship→content-addressed CID + honest 'unconfigured' pin + **mint HIC-1 gated**;
green accent applied; clean unregister.

## Visual verification — DONE (2026-08-09)

Rendered on the real binary via Xvfb + the **Vulkan** backend on the GB10 (the NVIDIA GL path can't
attach to a virtual X display; Vulkan can). Two screenshots in this folder:

- `spl-s1-gui.png` — the viewport with the **HIC Control Bar** in the header (`HIC-2 · Budgeted`), the
  **Retro HUD** overlay (`12/500 tris · pal 16 · score 1.00 · SCORED`, green meter), the **Citrate-green
  selection accent** on the built "Potion", and the **Splendor** sidebar tab.
- `spl-s1-panel.png` — the full **Splendor Harness** N-panel: the **6-step flow** (1–6), the
  Describe/Plan/Build/Score/Ship operators, the **inline HIC-1 approval box in red** ("build needs your
  approval" + Approve button, shown because the build was gated), the **Retro HUD** toggle, and the
  sub-panels **Eval / Leaderboard · Deploy · Splendor × Citrate · Model / Backend Manager · Training**.

Everything renders as designed. The read-only `Region.active_panel_category` means the Splendor tab can't be
forced by script; `spl-s1-panel.png` captured it because it was the active tab.

## Still open (honest, per the mock's own labels)
- The Citrate **paper skin** for Deploy is approximated in bpy; the pixel-faithful paper surface is the
  future web deploy/gallery (its own substrate).
- Node-editor conditional routing shipped; a depth-4 MCP column in the disclosure map is a follow-up.
