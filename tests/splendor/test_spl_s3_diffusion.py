# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the delegated diffusion-LoRA trainer (a real DDPM + peft finetune).

    python3 tests/splendor/test_spl_s3_diffusion.py

Trains a style LoRA on toy "renders" through the subprocess protocol: only the peft
adapters train (the DDPM base is frozen), the denoising loss falls, and a real
adapter + digest come back. Skips honestly when torch/peft are absent; the no-trainer
path is always checked.
"""
import importlib.util
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.train import TrainerUnavailable, resolve_trainer  # noqa: E402

_FAIL = []
_HAVE_TORCH = all(importlib.util.find_spec(m) for m in ("torch", "peft"))


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def _toy_renders():
    # 8×8 grayscale "renders" with distinct looks — the style to learn.
    return [
        [(x % 8) / 7 for x in range(64)],
        [1 - (x % 8) / 7 for x in range(64)],
        [(x // 8) / 7 for x in range(64)],
        [((x % 8) ^ (x // 8)) / 7 for x in range(64)],
    ]


def main():
    print("[1] A diffusion trainer resolves; a bad command fails honestly")
    trainer = resolve_trainer({}, kind="diffusion")
    check(trainer is not None and "diffusion" in trainer.command[-1], "resolve_trainer(kind='diffusion')")
    bad = resolve_trainer({"SPLENDOR_DIFFUSION_TRAINER": "/nonexistent/diff_trainer"}, kind="diffusion")
    try:
        bad.train_diffusion(_toy_renders())
        check(False, "bad trainer should raise")
    except TrainerUnavailable:
        check(True, "missing trainer → TrainerUnavailable (no fake adapter)")

    if not _HAVE_TORCH:
        print("[2] SKIP — torch/peft absent; real-train checks need them")
        return _finish()

    print("[2] capabilities + a real DDPM LoRA finetune (LoRA-only, loss ↓, adapter saved)")
    caps = trainer.capabilities()
    check(caps.get("ok") and "peft" in caps, f"capabilities → torch {caps.get('torch')} · peft {caps.get('peft')}")
    res = trainer.train_diffusion(_toy_renders(), rank=8, steps=80, lr=8e-3, seed=0)
    check(res["ok"], "train succeeded")
    check(0 < res["trainable_params"] < res["total_params"],
          f"only the LoRA trains ({res['trainable_params']}/{res['total_params']})")
    check(res["final_loss"] < res["initial_loss"],
          f"denoising loss fell ({res['initial_loss']:.3f} → {res['final_loss']:.3f})")
    check(os.path.exists(res["adapter_path"]) and res["adapter_digest"].startswith("sha256:"),
          "a real adapter + content digest were produced")

    print("[3] Determinism — same seed/data → same adapter digest")
    res2 = trainer.train_diffusion(_toy_renders(), rank=8, steps=80, lr=8e-3, seed=0)
    check(res2["adapter_digest"] == res["adapter_digest"], "identical digest on a repeat run")

    return _finish()


def _finish():
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — delegated diffusion-LoRA trainer verified (real DDPM finetune)")
    sys.exit(0)


if __name__ == "__main__":
    main()
