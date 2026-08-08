# Splendor — Alignment Decision Ledger

> Source of truth for the founding decisions of **Splendor**, a hard fork of Blender aimed at
> AI-first creators making retro (PS1-era) 3D animation, games, and on-chain creative work.
> Captured from the founding alignment interview (2026-08-08). Every downstream spec, sprint,
> and acceptance criterion traces back to a decision here. Amend by PR + note the date.

Fork created: **https://github.com/SaulBuilds/splendor** (forked from `blender/blender`, the official
GitHub mirror of the canonical `projects.blender.org` repo). Default branch `main`, full ~1.3 GB history.

---

## 1. Positioning & fork strategy
| # | Decision | Choice |
|---|----------|--------|
| 1.1 | Structural relationship to Blender | **Hard fork, own identity** — own release cadence, UI, branding; cherry-picks upstream fixes but free to diverge deeply. |
| 1.2 | Primary retro north star | **PS1/N64 low-poly 3D** leads (affine texture warp, vertex snap/jitter, low-res render, dithering, fog). Pixel/voxel, 16-bit 2.5D, CRT/VHS all matter but are secondary. |
| 1.3 | Tip-of-the-spear user (v1 obsesses over them) | **AI-first "vibe" creators** — describe intent, harness builds/iterates; low manual modeling skill assumed. Must not alienate pro Blender users. |
| 1.4 | Monetization posture | **RESOLVED (2026-08-08)** → **open GPL app + Zone-B services + Zone-C Citrate protocol + stewardship shell.** GPL is load-bearing: core stays GPL; value captured via hosting/services/protocol, never a proprietary core. Full model in `docs/business/BUSINESS_MODEL_AND_GPL.md`; specifics in §9 below. |

## 2. AI-native architecture & MCP harness
| # | Decision | Choice |
|---|----------|--------|
| 2.1 | Agent-loop topology | **Both: in-app agent panel (loops/goals in-process) + MCP server** exposing Splendor as tools/resources to external agents. |
| 2.2 | Inference backends (v1 non-negotiable) | **llama.cpp/GGUF, Ollama, cloud APIs (Anthropic/OpenAI/Google), diffusion (ComfyUI/SD), AND raw ML frameworks (PyTorch/TensorFlow/etc.)** — backend layer is a general model-execution abstraction, not just LLM servers. |
| 2.3 | Primary AI action surface | **Hybrid DSL over nodes+ops** — typed intents compile to geometry/shader nodes where possible, bpy operators otherwise. Reviewable, undoable, benchmarkable, model-agnostic. |
| 2.4 | Compute/privacy posture | **Local-first now, router-ready architecture** — llama.cpp/local default & offline-capable; a clean routing seam so a hybrid auto-router can be added later without rewrite. |

## 3. Model-agnostic training + eval/benchmark
| # | Decision | Choice |
|---|----------|--------|
| 3.1 | Training modalities (v1) | **All four**: diffusion/image style LoRAs, LLM LoRAs/fine-tunes, weightless workflow/loop capture, and 3D/geometry model training. |
| 3.2 | Training compute | **Local GPU + optional cloud**, AND **must be able to source compute from CitrateNetwork chain / DePIN** — training compute is a pluggable resource provider. |
| 3.3 | Eval/benchmark harness role | **First-class pillar, not a feature** — output-quality-vs-goal, model/backend benchmarking (in-app leaderboard), regression/reproducibility, and routing signal for the future router. Central to the data-flow architecture. **Shipped as its own SDK in the packaging.** |
| 3.4 | Scoring methods | **All**: automated metrics, VLM-as-judge on renders, human ratings, deterministic DSL task criteria — governed by HIC levels. |

## 4. Governance — HIC (Human In Control)
| # | Decision | Choice |
|---|----------|--------|
| 4.1 | Terminology | **HIC = "Human In Control"**, never "HITL". Autonomy is graduated, baked into the term. (User convention across all their architecture.) |
| 4.2 | Autonomy ladder | Reuse the canonical `quorum-audit` scheme: **HIC-0 Observed → HIC-1 ApproveEach → HIC-2 Budgeted → HIC-3 PostHoc → X Ungoverned.** |
| 4.3 | Rules enforcement | **HIC levels + policy engine at the tool-call boundary + declarative rule codes** (quorum-policy-style verdicts, e.g. RC-101/102/103). |

