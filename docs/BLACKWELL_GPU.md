---
created: 2026-08-09
branch: feat/spl-blackwell-gpu
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# Blackwell (GB10) GPU enablement

The dev box is an NVIDIA **GB10** (Grace-Blackwell, compute 12.1 → `sm_121`), which requires CUDA 13.

## Status — CUDA VERIFIED (2026-08-09)
- **CUDA device detected out of the box** — `WITH_CYCLES_DEVICE_CUDA=ON` (default). Cycles lists `NVIDIA GB10 · CUDA`.
- **GPU rendering works** — Cycles path-traces on the GB10. Proof: `docs/design/gpu-render-gb10.png` (a 64px Cycles **GPU** render of the default cube).
- **First render is slow** — the WP-0 binary ships without precompiled kernels, so Cycles compiles the `sm_121`
  megakernel at runtime with `ptxas` (~5 min the first time; cached after).

## Fast (precompiled) GPU build
`nvcc 13` supports `compute_121`. CUDA 13 **removed** `sm_50/52/60/70`, so the default arch list is now
toolkit-aware (`CMakeLists.txt`) — on CUDA ≥ 13 it targets `sm_75 … sm_121`. To ship precompiled kernels:

```
make BUILD_CMAKE_ARGS="-DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121"
```

(`sm_121` alone keeps the build fast on this box; the default list covers Turing→Blackwell.)

## OptiX (hardware RT) — deferred
`WITH_CYCLES_DEVICE_OPTIX` needs the NVIDIA **OptiX SDK** (headers, EULA-gated download) — not present here.
OSL-on-OptiX is also off; its dep build hardcoded `sm_50`, but the arch is no longer the blocker — the SDK
is. Re-enable with `-DOPTIX_ROOT_DIR=…` once the SDK is provided (then bump OSL's `CUDA_TARGET_ARCH` to a
supported arch in `build_files/build_environment/cmake/osl.cmake`).
