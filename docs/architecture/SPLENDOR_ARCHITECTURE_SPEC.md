# Splendor — Master Architecture Spec (v0.1, draft)

> Grounds the vision in how Blender is actually built, then defines the seven Splendor pillars, the
> data flow that binds them, and the v0 vertical slice. This is the alignment artifact that precedes
> agentile decomposition. Decisions referenced as `[D-x.y]` map to `docs/DECISIONS.md`.
>
> Status: **draft for review by Saul + Emma.** Not yet decomposed into sprints.

---

## 0. One-paragraph thesis
Splendor is a hard fork of Blender [D-1.1] for **AI-first creators** [D-1.3] making **PS1-era retro** [D-1.2]
3D animation, game assets, and on-chain creative work. It keeps everything Blender does, and adds an
**AI harness** that plans/acts through a **typed intent DSL**, a **model-agnostic backend**, a **first-class
eval/benchmark SDK**, **HIC governance**, a **node/edge language that unifies Blender nodes with LangGraph
agent workflows**, and a **deploy layer** that ships work to the web and to CitrateNetwork (provenance,
mint, licensing, pinned storage). Local-first, spec-driven, fully wired end-to-end on the first pass [D-8.2].

---

## 1. How Blender is built (the extension surface we inherit)
Splendor must extend Blender without breaking the core that made it successful. The relevant layers:

- **`blender` (C/C++ core)** — the executable. Key subsystems:
  - **DNA/RNA** — DNA is Blender's serialized struct layer (the `.blend` file schema); RNA is the
    runtime reflection/property system that exposes DNA to Python, the UI, and animation. *Any new
    persistent Splendor data (retro targets, DSL graphs, eval records, HIC policy) lives as DNA structs
    surfaced through RNA, or as ID-block custom properties.*
  - **`bpy`** — the Python API (thin CPython binding over RNA + operators). Add-ons, the AI action
    surface, and most Splendor tooling call through here.
  - **Operators (`wm.operator`)** — the atomic, undoable, reportable action unit. The DSL compiles to
    operators; this is also where the **HIC policy check** intercepts [D-4.3].
  - **Node systems** — Geometry Nodes, Shader Nodes, Compositor. Custom node trees + node types are the
    home of the **retro-look nodes** and, extended, the **agent-workflow nodes** [D-6.2].
  - **Draw Manager / GPU module / GHOST** — the viewport draw backend (OpenGL/Vulkan/Metal via GHOST
    windowing) and real-time engine (EEVEE-Next). Retro render passes (affine warp, vertex snap,
    dithering, low-res) attach here and in **Cycles/EEVEE render engine hooks**.
  - **Render engines** — Cycles (path tracer) and EEVEE (real-time). Splendor adds a **retro render
    pipeline** (custom passes + a `RenderEngine` subclass or EEVEE post stack).
  - **`asset system` / `USD` / `glTF` IO** — Blender already ships USD + glTF importers/exporters and an
    asset browser/library. The **export pillar** builds on these (adds Godot/Unity/Unreal + retro
    variants + Apple USDZ/RealityKit) [D-6.1].
  - **Extensions platform (4.2+)** — Blender's modern add-on/extension packaging + repository system.
    Splendor bundles its Python layer as first-class extensions where a C fork isn't required.
- **Build system** — CMake + a large vendored dependency set (`lib/`), Python 3.11+ embedded. Full
  matrix Linux/Windows/macOS [D-8.7].

