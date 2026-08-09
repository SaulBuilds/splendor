---
created: 2026-08-08
branch: main
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# 02 — HIC Model (normative)

> **Read this before writing anything that lets an agent act in Splendor.** HIC = **Human In Control**
> (never "HITL" — [D-4.1]). Autonomy is graduated, not binary. Splendor reuses the canonical Citrate scheme
> from `citrate-quorum`'s `quorum-audit` crate — it is **inherited, not reinvented** (Rule 11).

## The autonomy ladder ([D-4.2])

| Level | Name | Meaning |
|-------|------|---------|
| **HIC-0** | Observed | Agent acts; every action is recorded/observed. |
| **HIC-1** | ApproveEach | Each action requires explicit human approval before it proceeds. |
| **HIC-2** | Budgeted | Agent acts freely within a granted budget/envelope; over-ceiling escalates to HIC-1. |
| **HIC-3** | PostHoc | Agent acts; human reviews after the fact. |
| **X** | Ungoverned | No governance. An action with no live grant is recorded here **and surfaced** — never silently allowed. |

## Non-negotiable enforcement rules

1. **Gate before act (Rule 4 / I-2).** Every AI action — whether initiated by the in-app agent or an
   external MCP client — passes the HIC policy gate **before execution**, producing a `Verdict`
   (`proceed` / `require-approval` / `deny`) with a declarative rule code. The gate lives at the tool-call
   boundary of the single governed action API (I-1). A prompt telling the model to behave is documentation,
   not a control.
2. **Per action, not global (Rule 5 / I-3).** Every decision record carries principal, grant id, and the
   HIC level in force. No global "autonomy setting" substitutes for a per-action grant.
3. **Default sensitive actions to HIC-1.** Chain, money, key, mint, license, and destructive-file actions
   default to **ApproveEach** even when covered by a broader budget. Bulk creative operations (mesh edits
   inside a retro budget) are the natural HIC-2 case.
4. **Ungoverned is loud.** An action with no live grant is recorded `ungoverned` and surfaced in the HIC
   control bar — never dropped, never silently permitted.
5. **Records are evidence.** HIC records feed the Eval SDK, on-chain provenance (P7), and the captured-
   workflow memory. "What the agent did, under what authority, and how it scored" is one reconstructable
   trail.

## Alignment with the Citrate stack

Splendor's HIC levels, verdicts, and rule-code style mirror `quorum-policy` / `quorum-audit` so a creator
who also uses Citrate tools meets one governance model. Where Splendor adds on-chain actions, the on-chain
half of the envelope maps to the same `CapabilityGrant` / `BudgetedAutonomy` pattern. Do not fork the
concept; extend it.

## Surface

The **HIC Control Bar** (see the design handoff) shows the current level, surfaces `require-approval`
inline, and makes `ungoverned` visible. Legible autonomy is a design requirement, not a nicety: the user
must always know what the agent is about to do, is doing, and did.
