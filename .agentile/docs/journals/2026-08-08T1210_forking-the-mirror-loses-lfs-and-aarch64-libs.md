---
created: 2026-08-08
branch: chore/splendor-planning-scaffold
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# Forking the mirror loses the LFS, and there are no aarch64 Linux libs

The first hour of WP-0 was not spent on Splendor at all. It was spent discovering two facts about the
ground we chose to build on — neither visible from the architecture spec, both surfaced only by trying to
actually clone and build the thing.

**One: a GitHub fork of `blender/blender` does not carry the Git-LFS objects.** The clone succeeded and
then the checkout failed mid-way — `404 Object does not exist on the server` — because the 6,755 LFS-tracked
binary assets (brushes, `startup.blend`, fonts, test data) live on Blender's LFS server, and a fork's LFS
storage is empty. The working tree was left incomplete. Blender anticipated this: `make update` installs a
*fallback LFS remote* pointing at `projects.blender.org`, and `git lfs pull lfs-fallback` materializes the
files from the canonical source. But you only learn you need it when `cmake` refuses to configure with
"Detected incomplete startup blend, likely due to missing Git LFS checkout." The build depends on data the
fork does not contain.

**Two: Blender publishes no precompiled libraries for Linux on aarch64.** `.gitmodules` has lib bundles for
`linux_x64`, `macos_arm64`, `windows_x64`, and `windows_arm64` — and nothing for `linux_arm64`. On the
Grace-class ARM box this is, the default build (which expects precompiled libs) hard-errors on a missing
`LIBDIR`. The only paths are a system-libraries build or compiling every dependency from source with
`make deps`. We chose `make deps`: full fidelity, multi-hour, 53 apt packages of prerequisites first.

The lesson is not "Blender is hard to fork." It is that **the platform assumptions in a plan are the ones
most worth checking first, because they are the ones a document cannot check for you.** The architecture
spec was right about the seven pillars and said nothing wrong — it simply could not know this machine was
aarch64 or that the fork would arrive without its own assets. The acceptance framework's "measure against
reality before building" is exactly this: the honest report about the ground gets written down *before* it
becomes an inconvenient surprise at a gate three sprints later.

A footnote that may yet matter: this box has CUDA 13.0; Blender's reference environment version-locks 12.8
for OpenImageDenoise. If the OIDN dep chokes on the newer toolkit, that is the next thing this journal's
sequel will be about.