## 5. Deployment — web + blockchain
| # | Decision | Choice |
|---|----------|--------|
| 5.1 | On-chain semantics (all in scope) | **Provenance/attestation** (hash work + eval scores + AI-run trace), **NFT mint / generative collections**, **asset registry + licensing/royalties**, **decentralized storage** — storage **hooks into Citrate's pinning system**. |
| 5.2 | Chain target | **CitrateNetwork first**, via a **composable, open-ended chain interface** extendable to EVM chains + Solana. |
| 5.3 | Web deploy paths (all in scope) | Real-time web export (WebGL/WebGPU), rendered video/gif/sprite-sheet, Splendor-hosted gallery + embeddable player, self-hosted static export. |
| 5.4 | Identity/keys | **Account-abstraction / smart accounts** — vibe creators sign in simply (email/passkey); keys/gas invisible, on CitrateNetwork. |

## 6. Game-dev pipeline & the node/edge language
| # | Decision | Choice |
|---|----------|--------|
| 6.1 | Export targets | **Godot, Unity, Unreal, open formats (glTF/USD/FBX) + retro variants, AND Apple Reality Composer Pro / USDZ (RealityKit) spatial formats.** |
| 6.2 | New node/edge capabilities (all) | Retro-look procedural nodes; game-logic/behavior nodes; **AI agent-workflow nodes expressing LangGraph patterns**; deploy/publish pipeline nodes. **One visual node/edge language shared by the MCP harness and the Blender node editor** — familiar to Blender users *and* AI devs, bootstrappable by newcomers via natural language + starter workflows/tutorials. |
| 6.3 | Retro authenticity constraints | **Full manual, presets optional** — presets accelerate, never cage. |
| 6.4 | Retro animation (v1 must nail, all) | Loop/procedural animation, character rig+anim, classic vertex/keyframe animation, camera/cinematics, **and retro lighting** (vertex/Gouraud/baked). |

## 7. Interop & compatibility
| # | Decision | Choice |
|---|----------|--------|
| 7.1 | Interop spine | **MCP transport + LangGraph-compatible graph format** for portable workflow authoring/serialization. |
| 7.2 | Memory/learning layers (all) | Local file memory (agentile-style), vector/graph store (citrate-memories-style), on-chain/pinned run provenance, captured reusable-workflow library. |
| 7.3 | Day-one compatibility targets | Claude Code/Claude (MCP), local OpenAI-compatible endpoints (llama.cpp/Ollama/LM Studio/vLLM), LangGraph/LangChain, Cursor/Windsurf/Cline, **plus Devin, Hermes, OpenClaw, Prime Intellect.** Principle: lean on open standards (MCP + OpenAI API shape + LangGraph) so any frontier/decentralized-training tool plugs in without bespoke glue. |

## 8. Process, team, MVP, platform, distribution
| # | Decision | Choice |
|---|----------|--------|
| 8.1 | v0 vertical slice | **Prompt → PS1 asset → eval → export/mint**, wired end-to-end. |
| 8.2 | Build philosophy | **Fully spec-driven.** No feature is more important than another; all pillars ship in the same release and are tested. **Everything wired end-to-end on the first full sprint pass — no fluff/mock features.** AI/Eval + governance is proof-critical (rest is proven in existing architecture) and must be made to work. Acceptance criteria must forbid misinterpretation/mocking. |
| 8.3 | Team (until v1) | **Saul + Claude Code (me) + Claude Design + Emma (game-designer SME, final say on design/UX/functionality).** Mirrored repo opens to OSS community **at v1 release.** |
| 8.4 | Methodology | **Full agentile scaffold** (sprints, rules, audits, journals, claim-grading). |
| 8.5 | Design handoff contract | I define wiring + expected tooling → **Claude Design** expresses it into UX that excites (not alienates) Blender users, progressively obfuscating complexity (click-into depth), preserving Blender's proven core, with **chat modals for specific features** and an AI/harness navigation model that never degrades the pro modeler/animator workflow → handed back to me mid-build to wire up. **I hold final say on feature behavior; Emma holds final say on design/UX.** |
| 8.6 | Workspace | **Separate workspace outside Citrate-Labs** → `~/Projects/Splendor`. Fork clone deferred until implementation (avoid premature 1.3 GB pull). |
| 8.7 | Platform matrix (v1) | **Linux + Windows + macOS** (full Blender matrix). |
| 8.8 | Distribution (all) | Standalone app builds + itch.io + Steam + GitHub releases/website. |

