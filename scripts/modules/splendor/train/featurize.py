# SPDX-License-Identifier: GPL-2.0-or-later
"""Deterministic featurization — a prompt/workflow → a fixed-length vector.

A hashed bag-of-tokens: tokens are lowercased alphanumeric runs, each hashed into a
fixed number of buckets, then the vector is L2-normalised. Pure + deterministic (a
fixed seed in the hash), so the same prompt always yields the same features — the
property the training + eval tests rely on. No external tokeniser, no bpy.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str):
    return _TOKEN.findall((text or "").lower())


def _bucket(token: str, dim: int) -> int:
    h = hashlib.blake2b(token.encode(), digest_size=8).digest()
    return int.from_bytes(h, "big") % dim


def featurize(text: str, dim: int = 32) -> np.ndarray:
    """Prompt → L2-normalised hashed bag-of-tokens vector of length `dim`."""
    v = np.zeros(dim, dtype=np.float64)
    for t in tokens(text):
        v[_bucket(t, dim)] += 1.0
    n = np.linalg.norm(v)
    return v / n if n > 0.0 else v


def featurize_batch(texts, dim: int = 32) -> np.ndarray:
    return np.stack([featurize(t, dim) for t in texts]) if texts else np.zeros((0, dim))
