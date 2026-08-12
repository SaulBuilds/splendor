# SPDX-License-Identifier: GPL-2.0-or-later
"""A small geometry model (SPL-S3) — a PCA morphable shape basis over meshes.

Given several meshes *in correspondence* (same topology → equal-length flattened vertex
vectors), this fits a mean shape + top-k principal directions: a compact "shape model"
that reconstructs and interpolates variants (a blendshape/morphable basis — exactly what
retro character/prop variation wants). Real linear algebra (numpy SVD), deterministic,
verifiable: reconstruction error falls as k grows and hits ~0 at full rank. The model is
content-addressed so it can be pinned/attested like any Splendor artifact.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np


@dataclass
class ShapeModel:
    mean: np.ndarray          # (D,)
    components: np.ndarray    # (k, D) — orthonormal principal directions
    singular_values: np.ndarray  # (k,)

    @property
    def k(self) -> int:
        return self.components.shape[0]

    @property
    def dim(self) -> int:
        return self.mean.shape[0]

    def project(self, mesh) -> np.ndarray:
        """A mesh (flat vertex vector) → its k shape coefficients."""
        return (np.asarray(mesh, dtype=np.float64) - self.mean) @ self.components.T

    def reconstruct(self, coords) -> np.ndarray:
        """Shape coefficients → a mesh (flat vertex vector)."""
        return self.mean + np.asarray(coords, dtype=np.float64) @ self.components

    def digest(self) -> str:
        h = hashlib.sha256()
        h.update(self.mean.astype("<f8").tobytes())
        h.update(self.components.astype("<f8").tobytes())
        return "sha256:" + h.hexdigest()


def fit_shape_basis(meshes, k: int = 4):
    """Fit a mean + top-k PCA basis over `meshes` (equal-length flat vertex vectors).

    Returns ``(ShapeModel, info)`` where info has n, dim, k, and variance_explained.
    Deterministic (SVD). Raises ValueError on <2 meshes or ragged lengths.
    """
    if len(meshes) < 2:
        raise ValueError("need at least 2 meshes to fit a shape basis")
    X = np.stack([np.asarray(m, dtype=np.float64).ravel() for m in meshes])
    if len({m.shape[0] for m in X}) != 1:
        raise ValueError("meshes must share topology (equal vertex counts)")
    mean = X.mean(axis=0)
    Xc = X - mean
    _u, s, vt = np.linalg.svd(Xc, full_matrices=False)
    k = max(1, min(int(k), vt.shape[0]))
    model = ShapeModel(mean=mean, components=vt[:k].copy(), singular_values=s[:k].copy())
    total = float((s ** 2).sum())
    explained = float((s[:k] ** 2).sum() / total) if total > 0 else 1.0
    return model, {"n": int(X.shape[0]), "dim": int(X.shape[1]), "k": k,
                   "variance_explained": explained}


def reconstruction_error(model: ShapeModel, meshes) -> float:
    """Mean per-mesh RMS reconstruction error under the basis (0 = perfect)."""
    errs = []
    for m in meshes:
        x = np.asarray(m, dtype=np.float64).ravel()
        rx = model.reconstruct(model.project(x))
        errs.append(float(np.sqrt(np.mean((x - rx) ** 2))))
    return float(np.mean(errs)) if errs else 0.0
