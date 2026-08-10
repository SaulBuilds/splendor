# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the LLM-LoRA modality delegates to a real trainer, in the product.

    blender --background --factory-startup --python tests/splendor/test_spl_s3_llm_lora_ui.py

Captures runs, then enqueues the `llm_lora` modality — which builds a prompt→params
dataset and delegates to the trainer process (a real peft finetune). Asserts the
operator reports a real adapter digest, or an honest status if no trainer/deps are
present. This checks the *wiring*; convergence is the pure test's job (few steps here).
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402
from splendor_harness import training  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    training.LIBRARY._entries.clear()
    os.environ["SPLENDOR_LORA_STEPS"] = "15"  # lean: this test is about wiring, not convergence
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        print("[1] llm_lora with no captured runs → honest, no fake adapter")
        scene.splendor_train_modality = 'llm_lora'
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        st0 = scene.splendor_train_jobs[-1].status
        check("capture" in st0, f"refuses without data ({st0})")

        print("[2] Capture runs → build the prompt→params dataset")
        for i in range(4):
            scene.splendor_prompt = f"flat facet potion {i}"
            scene.splendor_palette_size = 4
            scene.splendor_eval_tris = 120
            scene.splendor_train_modality = 'workflow_capture'
            bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        check(len(training.samples_from_library()) == 4, "4 runs captured")

        print("[3] llm_lora delegates to the trainer process (Blender's Python has no torch)")
        scene.splendor_train_modality = 'llm_lora'
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        st = scene.splendor_train_jobs[-1].status
        # The trainer runs under system python3 (not Blender's). Whether it has torch
        # decides the outcome — either a real adapter or an honest status. Both are correct.
        real = "trained" in st and scene.splendor_lora_digest.startswith("sha256:")
        honest = any(w in st for w in ("unavailable", "missing", "trainer", "configured"))
        check(real or honest, f"delegated: real adapter OR honest status, never a fake ({st[:60]}…)")
        if real:
            check(scene.splendor_lora_digest.startswith("sha256:"), "real delegated adapter is content-addressed")
    finally:
        os.environ.pop("SPLENDOR_LORA_STEPS", None)
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — llm_lora modality delegates to a real trainer (honest when absent)")
    sys.exit(0)


if __name__ == "__main__":
    main()
