---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# Splendor — Agent Operations Policy

> How work is conducted in Splendor. This is the *cadence and sign-off* layer; the *hard rules* live in
> `../../CLAUDE.md` and are not restated here. Where this policy and CLAUDE.md appear to conflict, CLAUDE.md
> wins. Tier: **T1**.

## 1. The loop

1. **Measure reality** → **SCOPE** → **build WPs (vertical slices + negative controls)** → **exit gate** →
   **RETRO + journal** → next sprint. (`../planset/03_ACCEPTANCE_FRAMEWORK.md`.)
2. Exactly one sprint is `active` at a time under `sprints/active/`; on close it moves to
   `sprints/completed/` with a `RETRO.md`.
3. Every sprint's assumptions are checked against the real code/chain/tooling **before** its SCOPE is
   finalized. An unverified dependency may not be claimed live.

## 2. Records (the development history)

| Record | When | Where |
|--------|------|-------|
| SCOPE.md | Sprint start | `sprints/active/<sprint>/` |
| RETRO.md | Sprint close (honest: what didn't work too) | `sprints/completed/<sprint>/` |
| Journal | After a non-trivial session; a durable lesson | `docs/journals/` |
| Essay | A conceptual argument worth outliving its sprint | `docs/essays/` |
| Decision record | An owner call that changes what the rules permit | `docs/decisions/` (canonical ledger: `../../docs/DECISIONS.md`) |
| Audit | A claim re-tested rather than re-read | `docs/audits/` |

## 3. Sign-off gates (T1)

- **Owner merges.** Agents open PRs; the owner (@SaulBuilds) merges. Never commit to `main` (except the
  initial scaffold commit).
- **Governance in-PR.** Any change that lets an agent act ships its HIC gate + grant check + decision
  record in the *same* PR (I-2), or it is not accepted.
- **Counsel gates (⚖️).** Mint/marketplace/royalty/token/custody surfaces do not ship past a testnet
  provenance/pin call until IP + securities/custody counsel sign off ([D-9.7]). No legal/compliance claims
  in product or docs.
- **Design gate.** User-facing surfaces pass the Claude Design → Emma review loop before they are called
  done for UX; Claude Code holds final say on behavior, Emma on design/UX ([D-8.5]).
- **Fork-tax gate.** Every PR with a C/C++ diff carries a one-line justification vs "could this be an
  extension?" and updates the upstream-diff surface report (Rule 7).

## 4. Team & roles (until v1 → then OSS)

| Who | Final say on |
|-----|--------------|
| @SaulBuilds | Product direction, owner decisions, merges, business/regulatory calls. |
| Claude Code | Feature behavior, wiring, the action API, acceptance criteria. |
| Claude Design | Visual/interaction design, prototypes (expression of the handoff contract). |
| Emma (SME) | Design/UX and whether functionality serves real game-maker workflows. |

At v1 the mirrored repo opens to an OSS community ([D-8.3]); a trademark-usage + contribution policy lands
with that launch.

## 5. Commit hygiene

- Feature branch + PR via `gh`; explicit paths on `git add` (never `-A`/`.`).
- YAML frontmatter on every doc (created, branch, author, status).
- End commits with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
