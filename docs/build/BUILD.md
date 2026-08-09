---
created: 2026-08-09
branch: docs/spl-build-handoff
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# Splendor — Build runbook & platform handoff

Splendor is a hard fork of **Blender 5.3.0 Alpha** (GPL v2-or-later). This is the reproducible build
runbook. **Linux is verified** (built + GPU-rendered on the dev box); **Windows and macOS are a handoff** —
the steps are the standard Blender process plus the Splendor-specific notes below, but nobody has run them
yet, so they are marked HANDOFF.

> Base commit hash of the fork: run `git log -1` after cloning. The dev build was `blender 5.3.0 Alpha`,
> build hash `6741bb1d92a`.

---

## 0. The Splendor build-file diffs (why a plain Blender build isn't enough)

Three committed changes vs upstream Blender make the fork build on modern toolchains (all in-tree; you do
**not** apply them by hand). They are also the answer to "what did we change in the build":

| File | Change | Why |
|---|---|---|
| `build_files/build_environment/cmake/osl.cmake` | disable OSL OptiX (`if(FALSE)`) | OSL hardcodes `CUDA_TARGET_ARCH=sm_50`, which CUDA 13 removed. GPU OSL deferred (needs OptiX SDK anyway). |
| `build_files/build_environment/cmake/wayland.cmake` | pin meson `--libdir lib64` | Ubuntu multiarch installs to `lib/aarch64-linux-gnu`; the harvest expects `lib64`. |
| `build_files/cmake/platform/platform_unix.cmake` | link `libdrm` to ffmpeg | from-source ffmpeg builds the DRM hwcontext → the final link needs `-ldrm`. |
| `CMakeLists.txt` | CUDA arch list is toolkit-aware | CUDA 13 removed `sm_50/52/60/70`; on nvcc ≥ 13 the default targets `sm_75 … sm_121` (Blackwell). |

The wayland/drm fixes are **Linux-from-source** concerns (they don't affect Windows/macOS, which use
Blender's precompiled libraries). The OSL and CUDA-arch changes apply anywhere OSL/CUDA are built from source.

---

## 1. Get the source (all platforms)

```
git clone https://github.com/SaulBuilds/splendor.git
cd splendor
```

**LFS gotcha (important):** a GitHub fork does **not** inherit Blender's Git-LFS objects (brushes,
`startup.blend`, fonts…) — you'll see `404 Object does not exist`. `make update` installs a fallback LFS
remote to `projects.blender.org`; materialize the assets with:

```
git lfs install
make update            # sets up the projects.blender.org LFS fallback + fetches libraries
git lfs pull lfs-fallback   # if the checkout left LFS files as pointers
```

The build fails at `cmake` ("incomplete startup blend") without these.

---

## 2. Linux — VERIFIED (aarch64 GB10; x86_64 should be easier)

