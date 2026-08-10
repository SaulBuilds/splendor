# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 Training Panel test — real workflow capture, honest weight modalities.

    blender --background --factory-startup --python tests/splendor/test_spl_s3_training.py

Exits non-zero on any failure. Workflow capture actually saves a content-hashed,
reusable workflow; weight-based modalities enqueue an honest job (trainer not
wired); DePIN/cloud compute reports availability truthfully.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402
from splendor_harness import training  # noqa: E402
from splendor import train as _train  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    for v in ("SPLENDOR_CLOUD_TRAINING", "SPLENDOR_DEPIN_COMPUTE"):
        os.environ.pop(v, None)
    splendor_harness.register()
    scene = bpy.context.scene
    n0 = len(training.LIBRARY)
    try:
        check(hasattr(bpy.types, "SPLENDOR_PT_training"), "Training panel registered")
        check(scene.splendor_train_modality == 'workflow_capture', "default modality = workflow_capture")

        print("[1] Workflow capture is REAL — saves a content-hashed reusable workflow")
        scene.splendor_prompt = "a low-poly PS1 potion"
        scene.splendor_palette_size = 16
        scene.splendor_train_modality = 'workflow_capture'
        scene.splendor_train_compute = 'local'
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        check(len(training.LIBRARY) == n0 + 1, "library grew by one captured workflow")
        job = scene.splendor_train_jobs[-1]
        check(job.status.startswith("captured ") and job.digest.startswith("sha256:"),
              "job captured with a content digest")

        print("[2] Capture is deterministic (same run → same digest)")
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        d1, d2 = scene.splendor_train_jobs[-2].digest, scene.splendor_train_jobs[-1].digest
        check(d1 == d2 and d1, "identical run → identical captured digest")

        print("[3] Weight modality (local) is HONEST — trainer not yet wired, not faked")
        scene.splendor_train_modality = 'diffusion_lora'
        scene.splendor_train_compute = 'local'
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        st = scene.splendor_train_jobs[-1].status
        check("trainer" in st and "not yet" in st, f"diffusion LoRA → honest 'trainer not yet wired' ({st})")

        print("[4] DePIN / cloud compute reports availability truthfully")
        scene.splendor_train_modality = 'geometry_model'
        scene.splendor_train_compute = 'depin'
        bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
        st = scene.splendor_train_jobs[-1].status
        check("unavailable" in st and "not configured" in st, f"DePIN unconfigured → honest unavailable ({st})")
        check(_train.compute_available("local", os.environ) is True, "local compute available")
        check(_train.compute_available("depin", os.environ) is False, "DePIN unavailable until configured")
        os.environ["SPLENDOR_DEPIN_COMPUTE"] = "1"
        check(_train.compute_available("depin", os.environ) is True, "DePIN available once configured")
        os.environ.pop("SPLENDOR_DEPIN_COMPUTE", None)

        print("[5] Clear the job queue")
        bpy.ops.splendor.train_clear('EXEC_DEFAULT')
        check(len(scene.splendor_train_jobs) == 0, "jobs cleared")
    finally:
        splendor_harness.unregister()
        check(not hasattr(bpy.types, "SPLENDOR_PT_training"), "clean unregister")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — SPL-S3 Training Panel verified (real capture, honest weights + compute)")
    sys.exit(0)


if __name__ == "__main__":
    main()
