---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# Splendor

**A hard fork of Blender for AI-first creators making PS1-era retro 3D animation, game assets, and on-chain
creative work.** Everything Blender does, plus a native AI harness (in-app agent + MCP server), a
model-agnostic backend, a first-class eval/benchmark SDK, HIC governance, a node/edge language that unifies
Blender nodes with LangGraph agent workflows, and a deploy layer to the web and CitrateNetwork.

## Honest current status (2026-08-08)

**This is a planning workspace, not yet code.** What exists:

- ✅ The fork: https://github.com/SaulBuilds/splendor (server-side, not cloned locally yet).
- ✅ `docs/DECISIONS.md` — the 31 founding decisions + resolved business model (§9).
- ✅ `docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md` — the 7 pillars + data flow + v0 slice.
- ✅ `docs/business/BUSINESS_MODEL_AND_GPL.md` — the GPL-bounded business model.
- ✅ `docs/handoff/CLAUDE_DESIGN_HANDOFF.md` — the design wiring contract.
- ✅ `.agentile/` — the agentile scaffold (this methodology), with the first sprint (SPL-S0) scoped.

What does **not** exist yet: any Splendor source, a local fork checkout, a build, or any running feature.
Nothing here is claimed to work that does not. See `.agentile/sprints/active/sprint-spl-s0/SCOPE.md` for the
first buildable sprint.

## Read next

- `.agentile/AGENT_ENTRY.md` — start here (human or AI).
- `CLAUDE.md` — the hard rules.

## License

Splendor is a fork of Blender and is distributed under the **GNU GPL v2-or-later**, same as Blender. See the
GPL boundary discussion in `docs/business/BUSINESS_MODEL_AND_GPL.md` for how this shapes the project.
