# SPDX-License-Identifier: GPL-2.0-or-later
"""Provenance records (P7) — the thing that gets attested.

Ties the pillars together: a pinned asset's CID (P7), the eval digest (P4), and
the workflow that produced it (P5). Content-hashed so "this creator made this,
with these tools/models, scoring X" is one reconstructable, attestable fact
(I-6). Keeping provenance FREE seeds the deploy loop (business §9.3).
"""
from __future__ import annotations

import hashlib
import json


def make_provenance(asset_cid, eval_digest=None, workflow=None, meta=None) -> dict:
    record = {
        "schema": "splendor.provenance/v1",
        "asset": asset_cid,        # pinning CID (P7)
        "eval": eval_digest,       # Eval SDK digest (P4)
        "workflow": workflow,      # LangGraph artifact / its hash (P5)
        "meta": dict(meta or {}),
    }
    canon = json.dumps(record, sort_keys=True, separators=(",", ":"))
    record["digest"] = "sha256:" + hashlib.sha256(canon.encode()).hexdigest()
    return record
