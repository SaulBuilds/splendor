---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# 01 — Pillars → Epics → Sprint sequence (advisory)

> Decomposition of the 7 pillars (`docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md`) into epics and a
> proposed sprint order. **Advisory, not locked** — sprint SCOPEs are the binding artifacts and each is
> written only after its assumptions are measured against reality (`03_ACCEPTANCE_FRAMEWORK.md` §4).
> No pillar is more important than another; AI/Eval + governance simply gets the most rigor (D-8.2).

## Epics by pillar

| Epic | Pillar | Core deliverables |
|------|--------|-------------------|
| **E-P1** | Retro Engine | Retro render pipeline (affine warp, vertex snap, low-res FB, dithering, palette quantize, vertex/Gouraud lighting, fog); retro-target presets (PS1/N64/Saturn) as *optional* accelerators; retro animation (vertex/keyframe + rig + loop/procedural + camera). |
| **E-P2** | AI Harness | In-app agent runtime (loops/goals) + MCP server + MCP client; the single governed action API; chat-modal + harness-panel wiring. |
| **E-P3** | Model Backend | Capability-declaring adapters (llama.cpp, Ollama, OpenAI-compat, Anthropic, Google, ComfyUI/diffusion, PyTorch/TF/ONNX framework); Router seam (local-first, router-ready); compute providers incl. CitrateNetwork/DePIN. |
| **E-P4** | Eval SDK | Scorers (automated metrics, VLM-judge, HIC-gated human, deterministic DSL criteria); benchmark harness + leaderboard; regression/repro; provenance link; meta-eval. Shipped as a standalone importable SDK. |
| **E-P5** | Node/Edge Language | Retro-look nodes, game-logic/behavior nodes, AI agent-workflow nodes (LangGraph patterns), deploy/publish nodes; Blender-nodes ⇄ LangGraph serialization; NL → starter-workflow on-ramp. |
| **E-P6** | HIC Governance | Policy engine at the tool-call boundary; HIC ladder; declarative rule codes; decision records + audit trail; on-chain envelope mirror. |
| **E-P7** | Deploy & Chain | Web export (real-time WebGL/WebGPU, clips/sprite-sheets, hosted gallery + embeddable player, static); composable chain interface (CitrateNetwork-first); provenance/mint/registry/licensing; Citrate pinning; AA identity; engine/format export (Godot/Unity/Unreal/glTF/USD/FBX/USDZ). |

## Cross-cutting epics

| Epic | Scope |
|------|-------|
| **E-X1** | Fork build hygiene + CI across Linux/Windows/macOS (D-8.7); GPL source-publication automation; upstream-diff surface tracking (Rule 7). |
| **E-X2** | Design system + surfaces with Claude Design/Emma (the handoff contract); progressive-disclosure UX; chat modals. |
| **E-X3** | Packaging + distribution (standalone builds, itch.io, Steam, GitHub/website — D-8.8); the Eval SDK as a shippable package. |
| **E-X4** | Business/compliance (Zone-B service seams, Zone-C protocol seams, trademark/Phase-0 items, counsel gates — D-9). |

## Proposed sprint sequence

> Each sprint ships **vertical slices** (real end-to-end), never a horizontal layer. The sequence front-loads
> the spine so every later feature has a real seam to plug into; it does **not** defer any pillar out of v1.

- **SPL-S0 — Spine: fork build + the seven seams.** Fork builds on all platforms; a *thin but real*
  interface exists for each pillar (DSL skeleton, MCP bridge, HIC gate, backend Router, Eval SDK boundary,
  chain/pinning adapter interface, one retro shader). Each seam has a negative control. *(Active — see
  SCOPE.)*
- **SPL-S1 — The v0 vertical slice.** Prompt → PS1 asset → eval → export/mint, wired end-to-end, no mocks
  (D-8.1). Minimal real implementation across P1–P7 + E-P6.
- **SPL-S2 — Retro depth + node language.** E-P1 render/animation depth; E-P5 retro + workflow nodes with
  LangGraph round-trip.
- **SPL-S3 — Harness + backends + eval depth.** E-P2 agent loops/goals; E-P3 full adapter set + DePIN
  provider; E-P4 leaderboard + meta-eval + training-data feed.
- **SPL-S4 — Deploy breadth.** E-P7 real-time web runtime, gallery, engine/USDZ exports, on-chain
  provenance/mint/licensing (counsel-gated surfaces flagged).
- **SPL-S5 — Training + polish + packaging.** E-P3 training (diffusion/LLM/3D/workflow-capture); E-X3
  distribution; v1 OSS-launch readiness.

Ordering is practical, not a priority ranking. All pillars are v1. Adjust at each sprint boundary based on
the measured-reality check and Emma's UX review.
