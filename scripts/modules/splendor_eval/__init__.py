# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor Eval SDK (P4) — the proof-critical measurement backbone.

Standalone and bpy-independent: import it in Blender, in CI, or in a service to
score outputs against criteria and produce reproducible, hashable records. This
is the differentiator (D-3.3) and the eventual routing signal for the Router
(D-2.4). Scorers here are the deterministic-criteria kind; VLM-as-judge,
HIC-gated human ratings, and the benchmark leaderboard are later P4 work that
plugs into this same harness.
"""
from __future__ import annotations

from . import criteria, harness
from .criteria import (
    Criterion, CriterionResult, PaletteAdherence, ReferenceSimilarity,
    SeededSampleMean, TriBudget,
)
from .harness import EvalHarness, EvalRecord

__all__ = [
    "criteria", "harness",
    "Criterion", "CriterionResult", "PaletteAdherence", "ReferenceSimilarity",
    "SeededSampleMean", "TriBudget", "EvalHarness", "EvalRecord",
]
__version__ = (0, 0, 1)