### 2a. System packages
```
sudo apt-get update && sudo apt-get install -y \
  build-essential gcc-14 g++-14 git git-lfs cmake ninja-build meson \
  autoconf automake libtool libtool-bin yasm nasm help2man autogen gettext autopoint texinfo \
  bison flex patch patchelf tcl bzip2 wget pkg-config perl \
  python3-dev python3-pip python3-mako python3-yaml libncurses-dev \
  libx11-dev libx11-xcb-dev libxxf86vm-dev libxcursor-dev libxi-dev libxrandr-dev libxinerama-dev \
  libxt-dev libxkbcommon-dev libegl-dev libgl-dev libglu1-mesa-dev \
  libcairo2-dev libdrm-dev libpixman-1-dev libffi-dev libinput-dev libevdev-dev libgbm-dev libudev-dev \
  libasound2-dev libpulse-dev libjack-jackd2-dev
```
**GCC 14 is required** (Blender's minimum; Ubuntu 24.04 ships 13).

### 2b. Dependencies
- **aarch64:** Blender publishes **no `linux_arm64` precompiled libraries**, so build them from source
  (multi-hour, one-time):
  ```
  python3 build_files/utils/make_update.py --no-blender --architecture arm64
  make deps     # if the above didn't build them; installs into lib/linux_arm64
  ```
  If a source download times out (e.g. GMP from gmplib.org), pre-place it from a mirror into
  `../build_<os>/deps_<arch>/packages/` (verify the MD5 in `build_files/build_environment/cmake/versions.cmake`)
  and re-run — `make deps` is resumable.
- **x86_64:** precompiled libs exist — just `make update` (no `make deps`).

### 2c. Build
```
CC=gcc-14 CXX=g++-14 make BUILD_CMAKE_ARGS="\
  -DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14 \
  -DWITH_CYCLES_DEVICE_OPTIX=OFF -DWITH_CYCLES_DEVICE_HIP=OFF -DWITH_CYCLES_DEVICE_ONEAPI=OFF"
```
Output: `../build_linux/bin/blender`. Launch: `./bin/blender --version`.

### 2d. GPU (CUDA) — see §5. A precompiled-kernel build adds:
`-DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121` (use your GPU's arch).

---

## 3. Windows — HANDOFF (not yet run by us)

Windows is **easier than aarch64 Linux** because Blender ships precompiled libraries (`lib/windows_x64`,
`lib/windows_arm64`) — no `make deps`.

1. **Tools:** Visual Studio 2022 (Desktop C++), CMake, Git + Git LFS, Python 3.11+, and the CUDA 12/13
   toolkit for GPU. (See Blender's own "Building Blender/Windows" handbook for the canonical prerequisites.)
2. **Source + LFS:** clone, then `make.bat update` (fetches precompiled libs + sets the LFS fallback). If
   LFS files are pointers, `git lfs pull lfs-fallback`.
3. **Build:** `make.bat` (or `make.bat release`). Output under `..\build_windows_*\bin\`.
4. **Splendor notes:**
   - The wayland/drm fixes do not apply (Windows). The OSL fix only matters if OSL is built from source;
     Windows uses the precompiled OSL, so it's a no-op there.
   - GPU: CUDA works out of the box on Windows/x64 if the toolkit is installed; set
     `WITH_CYCLES_CUDA_BINARIES=ON` with your arch. OptiX: see §6.
   - `windows_arm64` libs exist, so an ARM64 Windows build is possible but doubly untested.
5. **Verify:** run the suite (§7) — `SPLENDOR_BLENDER` must point at the built `blender.exe`; the shell
   parts of `scripts/ci/run_tests.sh` need Git-Bash/WSL.

---

## 4. macOS — HANDOFF (not yet run by us)

macOS also ships precompiled libs (`lib/macos_arm64`) — no `make deps`.

1. **Tools:** Xcode + command-line tools, CMake, Git + Git LFS, Python 3.11+.
2. **Source + LFS:** clone, `make update`, `git lfs pull lfs-fallback` if needed.
3. **Build:** `make` (Apple Silicon → `macos_arm64`, Metal GHOST backend). Output `../build_darwin/bin/`.
4. **Splendor notes:**
   - GPU is **Metal**, not CUDA — the CUDA/OptiX sections don't apply; Cycles uses the Metal device.
   - The **USDZ / RealityKit** export target (D-6.1) is most relevant here; verify `WITH_USD` (on by default).
   - The Linux-from-source fixes (wayland/drm/OSL-sm50) are no-ops on macOS (precompiled libs).
5. **Verify:** run the suite (§7) with `SPLENDOR_BLENDER=../build_darwin/bin/Blender.app/Contents/MacOS/Blender`.
   (The retro-shader GPU test uses Metal there; it may need a windowing context — see the headless note in §7.)

---

## 5. GPU — CUDA (verified) / Blackwell

- The **CUDA device is detected out of the box** (`WITH_CYCLES_DEVICE_CUDA=ON`).
- **Verified on the GB10** (compute 12.1 → `sm_121`): a precompiled build
  (`-DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121`) installs `kernel_sm_121.cubin.zst`
  and renders in **~0.9 s** (vs ~5 min runtime-compile). Details: `docs/BLACKWELL_GPU.md`.
- Without precompiled binaries, Cycles compiles the kernel at runtime on first GPU render (slow, then cached).

---

## 6. OptiX (hardware ray tracing) — ENABLED & VERIFIED (2026-08-09)

The OptiX **driver runtime** (`libnvoptix.so.1`) is present. The **OptiX SDK headers** are login + EULA
gated on `developer.nvidia.com` (can't be fetched unattended), but once downloaded it's one step —
**verified** with the **OptiX 9.1.0 SDK**: the OptiX device is detected (`NVIDIA GB10 · OPTIX`) and a Cycles
hardware-RT render completes in ~0.48 s (`docs/BLACKWELL_GPU.md`). To reproduce:

1. With a (free) NVIDIA developer account, download the **OptiX SDK 8.x** and run/extract it to a path,
   e.g. `~/optix-8.0.0`. Only the `include/` headers are needed (they're arch-portable).
2. Build with:
   ```
   CC=gcc-14 CXX=g++-14 make BUILD_CMAKE_ARGS="\
     -DCMAKE_C_COMPILER=gcc-14 -DCMAKE_CXX_COMPILER=g++-14 \
     -DWITH_CYCLES_DEVICE_OPTIX=ON -DOPTIX_ROOT_DIR=$HOME/optix-8.0.0 \
     -DWITH_CYCLES_CUDA_BINARIES=ON -DCYCLES_CUDA_BINARIES_ARCH=sm_121"
   ```
3. Verify the OptiX device appears:
   `blender -b --factory-startup --python-expr "import bpy; p=bpy.context.preferences.addons['cycles'].preferences; p.compute_device_type='OPTIX'; p.refresh_devices(); print([d.name for d in p.devices if d.type=='OPTIX'])"`
4. **GPU OSL on OptiX** is a further step: re-enable the block in
   `build_files/build_environment/cmake/osl.cmake` (currently `if(FALSE)`) and change `sm_50` →
   `sm_90` (a CUDA-13-supported arch), with the OptiX SDK available to the deps build. Not required for
   Cycles OptiX.

If you place the SDK on disk (or paste the download command with your session), Splendor can be rebuilt with
OptiX in one step — everything else is prepared.

---

## 7. Verify any build (local CI)

```
SPLENDOR_BLENDER=/path/to/blender bash scripts/ci/run_tests.sh
```
Runs all `tests/splendor/` suites (12 as of this writing). Pure-Python suites run under `python3`;
Blender-runtime suites under `blender --background`. Exit non-zero on any failure. The pre-push git hook
(`scripts/ci/install-hooks.sh`) runs this before every push.

**Headless GUI note:** the visual pass renders under `xvfb-run … blender --gpu-backend vulkan` (the NVIDIA
GL path can't attach to a virtual X display; Vulkan can). See `docs/design/spl-s1-*.png`.

## 8. Citrate deploy — local IPFS pinning (Ship)

Citrate pinning **is** IPFS. The **Ship** step (`splendor.deploy.IpfsPinning`) pins the asset to a
running IPFS daemon and records the content-addressed CID; unreachable fails honestly (never a faked CID).

Install [Kubo](https://docs.ipfs.tech/install/command-line/) (`ipfs`), then:
```
ipfs init            # once
ipfs daemon          # RPC API :5001, gateway :8080
```
Ship uses the Citrate config (`scripts/modules/splendor/deploy/citrate.py`) — defaults API
`http://127.0.0.1:5001`, gateway `http://127.0.0.1:8080`. Override per environment:
```
export CITRATE_IPFS_API=http://127.0.0.1:5001
export CITRATE_IPFS_GATEWAY=http://127.0.0.1:8080
```
`SPLENDOR_CITRATE_PINNING=<url>` overrides with a custom HTTP pinning service instead of the IPFS daemon.
Verify end-to-end (pin → CID → fetch round-trip against a live daemon, skip-safe when none is running):
```
python3 tests/splendor/test_s0_8_citrate_live.py
```

**On-chain attestation** (provenance/mint) is honestly deferred: `CitrateEvmChain.attest()` raises
`ChainUnavailable` until a non-custodial signer is wired — the live chain is read-only here (chain 40204,
`rpc.citrate.ai`). Reads (`chain_id`, `block_number`) work today.
