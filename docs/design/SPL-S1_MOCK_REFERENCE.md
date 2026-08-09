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

## Not yet (honest, per the mock's own labels)
- **Visual pass** needs a GUI session (panels can't render headlessly). Launch Splendor → N-panel
  "Splendor" + header autonomy bar + green accent.
- **Plan** step (Router, local-first, honest-offline) and the **Retro HUD** viewport overlay are DONE (this increment).
- Node/Edge editor + Model Manager (SPL-S2), Training Panel (SPL-S3) — named honestly, later slices.
- The Citrate **paper skin** for Deploy is approximated in bpy; the pixel-faithful paper surface is the
  future web deploy/gallery (its own substrate).
