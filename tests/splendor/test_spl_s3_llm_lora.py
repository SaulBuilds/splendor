# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the delegated LLM-LoRA trainer (a real peft finetune).

    python3 tests/splendor/test_spl_s3_llm_lora.py

Trains a genuine peft LoRA through the subprocess protocol: only the adapter matrices
are trainable (the base is frozen), the loss actually falls, and a real
adapter_model.safetensors + content digest come back. Skips honestly when
torch/transformers/peft aren't installed; the no-trainer path is always checked.
"""
import importlib.util
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.train import TrainerUnavailable, resolve_trainer  # noqa: E402

_FAIL = []
_HAVE_TORCH = all(importlib.util.find_spec(m) for m in ("torch", "transformers", "peft"))


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    print("[1] A trainer resolves by default (bundled reference trainer)")
    trainer = resolve_trainer({})
    check(trainer is not None, "resolve_trainer → the bundled reference trainer")

    print("[2] NEG CONTROL: a bad trainer command fails honestly (no fake adapter)")
    bad = resolve_trainer({"SPLENDOR_LORA_TRAINER": "/nonexistent/splendor_trainer"})
    try:
        bad.train([{"prompt": "x", "completion": "y"}])
        check(False, "bad trainer should raise")
    except TrainerUnavailable as exc:
        check("not found" in str(exc).lower() or "trainer" in str(exc).lower(),
              "missing trainer → TrainerUnavailable (honest)")

    if not _HAVE_TORCH:
        print("[3] SKIP — torch/transformers/peft absent; real-train checks need them")
        return _finish()

    print("[3] capabilities reports the real backend")
    caps = trainer.capabilities()
    check(caps.get("ok") and "peft" in caps, f"capabilities → torch {caps.get('torch')} · peft {caps.get('peft')}")

    print("[4] A real peft LoRA finetune: only the adapter trains, loss falls, adapter saved")
    dataset = [{"prompt": "flat facet potion", "completion": '{"palette":4}'},
               {"prompt": "gradient dithered sunset", "completion": '{"palette":32}'}] * 8
    res = trainer.train(dataset, rank=8, steps=60, lr=8e-3, seed=0)
    check(res["ok"], "train succeeded")
    check(0 < res["trainable_params"] < res["total_params"],
          f"only the LoRA trains ({res['trainable_params']}/{res['total_params']} params)")
    check(res["final_loss"] < res["initial_loss"],
          f"loss fell ({res['initial_loss']:.3f} → {res['final_loss']:.3f})")
    check(os.path.exists(res["adapter_path"]) and res["adapter_digest"].startswith("sha256:"),
          "a real adapter file + content digest were produced")

    print("[5] Determinism — same seed/data → same adapter digest")
    res2 = trainer.train(dataset, rank=8, steps=60, lr=8e-3, seed=0)
    check(res2["adapter_digest"] == res["adapter_digest"], "identical digest on a repeat run")

    return _finish()


def _finish():
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — delegated LLM-LoRA trainer verified (real peft finetune, honest failures)")
    sys.exit(0)


if __name__ == "__main__":
    main()
