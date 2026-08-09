# SPDX-License-Identifier: GPL-2.0-or-later
"""HIC (Human In Control) governance for the Splendor action API.

Reuses the canonical Citrate ``quorum-audit`` ladder verbatim — HIC, never HITL;
autonomy is graduated, not binary. See ``.agentile/planset/02_HIC_MODEL.md``.

This module is pure Python (no ``bpy``) so the governance layer is importable and
testable outside Blender, and reusable by the (future) MCP server and agent.
"""
from __future__ import annotations

import enum
import itertools
import time
from dataclasses import dataclass, field
from typing import Optional


class HicLevel(enum.Enum):
    """The autonomy ladder (mirrors ``quorum-audit``'s ``HicLevel``)."""

    OBSERVED = 0        # HIC-0: agent acts; every action recorded/observed.
    APPROVE_EACH = 1    # HIC-1: each action requires explicit human approval.
    BUDGETED = 2        # HIC-2: acts within a budget; over-ceiling escalates to HIC-1.
    POST_HOC = 3        # HIC-3: acts; human reviews after the fact.
    UNGOVERNED = 0xFF   # X: no governance (recorded and surfaced, never silent).

    @property
    def tag(self) -> int:
        return self.value


class Verdict(enum.Enum):
    PROCEED = "proceed"
    REQUIRE_APPROVAL = "require-approval"
    DENY = "deny"


# Action classes that always default to HIC-1 approve-each, even under a broader
# grant (chain / money / key / mint / grant / destructive). D-4.3 / CLAUDE Rule 5.
SENSITIVE_ACTION_CLASSES = frozenset(
    {"chain", "money", "key", "mint", "grant", "destructive"}
)


@dataclass(frozen=True)
class Grant:
    """A live authority for a principal to act within an envelope."""

    grant_id: str
    principal: str
    hic_level: HicLevel
    action_classes: frozenset  # which action classes this grant covers
    budget: Optional[int] = None  # HIC-2: remaining actions; None == unlimited

    def covers(self, action_class: str) -> bool:
        return action_class in self.action_classes


@dataclass(frozen=True)
class PolicyDecision:
    """The gate's verdict for one (action_class, grant) pair."""

    verdict: Verdict
    hic_level: HicLevel
    rule_code: str
    reason: str


class PolicyBinding:
    """Maps ``(action_class, grant)`` to a :class:`PolicyDecision`.

    Mirrors ``quorum-policy``'s ``PolicyBinding.check -> Verdict`` with declarative
    rule codes. This is the enforcement point the action API calls *before* any
    execution (invariant I-2). A prompt is not a control; this is.
    """

    @staticmethod
    def check(action_class: str, grant: Optional[Grant]) -> PolicyDecision:
        # RC-SPL-001: no live grant -> ungoverned, approval required, surfaced.
        if grant is None:
            return PolicyDecision(
                Verdict.REQUIRE_APPROVAL, HicLevel.UNGOVERNED,
                "RC-SPL-001", "no live grant → ungoverned, approval required",
            )
        # RC-SPL-002: grant does not cover this action class.
        if not grant.covers(action_class):
            return PolicyDecision(
                Verdict.REQUIRE_APPROVAL, HicLevel.APPROVE_EACH,
                "RC-SPL-002", f"grant does not cover action class '{action_class}'",
            )
        # RC-SPL-003: sensitive classes are HIC-1 even when covered.
        if action_class in SENSITIVE_ACTION_CLASSES:
            return PolicyDecision(
                Verdict.REQUIRE_APPROVAL, HicLevel.APPROVE_EACH,
                "RC-SPL-003", f"sensitive action class '{action_class}' → HIC-1 approve-each",
            )
        # Otherwise, governed by the grant's declared level.
        lvl = grant.hic_level
        if lvl is HicLevel.APPROVE_EACH:
            return PolicyDecision(Verdict.REQUIRE_APPROVAL, lvl, "RC-SPL-010", "HIC-1 approve-each grant")
        if lvl is HicLevel.BUDGETED:
            # NOTE: budget is checked here but not yet *decremented* across calls
            # (needs a mutable grant store — a documented S0.x follow-up, not a
            # mock). The over-ceiling escalation path below is real.
            if grant.budget is not None and grant.budget <= 0:
                return PolicyDecision(
                    Verdict.REQUIRE_APPROVAL, lvl, "RC-SPL-011",
                    "HIC-2 budget exhausted → escalate to approve-each",
                )
            return PolicyDecision(Verdict.PROCEED, lvl, "RC-SPL-012", "within HIC-2 budget")
        if lvl in (HicLevel.OBSERVED, HicLevel.POST_HOC):
            return PolicyDecision(Verdict.PROCEED, lvl, "RC-SPL-013", f"{lvl.name} → proceed, recorded")
        # An explicitly UNGOVERNED grant.
        return PolicyDecision(Verdict.PROCEED, HicLevel.UNGOVERNED, "RC-SPL-099", "ungoverned grant")


@dataclass
class DecisionRecord:
    """One governed action's evidence unit (I-3: principal, grant, HIC level).

    Later persisted and pinned as on-chain provenance (P7). For now, in-memory.
    """

    seq: int
    principal: str
    grant_id: Optional[str]
    hic_level: HicLevel
    action_class: str
    intent_type: str
    verdict: Verdict
    rule_code: str
    reason: str
    outcome: Optional[str] = None  # set after execution (or the blocked verdict)
    ts: float = field(default_factory=time.time)


class DecisionLog:
    """The HIC audit trail — an append-only log of decision records."""

    def __init__(self) -> None:
        self._records: list[DecisionRecord] = []
        self._counter = itertools.count(1)

    def record(self, **kw) -> DecisionRecord:
        rec = DecisionRecord(seq=next(self._counter), **kw)
        self._records.append(rec)
        return rec

    def all(self) -> list[DecisionRecord]:
        return list(self._records)

    def last(self) -> Optional[DecisionRecord]:
        return self._records[-1] if self._records else None
