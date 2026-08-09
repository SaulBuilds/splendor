# SPDX-License-Identifier: GPL-2.0-or-later
"""The single governed action API (invariant I-1).

Both the in-app agent and the (future) MCP server drive intents through
:func:`execute` — there is no second path. Every call:

1. validates the intent (deterministic DSL criteria),
2. passes the HIC policy gate **before** any execution (I-2),
3. emits a decision record carrying principal, grant and HIC level (I-3),
4. executes **only** on a ``PROCEED`` verdict, via the private executor registry.

A ``require-approval`` or ``deny`` verdict is recorded and returned *without*
mutating the scene — the gate is before the act, not after it. See
``.agentile/planset/02_HIC_MODEL.md`` and ``03_ACCEPTANCE_FRAMEWORK.md``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from . import dsl, hic
from . import intents as _intents

# The process-wide HIC audit trail. (Later: persisted + pinned as provenance, P7.)
_LOG = hic.DecisionLog()


def decision_log() -> hic.DecisionLog:
    """Return the shared decision log (the HIC audit trail)."""
    return _LOG


@dataclass
class ActionResult:
    executed: bool
    verdict: hic.Verdict
    record: hic.DecisionRecord
    outcome: Optional[str] = None
    error: Optional[str] = None


def execute(
    intent: dsl.Intent,
    *,
    principal: str,
    grant: Optional[hic.Grant],
    ctx: Optional[dict] = None,
    approval: "Optional[hic.Approval]" = None,
) -> ActionResult:
    """Governed execution: validate → gate → record → (only then) act.

    A matching human ``approval`` upgrades a ``require-approval`` verdict to
    ``proceed`` (recorded as approved), so a HIC-1 action can proceed once
    approved — never a bypass.
    """
    ctx = ctx or {}
    action_class = type(intent).action_class

    # 1. Validate the intent (deterministic, before touching governance).
    try:
        intent.validate()
    except ValueError as exc:
        rec = _LOG.record(
            principal=principal,
            grant_id=(grant.grant_id if grant else None),
            hic_level=hic.HicLevel.UNGOVERNED,
            action_class=action_class,
            intent_type=intent.type,
            verdict=hic.Verdict.DENY,
            rule_code="RC-SPL-000",
            reason=f"invalid intent: {exc}",
            outcome="denied",
        )
        return ActionResult(False, hic.Verdict.DENY, rec, error=str(exc))

    # 2. HIC gate BEFORE execution (I-2), with human-approval override.
    decision = hic.gate(action_class, grant, approval)

    # 3. Record the decision (I-3): principal, grant, HIC level — never dropped.
    rec = _LOG.record(
        principal=principal,
        grant_id=(grant.grant_id if grant else None),
        hic_level=decision.hic_level,
        action_class=action_class,
        intent_type=intent.type,
        verdict=decision.verdict,
        rule_code=decision.rule_code,
        reason=decision.reason,
    )

    # 4. Act ONLY on PROCEED. Anything else is recorded and returned unexecuted.
    if decision.verdict is not hic.Verdict.PROCEED:
        rec.outcome = decision.verdict.value
        return ActionResult(False, decision.verdict, rec)

    executor = _intents.REGISTRY.get(type(intent))
    if executor is None:
        rec.outcome = "no-executor"
        return ActionResult(False, hic.Verdict.DENY, rec, error="no executor for intent")

    try:
        outcome = executor(intent, ctx)
    except Exception as exc:  # executor raised — record honestly, do not swallow
        rec.outcome = f"error: {exc}"
        return ActionResult(False, decision.verdict, rec, error=str(exc))

    rec.outcome = outcome
    return ActionResult(True, decision.verdict, rec, outcome=outcome)
