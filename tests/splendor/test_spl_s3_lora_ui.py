# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the Workflow LoRA training operator, end-to-end in the product.

    blender --background --factory-startup --python tests/splendor/test_spl_s3_lora_ui.py

Captures several eval-scored runs (two prompt families with different palettes) via
the real capture operator, then runs the Train Workflow LoRA operator and checks it
trained a content-addressed adapter and reported an Eval-SDK-measured result — no
mock, the same loop the pure test verifies numerically.
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


def _capture(scene, prompt, palette, tris):
    scene.splendor_prompt = prompt
    scene.splendor_palette_size = palette
    scene.splendor_eval_tris = tris
    scene.splendor_train_modality = 'workflow_capture'
    bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')


def main():
    training.LIBRARY._entries.clear()
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        print("[1] Too few captured runs → the trainer refuses honestly")
        r = bpy.ops.splendor.train_lora('EXEC_DEFAULT')
        check(r == {'CANCELLED'}, "train refused with <4 captured runs (no fake adapter)")

        print("[2] Capture eval-scored runs (two prompt families, different palettes)")
        for i in range(5):
            _capture(scene, f"gradient dithered sunset {i}", 32, 400)
        for i in range(5):
            _capture(scene, f"flat facet minimal {i}", 4, 120)
        samples = training.samples_from_library()
        check(len(samples) == 10, f"10 runs captured into the library ({len(samples)})")

        print("[3] Train Workflow LoRA → a real, content-addressed adapter")
        r = bpy.ops.splendor.train_lora('EXEC_DEFAULT')
        check(r == {'FINISHED'}, "train operator finished")
        check(scene.splendor_lora_digest.startswith("sha256:"), "adapter is content-addressed (pinnable/attestable)")
        job = scene.splendor_train_jobs[-1]
        check(job.modality == "workflow_lora" and job.digest == scene.splendor_lora_digest,
              "job records the trained adapter")
        check("eval" in job.status and "loss" in job.status, f"job reports the Eval-SDK result ({job.status[:60]}…)")

        print("[4] Determinism — retraining the same library yields the same adapter")
        d1 = scene.splendor_lora_digest
        bpy.ops.splendor.train_lora('EXEC_DEFAULT')
        check(scene.splendor_lora_digest == d1, "same captured data → identical adapter digest")
    finally:
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — Workflow LoRA operator verified (capture → train → content-addressed adapter)")
    sys.exit(0)


if __name__ == "__main__":
    main()