**Fork strategy consequence:** we prefer the *thinnest possible C/C++ diffs* (render passes, DNA structs,
an embedded MCP/agent bridge that add-ons can't cleanly host, GPU retro shaders) and push everything else
into the Python/extension layer, so we can cherry-pick upstream fixes with minimal conflict. Every C-level
change is a maintenance tax we pay forever — it must justify itself against "could this be an extension?".

---

## 2. The seven pillars
```
                         ┌─────────────────────────────────────────────┐
                         │            SPLENDOR (fork of Blender)         │
                         └─────────────────────────────────────────────┘
  P1 Retro Engine    P2 AI Harness    P3 Model Backend   P4 Eval SDK
  P5 Node/Edge Lang  P6 Governance(HIC)                  P7 Deploy/Chain
```

### P1 — Retro Engine (`splendor.retro`)
The creative core: makes Splendor *look* PS1 [D-1.2].
- **Retro render pipeline**: affine (non-perspective-correct) texture mapping, per-vertex snapping/jitter
  to a low-res grid, integer/low-res framebuffer + nearest upscale, ordered dithering, palette
  quantization, vertex/Gouraud lighting mode, distance fog, draw-distance culling.
- **Retro targets** as *optional presets* [D-6.3]: `PS1`, `N64`, `Saturn`, `PSX-hi`, etc. — each a bundle
  of tri budgets, texture-res caps, palette size, warp/snap parameters. **Presets accelerate; never cage.**
  Live authentic preview in the viewport; soft budget HUD (warn, don't block).
- **Retro animation** [D-6.4]: vertex/keyframe (baked, no skeletal blend) path *and* modern rig path;
  loop/procedural tooling (seamless idle/turntable loops for social + NFT); camera/cinematics sequencing.
- Implemented as: GPU shaders + a render pass stack (C/GPU diff) + Geometry/Shader **retro nodes** (P5) +
  Python operators for the target/preset system.

### P2 — AI Harness (`splendor.ai`)
The heart [D-1.3]. **Both** an in-app agent panel *and* an MCP server [D-2.1].
- **In-app agent runtime**: runs loops/goals in-process; plans via the DSL (P5); every act goes through
  the governance boundary (P6). Surfaced through **chat modals + a harness panel** (see handoff doc).
- **MCP server**: exposes Splendor as MCP tools + resources so external agents (Claude Code, Cursor,
  Windsurf, Cline, Devin, Hermes, OpenClaw, Prime Intellect) [D-7.3] can drive it. Tools are the same
  governed DSL/operator surface the in-app agent uses — one action API, two front doors.
- **MCP client**: Splendor also *consumes* external MCP servers (e.g. citrate-memories, pinning, chain)
  so workflows can reach the wider ecosystem.
- **Router-ready seam** [D-2.4]: all model calls go through a `Router` interface that today resolves to
  "local-first"; tomorrow the same interface routes by cost/quality/latency using eval signal (P4).

### P3 — Model-Agnostic Backend (`splendor.models`)
A **general model-execution abstraction**, not just LLM servers [D-2.2].
- **Backend adapters**: `llama.cpp/GGUF`, `Ollama`, `OpenAI-compatible` (covers LM Studio/vLLM/etc.),
  `Anthropic`, `Google`, `ComfyUI/diffusion`, and a `Framework` adapter for raw **PyTorch/TensorFlow/ONNX**
  models (for custom 3D/geometry or scoring models).
- **Capability contract**: each adapter declares modalities (text, vision, image-gen, embedding, custom),
  context limits, streaming, tool-calling shape. The Router selects by *declared capability + eval score*,
  never by hardcoded model name.
- **Compute providers**: local process, local GPU, cloud endpoint — and a **CitrateNetwork/DePIN provider**
  [D-3.2] so inference *and* training compute can be sourced from the chain's compute market.

### P4 — Eval & Benchmark SDK (`splendor.eval`) — *proof-critical* [D-3.3]
A standalone SDK, shipped in packaging, that everything else is judged by.
- **Scorers** [D-3.4]: automated metrics (tri-count/topology, silhouette/image similarity to reference,
  palette adherence, CLIP-style), **VLM-as-judge** on rendered frames against rubrics, **HIC-gated human
  ratings**, and **deterministic DSL task criteria** (`≤800 tris`, `affine=on`, `palette=16`).
- **Benchmark harness**: runs a task across multiple model+backend combos → an **in-app leaderboard**
  (quality/latency/cost) so users and the Router choose informed.
- **Regression/repro**: seedable runs; golden sets; drift alarms across Splendor versions + model swaps.
- **Provenance link**: eval records are hashable and pinnable (P7) — "this asset scored X with model Y"
  becomes an attestable fact.
- **Training modalities feed** [D-3.1]: eval signal + captured runs supply datasets for diffusion LoRAs,
  LLM LoRAs, weightless workflow capture, and 3D-model training.

### P5 — Node/Edge Language (`splendor.graph`)
**One visual node/edge language shared by the Blender node editor and the MCP harness** [D-6.2].
- **Retro-look nodes** (P1 surfaced as nodes), **game-logic/behavior nodes** (state machines/triggers/
  transitions — "edges" = transitions/data flow, exportable to engine logic or a portable runtime),
  **AI agent-workflow nodes** (prompt→model→eval→apply, expressing **LangGraph patterns**), **deploy/
  publish nodes** (export→optimize→mint/pin→publish).
- **Dual representation**: a workflow authored as Blender nodes ⇄ serializes to a **LangGraph-compatible
  graph** [D-7.1], so the same workflow is editable visually *and* runnable/shareable by AI-dev tooling.
- **Newcomer on-ramp**: natural-language → starter workflow; tutorial graphs; templates. Complexity is
  opt-in (click-into depth).

### P6 — Governance: HIC (`splendor.hic`)
Reuses the Citrate model exactly [D-4.1/4.2/4.3].
- **Autonomy ladder**: HIC-0 Observed → HIC-1 ApproveEach → HIC-2 Budgeted → HIC-3 PostHoc → X Ungoverned.
- **Policy engine at the tool-call boundary**: every DSL/operator/MCP action passes a
  `PolicyBinding.check` → `Verdict` (`proceed` / `require-approval` / `deny`) with declarative rule codes.
  Chain/money/key/mint actions default to HIC-1. Budgeted autonomy for bulk creative ops.
- **Audit trail**: every governed action recorded as an HIC evidence unit — feeds eval, provenance, and
  the captured-workflow memory.

### P7 — Deploy & Chain (`splendor.deploy`)
Ships work to the internet and CitrateNetwork [D-5.x].
- **Web export** [D-5.3]: real-time WebGL/WebGPU runtime (retro scenes actually run in-browser),
  rendered clips/sprite-sheets, Splendor-hosted gallery + embeddable player, self-hosted static bundles.
- **Chain interface** [D-5.2]: composable adapter, **CitrateNetwork-first**, EVM + Solana pluggable later.
- **On-chain semantics** [D-5.1]: provenance/attestation (work hash + eval scores + AI-run trace),
  NFT mint + generative collections, asset registry + licensing/royalties, decentralized storage via
  **Citrate pinning**.
- **Identity** [D-5.4]: account-abstraction/smart accounts — vibe creators sign in with email/passkey;
  keys/gas invisible.
- **Engine/format export** [D-6.1]: Godot/Unity/Unreal + glTF/USD/FBX + retro variants + Apple USDZ/RealityKit.

---

## 3. The data flow (how the pillars bind)
```
 user intent (NL or node graph)
        │
        ▼
 [P5] DSL / workflow graph  ──serialize──▶  LangGraph-compatible artifact (portable)
        │
        ▼
 [P2] Harness plans a run ──▶ [P3] Router picks backend/model ──▶ model call
        │                                   ▲
        ▼                                   │ (future auto-route by score)
 [P6] HIC policy check at each tool call ───┘
        │  proceed / require-approval / deny
        ▼
 [P1] Retro engine applies (nodes + ops)  →  viewport / render
        │
        ▼
 [P4] Eval scores the output (metrics + VLM + criteria + HIC-gated human)
        │
        ├─▶ leaderboard / regression store
        ├─▶ captured-workflow library + training datasets
        ▼
 [P7] Deploy: web export + chain (provenance incl. eval scores, mint, license, pin)
```
Memory layers [D-7.2] wrap the whole loop: local file memory (agentile), vector/graph store,
on-chain/pinned run provenance, captured reusable-workflow library.

---

## 4. The v0 vertical slice [D-8.1]
**"Prompt → PS1 asset → eval → export/mint," wired end-to-end, no mocks.** Minimal real implementation of
every pillar:
1. **P2/P5**: user types "a low-poly PS1-style health potion, ≤500 tris, 16-color palette" → harness emits
   a DSL intent (also viewable as a workflow node graph).
2. **P3**: Router resolves to a local model (llama.cpp/Ollama) to plan; diffusion backend optional for texture.
3. **P6**: HIC-2 budget for geometry ops; HIC-1 approval gate before the mint step.
4. **P1**: DSL compiles to geometry/shader nodes + operators → a real PS1-look mesh + affine/dithered render.
5. **P4**: eval scores it — tri budget met? palette adherence? VLM "reads as PS1?" — recorded + shown.
6. **P7**: export glTF + retro variant; then a real provenance attestation + mint to CitrateNetwork testnet
   with the eval score embedded, asset pinned via Citrate pinning, signed via a smart account.

Acceptance criteria for the slice must be **objective and mock-forbidding** [D-8.2]: e.g. "the minted token's
metadata URI resolves to a pinned glTF whose hash matches the exported file, and includes the recorded eval
score object" — not "a mint button exists."

---

## 5. Cross-cutting tech decisions (proposed, for review)
- **Language split**: C/C++ only for render passes, GPU retro shaders, DNA structs, and the embedded
  MCP/agent bridge if it can't live in Python. Everything else Python/extensions. *(Minimize fork tax.)*
- **DSL**: typed, versioned, serializable; compiles to nodes-first then ops. Round-trips to LangGraph.
- **MCP**: transport = the interop spine [D-7.1]; the same governed action API backs in-app + external.
- **Model API lingua franca**: OpenAI-compatible shape for local endpoints; adapters normalize the rest.
- **Eval SDK**: independently importable (usable outside Splendor); this is a packaging + product asset.
- **Chain/pinning/identity**: thin adapters over Citrate primitives; nothing chain-specific leaks into P1–P5.

---

## 6. Risks & open questions
- **GPL boundary** [D-1.4]: services/hosting/eval-SDK monetization is GPL-safe; a proprietary core is not.
  Business memo owed before deploy/services detailing (`docs/business/`).
- **Fork maintenance tax**: every C diff must be justified vs. an extension. Track diff surface as a metric.
- **UX tension**: AI/chat surfaces must not degrade the pro modeler/animator workflow — the central design
  constraint handed to Claude Design + Emma (see handoff doc).
- **Eval validity**: VLM-as-judge and metrics need their own validation (meta-eval) or they mislead routing.
- **Real-time web retro runtime**: highest-risk deploy path (needs a runtime, not just a render export).
- **Blender code walk**: this spec is grounded in Blender's known architecture; each sprint still needs a
  targeted code walk of the exact subsystem it touches (owed item in DECISIONS).
```