## 9. Business model, GPL & compliance
> Resolved 2026-08-08 by accepting the recommendations in `docs/business/BUSINESS_MODEL_AND_GPL.md` §10.
> Regulatory items (⚖️) are directional intent, gated on counsel per 9.6. Amendable.

| # | Decision | Choice |
|---|----------|--------|
| 9.1 | Overall model | **Adopt the recommended hybrid**: free open GPL app (Zone A) + proprietary network services (Zone B) + Citrate protocol economics (Zone C) + foundation-style stewardship shell owning trademark/official builds. |
| 9.2 | GPL boundary rule | **Distribution triggers copyleft; hosting does not.** Everything shipped in the app is GPL and free; paid value lives behind the network (Zone B) or on-chain (Zone C). No closed features in the distributed binary. |
| 9.3 | First paid service at v1 | **Hosted gallery** (+ embeddable player, freemium) — lowest effort, strongest network effect. Provenance/attestation ships **free** to seed the loop. Eval-as-a-Service, managed training, inference follow. |
| 9.4 | Flagship Zone-C revenue | **DePIN compute take-rate** (usage-scaled, not seats) as the flagship protocol revenue, **phased in post-v1**. Mint/marketplace/licensing/royalties layered as the creator economy matures. |
| 9.5 | Trademark & brand (Phase 0) | **Register "Splendor" word mark + logo, secure domains/handles early.** Reserve "official build" status. Trademark is the enforceable moat (GPL covers copyright, not marks). Treated as an early action item. |
| 9.6 | Token posture | **Off the table for now.** Utility-only if ever, and **only** with securities counsel + genuine non-investment utility. No token ships without that gate. ⚖️ |
| 9.7 | Legal gate | **Engage IP + securities/custody counsel before Phase 1 (v1 OSS launch) — a hard gate.** Confirms arm's-length service boundary, AGPL-vs-proprietary for own server code, AA/custody posture, and mint/marketplace/token compliance. ⚖️ |
| 9.8 | Own-server-code licensing | Server components **Splendor authors** (eval/training/gallery backends, not derived from Blender) may be **AGPL or proprietary** to prevent uncompensated service cloning; inherited Blender code stays GPL. Boundary kept clean + documented. ⚖️ |
| 9.9 | Custody design | Prefer **non-custodial** account-abstraction (user holds keys; Splendor may sponsor gas) [D-5.4]; no custodial flow without counsel. ⚖️ |

---

## Open items owed
- [x] **Business-model + GPL memo** — written (`docs/business/BUSINESS_MODEL_AND_GPL.md`) and **resolved** into §9 (Decision 1.4). Recommendations accepted 2026-08-08. Regulatory items gated on counsel (9.6/9.7).
- [ ] **Phase-0 action item:** register "Splendor" trademark + secure domains/handles (Decision 9.5).
- [ ] **Legal gate:** engage IP + securities/custody counsel before Phase 1 (Decision 9.7).
- [ ] **Blender architecture walk** — grounded map of render/nodes/bpy/UI/addon extension points, per-sprint depth. (User asked to "walk the whole current architecture".)
- [ ] **Clone the fork** into `~/Projects/Splendor` (confirm before 1.3 GB pull). (Decision 8.6)
- [ ] **Agentile scaffold** — after the architecture spec + handoff doc land. (Decision 8.4)
