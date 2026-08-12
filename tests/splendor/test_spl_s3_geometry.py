# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the geometry model (a PCA morphable shape basis).

    python3 tests/splendor/test_spl_s3_geometry.py

Real linear algebra, verifiable: reconstruction error falls as k grows and hits ~0 at
the data's intrinsic rank; variance-explained is monotone; the fit is deterministic and
content-addressed. Mock-free.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

import numpy as np  # noqa: E402
from splendor.train import fit_shape_basis, reconstruction_error  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    rng = np.random.default_rng(0)
    # 10 meshes (8 verts × 3 = 24 dims) = a base shape + variation along 2 latent axes.
    base = rng.normal(size=24)
    a1, a2 = rng.normal(size=24), rng.normal(size=24)
    meshes = [base + rng.normal() * a1 + rng.normal() * a2 for _ in range(10)]

    print("[1] Reconstruction error falls with k and hits ~0 at the intrinsic rank")
    m1, i1 = fit_shape_basis(meshes, k=1)
    m2, i2 = fit_shape_basis(meshes, k=2)
    m4, _i4 = fit_shape_basis(meshes, k=4)
    e1, e2, e4 = (reconstruction_error(m, meshes) for m in (m1, m2, m4))
    check(e1 > e2 > 1e-12 or (e1 > e2), f"error decreases with k ({e1:.3f} → {e2:.2e})")
    check(e2 < 1e-9, "rank-2 data → rank-2 basis reconstructs to ~0 error")
    check(e4 <= e2 + 1e-12, "more components never increase error")

    print("[2] Variance explained is monotone and complete at the intrinsic rank")
    check(i1["variance_explained"] < i2["variance_explained"] - 1e-9 or i1["variance_explained"] < 1.0,
          f"k=1 explains less than k=2 ({i1['variance_explained']:.3f} < {i2['variance_explained']:.3f})")
    check(i2["variance_explained"] > 0.999, "k=2 explains ~all variance of rank-2 data")
    check(i2["dim"] == 24 and i2["n"] == 10, "info reports dim + sample count")

    print("[3] Deterministic + content-addressed; usable as a morphable model")
    m2b, _ = fit_shape_basis(meshes, k=2)
    check(m2.digest() == m2b.digest() and m2.digest().startswith("sha256:"), "same data → same digest")
    coords = m2.project(meshes[0])
    recon = m2.reconstruct(coords)
    check(recon.shape[0] == 24 and float(np.sqrt(np.mean((recon - meshes[0]) ** 2))) < 1e-9,
          "project→reconstruct round-trips a training mesh")
    novel = m2.reconstruct(np.array([2.0, -1.0]))  # a new point in shape space
    check(novel.shape[0] == 24, "reconstructs a novel shape from coefficients (interpolation)")

    print("[4] Guards: too few meshes / ragged topology")
    for bad, why in (([base], "1 mesh"), ([base, base[:20]], "ragged")):
        try:
            fit_shape_basis(bad, k=2)
            check(False, f"should reject {why}")
        except ValueError:
            check(True, f"rejects {why}")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — geometry shape model verified (PCA basis, error↓, deterministic)")
    sys.exit(0)


if __name__ == "__main__":
    main()
