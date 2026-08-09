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

**Status: `active` (2026-08-08)** — fork cloned; planning scaffold reconciled onto branch
`chore/splendor-planning-scaffold`. **The Linux/aarch64 build is VERIFIED**: Splendor builds from source
(base **Blender 5.3.0 Alpha**), produces a 236 MB `blender` binary, launches headless, and passes a real
EEVEE render smoke test. Windows/macOS + CI remain. Measured-reality rows below carry the actual findings.

## Measured against reality before writing this

| What the plan assumes | What is actually true (checked 2026-08-08) |
|---|---|
| The fork is cloneable + buildable locally | Cloned OK. **This box is aarch64 + NVIDIA GB10 (Grace-Blackwell, compute 12.1)**, 20 cores, 121 GB RAM. Blender publishes **no `linux_arm64` precompiled libraries** (`.gitmodules`: x64/macos_arm64/win only). **Owner call: build via `make deps`** — DONE (exit 0, `lib/linux_arm64` = 1.5 GB, 58 libs). **Splendor then built + launched (base Blender 5.3.0 Alpha), EEVEE render smoke test passed.** Required 7 fixes: LFS fallback; GMP staged from GNU; **GCC 14** (13.3 < min 14.0); **libx11-xcb-dev** (weston); **wayland `--libdir lib64`** (Ubuntu multiarch); **link libdrm to ffmpeg**; **OSL OptiX off** (sm_50 gone in CUDA 13). Build-file fixes committed `df9d46b`. |
| GPU compute (Cycles CUDA) on this Blackwell box | **CUDA VERIFIED (2026-08-09).** The GB10 CUDA device is detected and Cycles **path-traces on the GPU** (`sm_121`; proof `docs/design/gpu-render-gb10.png`). The WP-0 binary compiles the sm_121 kernel at runtime (slow first render); the arch list is now CUDA-13/Blackwell-aware (`CMakeLists.txt`) so a precompiled `WITH_CYCLES_CUDA_BINARIES` build targets sm_121 — **verified**: it installs `kernel_sm_121.cubin.zst` and renders in **0.88 s** with an empty cache. **OptiX (hardware RT) still deferred** — needs the NVIDIA OptiX SDK (headers), not the arch. See `docs/BLACKWELL_GPU.md`. |
| The GitHub fork carries what's needed to build | **False.** Forking the mirror does **not** inherit Blender's Git-LFS objects (6,755 paths → `404` on clone). The build *requires* them (`cmake` fails: "incomplete startup blend"). **Resolved:** `make update` adds a `projects.blender.org` LFS fallback; `git lfs pull lfs-fallback` materialized them (`startup.blend` real, 822 MB LFS cache). |
| GPU/OIDN toolchain matches reference | **Divergence flagged:** box has **CUDA 13.0**; Blender reference version-locks **12.8** for OpenImageDenoise. If OIDN's `nvcc` step fails under 13.0, disable that one dep and continue (make deps is resumable). |
| We can add a Python extension without a C diff | Blender extensions platform (4.2+) present in the fork; **to confirm** against this revision when the build lands. |
| An embedded MCP/agent bridge may need a C-level hook | Unknown until a long-lived in-process server is placed without fighting Blender's event loop. **To investigate in WP S0.3/S0.4.** |
| Local models reachable offline | OpenAI-compatible shape assumed as the local lingua franca. llama.cpp/Ollama presence **to verify** at S0.5. |
| CitrateNetwork testnet + pinning reachable | **S0.8 resolved the interface, not liveness:** the deploy layer's content-addressing + hash-verification + composable chain interface are verified via a local fixture; **live Citrate pinning/RPC endpoints remain UNCONFIGURED → UNVERIFIED**, and the adapters fail honestly (`PinUnavailable`/`ChainUnavailable`) rather than faking success. No Citrate infra hardcoded in the OSS repo. |

> Per the framework (§4), each row is resolved to a fact and the table updated **before** the dependent WP is
> built. A seam may not claim liveness against a dependency whose reachability is unverified.

## Work packages — each a real seam with a negative control

Each WP is a vertical sliver, not a layer. "Done" = objective criterion met **and** its negative control
fails on a broken build (`03_ACCEPTANCE_FRAMEWORK.md` §3). None of these is a full feature.

