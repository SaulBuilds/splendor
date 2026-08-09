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
- **Precompiled build VERIFIED (2026-08-09)** — a `-DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121`
  build installs `kernel_sm_121.cubin.zst` (32.5 MB) to `bin/5.3/scripts/addons_core/cycles/lib/`; a GPU render
  with the kernel cache **cleared** completes in **0.88 s** (vs ~5 min runtime compile) — proving the
  precompiled kernel is loaded, not recompiled. Production-ready.
- **First render is slow** — the WP-0 binary ships without precompiled kernels, so Cycles compiles the `sm_121`
  megakernel at runtime with `ptxas` (~5 min the first time; cached after).

## Fast (precompiled) GPU build
`nvcc 13` supports `compute_121`. CUDA 13 **removed** `sm_50/52/60/70`, so the default arch list is now
toolkit-aware (`CMakeLists.txt`) — on CUDA ≥ 13 it targets `sm_75 … sm_121`. To ship precompiled kernels:

```
make BUILD_CMAKE_ARGS="-DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121"
```

(`sm_121` alone keeps the build fast on this box; the default list covers Turing→Blackwell.)

## OptiX (hardware RT) — ENABLED & VERIFIED (2026-08-09)
Built with the **OptiX 9.1.0 SDK** (Blender 5.3 requires ≥ 8.0.0) extracted to `~/optix-9.1.0`:
```
CC=gcc-14 CXX=g++-14 make BUILD_CMAKE_ARGS="\
  -DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14 \
  -DWITH_CYCLES_DEVICE_OPTIX=ON -DOPTIX_ROOT_DIR=$HOME/optix-9.1.0 \
  -DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121"
```
cmake reported `Found OptiX … suitable version 9.1.0`. The **OptiX device is detected**
(`NVIDIA GB10 · OPTIX`) and a Cycles **OptiX hardware-RT render completes in ~0.48 s** (even faster than the
CUDA path's 0.9 s). Only the OptiX SDK *headers* are needed (arch-portable); the runtime is the driver's
`libnvoptix.so.1`, already present.

**GPU OSL on OptiX** remains a further step: `build_files/build_environment/cmake/osl.cmake` still has its
OptiX block `if(FALSE)` — re-enable it and change `sm_50` → a CUDA-13-supported arch (`sm_90`), with the
OptiX SDK available to the deps build. Not required for Cycles OptiX (verified above).
