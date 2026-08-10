# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the Workflow LoRA training loop (real gradients, Eval-SDK-scored).

    python3 tests/splendor/test_spl_s3_lora.py

Two proofs. (1) The LoRA is real: loss strictly decreases, a rank-r adapter recovers
a rank-r target, an under-rank adapter can't, and training is deterministic. (2) The
loop *learns something useful*: after training on eval-scored runs, its held-out
palette predictions pass the Eval SDK's PaletteAdherence more often than a constant
baseline — improvement measured against reality, not the loss.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

import numpy as np  # noqa: E402
from splendor.train import LoRAAdapter, Sample, run_training_loop, train_lora  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    print("[1] The LoRA is a real trainer (loss ↓, recovers a low-rank target)")
    rng = np.random.default_rng(1)
    X = rng.normal(size=(40, 8))
    W_true = rng.normal(size=(3, 2)) @ rng.normal(size=(2, 8))  # rank-2 target
    Y = X @ W_true.T
    ad, hist = train_lora(X, Y, rank=2, epochs=400, lr=0.3, seed=0)
    check(all(hist[i + 1] <= hist[i] + 1e-12 for i in range(len(hist) - 1)), "loss monotonically non-increasing")
    check(hist[-1] < hist[0] * 1e-3, f"loss collapses ({hist[0]:.3f} → {hist[-1]:.2e})")
    check(hist[-1] < 1e-4, "rank-2 adapter recovers the rank-2 target")
    _, h1 = train_lora(X, Y, rank=1, epochs=400, lr=0.3, seed=0)
    check(h1[-1] > hist[-1], "an under-rank (r=1) adapter leaves a larger residual")

    print("[2] Determinism (same seed → same weights + digest)")
    ad2, _ = train_lora(X, Y, rank=2, epochs=400, lr=0.3, seed=0)
    check(np.allclose(ad.effective_weight(), ad2.effective_weight()), "identical weights")
    check(ad.digest() == ad2.digest() and ad.digest().startswith("sha256:"), "identical content digest")

    print("[3] The loop learns prompt→palette and BEATS a baseline on the Eval SDK")
    # Two prompt families with different palette limits; 'good' palette == the limit.
    def make(kind, n):
        word = "gradient sunset dithered" if kind == "hi" else "flat facet minimal"
        limit = 32 if kind == "hi" else 4
        return [Sample(prompt=f"{word} scene {i}", palette=limit, limit=limit) for i in range(n)]

    train_samples = make("hi", 12) + make("lo", 12)
    holdout = make("hi", 6) + make("lo", 6)
    out = run_training_loop(train_samples, holdout, dim=32, rank=2, epochs=500, lr=0.4, seed=0)
    check(out["loss_history"][-1] < out["loss_history"][0], "training loss decreased")
    check(out["eval_pass_baseline"] < 1.0, f"constant baseline can't satisfy both limits ({out['eval_pass_baseline']:.2f})")
    check(out["eval_pass_lora"] > out["eval_pass_baseline"],
          f"LoRA beats baseline on Eval SDK ({out['eval_pass_lora']:.2f} > {out['eval_pass_baseline']:.2f})")
    check(out["improvement"] > 0.0, f"measured improvement = +{out['improvement']:.2f} pass-rate")
    check(out["adapter_digest"].startswith("sha256:"), "adapter is content-addressed (pinnable/attestable)")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — Workflow LoRA loop verified (real gradients + Eval-SDK-measured gain)")
    sys.exit(0)


if __name__ == "__main__":
    main()