| # | WP | Deliverable (thin but real) | Negative control | Status |
|---|---|---|---|---|
| **S0.0** | Clone + reconcile | Fork cloned; `docs/` + `.agentile/` folded onto a branch; owner merges. Reconciliation per AGENT_ENTRY. | — (enabling) | ☑ cloned + branch `chore/splendor-planning-scaffold` (LFS via fallback); **owner merge pending** |
| **S0.1** | Build on 3 platforms + CI | Splendor builds on Linux/Windows/macOS; a CI job produces artifacts; GPL source-publish step present. | A build with the retro shader syntactically broken **fails CI**, not silently skips. | ◐ **Linux/aarch64 VERIFIED** (builds + launches + EEVEE render smoke test passes; base Blender 5.3.0 Alpha; fixes in `df9d46b`). **Local CI**: `scripts/ci/run_tests.sh` + a pre-push git hook run all 8 `tests/splendor/` suites headlessly (ALL GREEN, ~4s) — no GitHub Actions (billing/binary). **Runbook + Win/macOS handoff** at `docs/build/BUILD.md` (Linux verified; Win/macOS documented, not yet run). **Actual Win/macOS builds + hosted CI + the negative-control shader test still to do.** |
| **S0.2** | One retro shader (P1 seam) | A single real retro effect (palette quantize *or* affine warp) as a GPU pass toggled in the viewport. | Palette set to 17 on a "≤16" target is detectable by the deterministic scorer (feeds S0.6). | ☑ `spl-s0.2` — real **GPU palette-quantization pass** (Vulkan `create_from_info` shader + palette texture), **verified headlessly on the GB10** via offscreen. **8 checks PASS**: hue ramp → exactly N colors, GPU==CPU ground truth (0 mismatches), deterministic, **palette 17 vs ≤16 caught by Eval SDK** (feeds S0.6); un-quantized ramp = 256 colors (load-bearing). Live-viewport overlay toggle = follow-up; headless Vulkan teardown segfaults on exit (Blender quirk) → test hard-exits with the real code. |
| **S0.3** | Governed action API + HIC gate (P2/P6 seam) | One typed DSL intent (`set_palette`/`snap_vertices`) routed through the single action API; every call passes the HIC gate and emits a decision record. | Removing the grant flips the action to `require-approval`; a second, un-gated code path is caught by a source-scan test (I-1). | ☑ `0c28acd` — `splendor` module (hic/dsl/intents/action_api) + `splendor_harness` addon; **22 checks PASS on the real binary** (no-grant→require-approval with geometry unchanged, invalid→deny, wrong-class→RC-SPL-002, sensitive→HIC-1, I-1 source-scan, reproducibility, operator front door). Meta-negative-control: bypassed gate mutates state → gate is load-bearing. |
| **S0.4** | MCP server + client (P2 seam) | Splendor exposes the S0.3 intent as one MCP tool (external Claude Code can call it) **and** consumes one external MCP tool. Same governed path as in-app. | Calling the MCP tool without a grant yields the same `ungoverned`/`require-approval` behavior as in-app — not a bypass. | ☑ `5bfd80e` — `splendor_mcp` (server hosted in `blender --background`, pure-Python client), MCP JSON-RPC 2.0. **11 checks PASS on a real server subprocess**: no-grant `tools/call`→require-approval RC-SPL-001 (scene unchanged), with-grant→executed + verified read-back, invalid→deny, and the client consumes an external echo MCP server. Transport = local socket; stdio/HTTP-SSE bridge is a documented follow-up. |
| **S0.5** | Backend Router seam (P3 seam) | A text plan runs through the Router → llama.cpp/Ollama via the OpenAI-compatible shape; capability contract in place; **works offline** ([D-2.4]). | Offline + cloud-only route selected → honest "backend unavailable" error, not a hang or fabricated result (framework §2). | ☑ `893cc87` — `splendor.models` (Capability contract, OpenAI-compat adapter covering llama.cpp/Ollama/LM Studio/vLLM/OpenAI, local-first Router). **8 checks PASS** vs a real OpenAI-compat HTTP fixture: text plan routes to local; offline+cloud-only→honest `BackendUnavailable` (no hang, no fake); local-first prefers local; works offline. Router-ready for eval-scored routing later. |
| **S0.6** | Eval SDK boundary (P4 seam) | The Eval SDK, importable standalone, scores one output with one deterministic criterion (tri/palette) and records it reproducibly under a seed. | Corrupting the reference/criterion drops the score below threshold; a fixed-seed rerun is bit-identical (repro criterion). | ☑ `spl-s0.6` — standalone `splendor_eval` (criteria + hashed EvalRecord). **15 checks PASS** (also runs inside the real binary): corrupt reference→below-threshold + passed_all False, over-budget detected, fixed-seed rerun byte-identical, seed load-bearing (distinct digests), digest tracks result (pinnable provenance). |
| **S0.7** | Node/edge ⇄ LangGraph seam (P5 seam) | One agent-workflow node graph (prompt→model→eval) serializes to a LangGraph-compatible artifact and round-trips back to the same graph. | A hand-edited invalid graph fails validation on import rather than loading a broken graph. | ☑ `spl-s0.7` — `splendor.graph` (model/serialize/validate/run). **16 checks PASS** (+ Blender parity): prompt→model→eval→apply round-trips **byte-identically** (LangGraph `__start__`/`__end__` + conditional edges); invalid graphs (dangling edge, unknown type, missing start, malformed) **fail on import**; **executes across Router (P3) + Eval SDK (P4)** — conditional routes to apply when eval passes, to `__end__` when it fails. |
| **S0.8** | Chain/pinning/identity adapter interface (P7 seam) | The composable chain interface + a pin/attest call against **Citrate testnet + pinning** (or an honest error if unreachable per WP-0). AA sign-in stubbed *honestly* (named "not yet", not faked). | A tampered asset fails hash verification on retrieval; an unreachable endpoint shows an honest error, never a fake success. | ☑ `spl-s0.8` — `splendor.deploy` (content-addressed pinning, composable `ChainRegistry`, provenance, AA identity). **12 checks PASS**: pin→fetch→verify; **tamper→IntegrityError**; unreachable pinning/chain→honest `PinUnavailable`/`ChainUnavailable`; provenance ties asset(P7)+eval(P4)+workflow(P5); AA sign-in honestly `IdentityNotAvailable`. **Live Citrate endpoints UNVERIFIED** (unconfigured, no hardcoded infra). |
| **S0.9** | Upstream-diff surface report | A report of the C/C++ diff introduced vs upstream Blender (Rule 7 cost tracking) + justification per diff. | — (a file, not a claim: the report exists and lists each C change) | ☑ Standing report: **`docs/build/BUILD.md` §0** tables all 4 build-file diffs (osl/wayland/platform_unix/CMakeLists) with rationale. Each is Linux-from-source or CUDA-13 scoped. |

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
