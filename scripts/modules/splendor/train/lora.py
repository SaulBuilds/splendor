# SPDX-License-Identifier: GPL-2.0-or-later
"""A real low-rank adapter (LoRA) and its trainer — deterministic gradient descent.

A LoRA adapts a frozen base linear map ``W0`` (out×in) with a low-rank delta
``(alpha/r)·B·A`` (``A`` is r×in, ``B`` is out×r), so only ``r(in+out)`` parameters
are learned. This is the genuine article — real MSE gradient descent, loss that
actually decreases, a rank-r adapter that recovers a rank-r target — not a stub.
Standard init (``A`` small-random, ``B`` zero) means the untrained adapter is exactly
the base. Deterministic under a seed. Requires numpy (present in Blender + system).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass
class LoRAAdapter:
    W0: np.ndarray   # (out, in) — frozen base
    A: np.ndarray    # (r, in)
    B: np.ndarray    # (out, r)
    alpha: float

    @property
    def rank(self) -> int:
        return self.A.shape[0]

    @property
    def scaling(self) -> float:
        return self.alpha / self.rank

    def effective_weight(self) -> np.ndarray:
        return self.W0 + self.scaling * (self.B @ self.A)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """X (N, in) → (N, out)."""
        return np.asarray(X, dtype=np.float64) @ self.effective_weight().T

    def to_bytes(self) -> bytes:
        """Deterministic serialization of the learned delta (for content-addressing)."""
        head = f"lora:r={self.rank}:alpha={self.alpha}:shape={self.A.shape}x{self.B.shape}".encode()
        return head + self.A.astype("<f8").tobytes() + self.B.astype("<f8").tobytes()

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(self.to_bytes()).hexdigest()


def mse(pred: np.ndarray, Y: np.ndarray) -> float:
    return float(np.mean((pred - Y) ** 2))


def train_lora(X, Y, rank: int = 2, epochs: int = 300, lr: float = 0.5,
               seed: int = 0, alpha: float = 1.0, W0=None):
    """Fit a LoRA delta to map X (N, in) → Y (N, out) by full-batch MSE gradient descent.

    Returns ``(adapter, history)`` where history is the per-epoch loss. Full-batch and
    seeded → deterministic. ``W0`` defaults to zeros (adapt from scratch); pass a frozen
    base to adapt on top of it.
    """
    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    n, in_dim = X.shape
    out_dim = Y.shape[1]
    rng = np.random.default_rng(seed)
    W0 = np.zeros((out_dim, in_dim)) if W0 is None else np.asarray(W0, dtype=np.float64)
    A = rng.normal(0.0, 0.01, size=(rank, in_dim))
    B = np.zeros((out_dim, rank))
    s = alpha / rank
    m = float(Y.size)  # elements, for a mean-squared loss
    history = []
    for _ in range(epochs):
        w_eff = W0 + s * (B @ A)
        pred = X @ w_eff.T
        err = pred - Y
        history.append(float(np.mean(err ** 2)))
        d_pred = (2.0 / m) * err            # (n, out)
        d_weff = d_pred.T @ X               # (out, in)
        d_A = s * (B.T @ d_weff)            # (r, in)
        d_B = s * (d_weff @ A.T)            # (out, r)
        A -= lr * d_A
        B -= lr * d_B
    adapter = LoRAAdapter(W0=W0, A=A, B=B, alpha=alpha)
    history.append(mse(adapter.predict(X), Y))
    return adapter, history
