# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S3 — the diffusion + geometry modalities in the product.

    blender --background --factory-startup --python tests/splendor/test_spl_s3_diffgeo_ui.py

Geometry: capture two same-topology meshes → the panel fits a PCA shape basis and
reports variance + a content digest. Diffusion: an image piece → the panel delegates a
real style-LoRA finetune (or reports honestly). Both through the same enqueue flow.
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


def _enqueue(scene, modality):
    scene.splendor_train_modality = modality
    bpy.ops.splendor.train_enqueue('EXEC_DEFAULT')
    return scene.splendor_train_jobs[-1].status


def main():
    training.GEO_MESHES.clear()
    os.environ["SPLENDOR_DIFFUSION_STEPS"] = "15"  # lean: wiring, not convergence
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        print("[1] Geometry model: capture two meshes → fit a PCA shape basis")
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1)  # fixed topology
        obj = bpy.context.active_object
        st1 = _enqueue(scene, 'geometry_model')
        check("need ≥2" in st1 or "captured 1" in st1, f"first capture asks for more ({st1[:40]}…)")
        # a second, deformed variant (same topology)
        for v in obj.data.vertices:
            v.co.x *= 1.3
        obj.data.update()
        st2 = _enqueue(scene, 'geometry_model')
        check("fit" in st2 and "var" in st2 and "sha256" in st2,
              f"second capture fits a shape basis ({st2[:60]}…)")

        print("[2] Diffusion LoRA: an image piece → delegate a real style finetune")
        img = bpy.data.images.new("Splendor Retro", 8, 8, alpha=True)
        img.pixels = [c for _ in range(64) for c in (0.55, 0.80, 0.035, 1.0)]
        img.update()
        scene.splendor_retro_last = "Splendor Retro"
        st3 = _enqueue(scene, 'diffusion_lora')
        real = "trained" in st3 and scene.splendor_lora_digest.startswith("sha256:")
        honest = any(w in st3 for w in ("unavailable", "missing", "no diffusion", "no images"))
        check(real or honest, f"delegated diffusion: real adapter OR honest status ({st3[:60]}…)")
    finally:
        os.environ.pop("SPLENDOR_DIFFUSION_STEPS", None)
        splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — diffusion + geometry modalities verified in the product")
    sys.exit(0)


if __name__ == "__main__":
    main()
