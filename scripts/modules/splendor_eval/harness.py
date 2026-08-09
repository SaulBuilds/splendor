# SPDX-License-Identifier: GPL-2.0-or-later
"""The Eval harness — runs criteria over a subject and produces a reproducible,
hashable record.

The :class:`EvalRecord` is content-hashed (excluding the timestamp), so the same
subject + seed + criteria always yields the same digest: reproducible, and
pinnable as on-chain provenance (P7 — "an eval score is provenance", I-6). This
is the standalone measurement backbone the rest of Splendor is judged by (D-3.3).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field


@dataclass
class EvalRecord:
    subject_id: str
    seed: int
    results: list          # list[CriterionResult]
    aggregate: float
    passed_all: bool
    digest: str
    ts: float = field(default_factory=time.time)

    def to_dict(self, include_ts: bool = True) -> dict:
        d = {
            "subject_id": self.subject_id,
            "seed": self.seed,
            "aggregate": self.aggregate,
            "passed_all": self.passed_all,
            "results": [
                {"name": r.name, "value": r.value, "passed": r.passed,
                 "threshold": r.threshold, "detail": r.detail}
                for r in self.results
            ],
            "digest": self.digest,
        }
        if include_ts:
            d["ts"] = self.ts
        return d


def _canonical(subject_id, seed, results, aggregate, passed_all) -> str:
    """Deterministic, timestamp-free serialization used for hashing + repro checks."""
    payload = {
        "subject_id": subject_id,
        "seed": seed,
        "aggregate": round(float(aggregate), 9),
        "passed_all": bool(passed_all),
        "results": [
            {"name": r.name, "value": r.value, "passed": r.passed, "threshold": r.threshold}
            for r in results
        ],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class EvalHarness:
    def __init__(self, criteria):
        self.criteria = list(criteria)

    def evaluate(self, subject: dict, subject_id: str, seed: int = 0) -> EvalRecord:
        results = [c.evaluate(subject, seed) for c in self.criteria]
        aggregate = round(sum(r.value for r in results) / len(results), 9) if results else 0.0
        passed_all = all(r.passed for r in results)
        canonical = _canonical(subject_id, seed, results, aggregate, passed_all)
        digest = "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
        return EvalRecord(subject_id, seed, results, aggregate, passed_all, digest)

    def canonical(self, record: EvalRecord) -> str:
        """The exact bytes hashed — for bit-identical reproducibility assertions."""
        return _canonical(record.subject_id, record.seed, record.results,
                          record.aggregate, record.passed_all)
