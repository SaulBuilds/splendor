# SPDX-License-Identifier: GPL-2.0-or-later
"""Evaluation criteria — the scorers the Eval SDK runs over a subject.

A *subject* is a plain dict of measurements (tri count, palette colors, a
signature vector, samples). Keeping the SDK dict-based makes it standalone and
bpy-independent: a Blender-side measurer produces the dict; the SDK scores it, so
the same criteria run in CI, headless, or against pinned provenance. Deterministic
criteria feed the reproducibility guarantee; the seeded one shows the seed is
real. Rounding to a fixed precision keeps serialization bit-identical (P4/D-3.3).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

_PREC = 9  # decimal places — stable, bit-identical serialization


def _r(x: float) -> float:
    return round(float(x), _PREC)


@dataclass(frozen=True)
class CriterionResult:
    name: str
    value: float      # 0..1 (1 = perfect)
    passed: bool
    threshold: float
    detail: str = ""


class Criterion:
    name: str
    threshold: float

    def evaluate(self, subject: dict, seed: int = 0) -> CriterionResult:
        raise NotImplementedError


class TriBudget(Criterion):
    """Pass if the mesh is within a triangle budget (retro authenticity)."""

    def __init__(self, max_tris: int, key: str = "tri_count", name: str = "tri_budget"):
        self.max_tris = int(max_tris)
        self.key = key
        self.name = name
        self.threshold = 1.0

    def evaluate(self, subject, seed=0):
        tris = int(subject[self.key])
        passed = tris <= self.max_tris
        value = 1.0 if passed else self.max_tris / tris
        return CriterionResult(self.name, _r(value), passed, 1.0,
                               f"{tris} tris vs budget {self.max_tris}")


class PaletteAdherence(Criterion):
    """Pass if the color count is within the retro palette cap."""

    def __init__(self, max_colors: int, key: str = "palette_colors", name: str = "palette_adherence"):
        self.max_colors = int(max_colors)
        self.key = key
        self.name = name
        self.threshold = 1.0

    def evaluate(self, subject, seed=0):
        colors = int(subject[self.key])
        passed = colors <= self.max_colors
        value = 1.0 if passed else self.max_colors / colors
        return CriterionResult(self.name, _r(value), passed, 1.0,
                               f"{colors} colors vs cap {self.max_colors}")


class ReferenceSimilarity(Criterion):
    """Cosine similarity of a subject signature vector to a reference.

    Corrupting the reference drops the score below threshold — the negative
    control that proves the scorer discriminates (framework §5, anti-'check that
    cannot fail').
    """

    def __init__(self, reference, key: str = "signature", threshold: float = 0.9,
                 name: str = "reference_similarity"):
        self.reference = tuple(float(x) for x in reference)
        self.key = key
        self.threshold = float(threshold)
        self.name = name

    def evaluate(self, subject, seed=0):
        vec = tuple(float(x) for x in subject[self.key])
        sim = _cosine(vec, self.reference)
        value = max(0.0, min(1.0, sim))
        passed = value >= self.threshold
        return CriterionResult(self.name, _r(value), passed, self.threshold,
                               f"cosine={_r(sim)} vs threshold {self.threshold}")


class SeededSampleMean(Criterion):
    """Pass if a *seeded* random subsample's mean is within a threshold.

    Present so the harness seed is genuinely load-bearing: same seed → identical
    sample (bit-identical record); different seed → (generally) different sample.
    """

    def __init__(self, threshold: float, key: str = "samples", k: int = 8,
                 name: str = "seeded_sample_mean"):
        self.threshold = float(threshold)
        self.key = key
        self.k = int(k)
        self.name = name

    def evaluate(self, subject, seed=0):
        data = list(subject[self.key])
        rng = random.Random(seed)
        sample = rng.sample(data, min(self.k, len(data)))
        mean = sum(sample) / len(sample)
        passed = mean <= self.threshold
        # Continuous score in (0, 1], monotonically decreasing in the sampled
        # mean — so the *value* (hashed) depends on the seed, making the seed
        # genuinely load-bearing, not just cosmetic.
        value = 1.0 / (1.0 + max(0.0, mean))
        return CriterionResult(self.name, _r(value), passed, self.threshold,
                               f"sample_mean={_r(mean)} (seed={seed}) vs {self.threshold}")


def _cosine(a, b) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(x * x for x in a[:n]))
    nb = math.sqrt(sum(x * x for x in b[:n]))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
