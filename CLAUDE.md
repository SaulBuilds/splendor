---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# CLAUDE.md — Splendor hard rules

Start at `.agentile/AGENT_ENTRY.md`. Canonical truth is `docs/DECISIONS.md`; within the planset,
`.agentile/planset/09_DECISIONS_LOCKED.md` points at it and supersedes conflicting text anywhere else.

Splendor is a **hard fork of Blender** (GPL v2-or-later) for AI-first creators making PS1-era retro 3D.
Repo tier: **T1** — keys/identity (account abstraction), on-chain money (mint/marketplace), binary
distribution, agent governance. T1 rules apply.

## Hard rules (non-negotiable)

1. **No mocks (Rule 1).** No mocked data, fake fixtures presented as live, or placeholder features that
   pretend to work. Every surface states what is real. AI output is real model output or an honest error.
   Chain/pinning calls hit a live endpoint or show an honest error. An unbuilt surface ships named honestly
   or does not ship. **Everything in a shipped slice is wired end-to-end** ([D-8.2]); a button that does
   nothing is a defect, not a placeholder.

2. **Acceptance criteria forbid interpretation (Rule 2).** Every work package carries objective,
   negative-controlled acceptance criteria per `.agentile/planset/03_ACCEPTANCE_FRAMEWORK.md`. A WP is not
   done until its check **fails on a deliberately broken build**. "A mint button exists" is not a criterion;
   "the minted token's metadata URI resolves to a pinned glTF whose hash matches the export and embeds the
   recorded eval score" is.

3. **Test/eval counts are monotone.** Test counts never silently decrease; record the count when it changes.
   Eval-harness golden sets never shrink without a written decision.

4. **AI acts through the governed action API only (Rule 4).** Both the in-app agent and external MCP clients
   drive the *same* typed DSL/operator surface. Every AI action passes the **HIC policy gate before
   execution** and produces a decision record. A prompt instructing the model to behave is not a control
   (see `.agentile/planset/02_HIC_MODEL.md`).

5. **HIC levels are per-action, not global.** Every recorded action carries principal, grant, and HIC level
   (HIC-0 Observed → HIC-1 ApproveEach → HIC-2 Budgeted → HIC-3 PostHoc → X Ungoverned). An action without a
   live grant is recorded `ungoverned` and surfaced — never silently allowed, never silently dropped.
   Chain/money/key/mint actions default to **HIC-1**.

6. **Model-agnostic by construction.** No feature hardcodes a model or provider. All inference/training goes
   through the backend capability contract + Router seam; selection is by declared capability + eval score
   ([D-2.2/2.4]). Local-first is the default; the Router must work fully offline.

7. **Minimize the fork tax.** Prefer Python/extensions over C/C++ diffs. Every C-level change must justify
   itself in its PR against "could this be an extension?" — the diff surface against upstream Blender is a
   tracked cost. Do not gratuitously diverge from Blender's core UX.

8. **GPL boundary discipline.** Everything distributed in the app is GPL. Value-capture code lives behind the
   network (services) or on-chain, never as closed features in the binary ([D-9.2]). Keep any non-GPL server
   code at genuine arm's length + documented ([D-9.8]). Publish complete corresponding source per build.

9. **Never commit to main.** Feature branch + PR via `gh`. Commit with explicit paths (`git add <paths>`,
   never `-A`/`.`). Never merge — the owner merges. (The initial scaffold commit is the sole exception.)

10. **Every doc gets YAML frontmatter** (created, branch, author, status).

11. **Link, don't copy (Rule 9).** `docs/` holds canonical architecture/decisions; the planset points at it.
    The HIC scheme is inherited from Citrate's `quorum-audit` — cite it, don't reinvent it.

12. **Data-source tracing (Rule 11).** Every UI surface names the command/operator it calls; every command
    names the model call, chain method, RPC, or store it reads. No surface renders a number (tri-count, eval
    score, price) whose origin cannot be stated.

## Regulatory gates (⚖️ — see `docs/business/BUSINESS_MODEL_AND_GPL.md`)

- **No token** ships without securities counsel + genuine non-investment utility ([D-9.6]).
- **No custodial key flow** ([D-9.9]); prefer non-custodial AA with optional gas sponsorship.
- **No compliance/legal claims** in product, docs, or decks that only counsel can supply (GPL fitness,
  securities status, custody licensing). State what is real; defer legal conclusions to counsel ([D-9.7]).
- Mint / marketplace / royalty surfaces are **counsel-gated before Phase 1**.

## Commits

End commits with:
`Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`
