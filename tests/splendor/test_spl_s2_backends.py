# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-S2 Model/Backend Manager test — configure backends, check reachability,
route by policy, and feed the Plan step.

    blender --background --factory-startup --python tests/splendor/test_spl_s2_backends.py

Exits non-zero on any failure. Uses a reachable local HTTP fixture + an
unreachable cloud (127.0.0.1:1) — no external network.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))
sys.path.insert(0, os.path.dirname(__file__))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402
from splendor_harness import flow  # noqa: E402
from splendor.models import BackendUnavailable, CompletionRequest, Message  # noqa: E402
import _openai_compat_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def add(scene, name, url, is_local):
    b = scene.splendor_backends.add()
    b.name, b.base_url, b.model, b.is_local, b.status = name, url, "m", is_local, "unknown"
    return b


def main():
    os.environ.pop("SPLENDOR_MODEL_URL", None)
    splendor_harness.register()
    scene = bpy.context.scene
    try:
        check(hasattr(bpy.types, "SPLENDOR_PT_backends"), "Model/Backend Manager panel registered")
        check(len(scene.splendor_backends) == 0, "starts with no backends")

        print("[1] Add-preset operator works; then reset to a controlled set")
        bpy.ops.splendor.backend_add('EXEC_DEFAULT', preset='OLLAMA')
        check(scene.splendor_backends[0].name == "Ollama" and scene.splendor_backends[0].is_local,
              "Ollama preset added (local)")
        scene.splendor_backends.clear()   # reset — don't depend on ambient local servers
        _srv, port = _openai_compat_server.start(reply="PLAN: box, snap, palette 16")
        add(scene, "fixture", f"http://127.0.0.1:{port}/v1", True)      # reachable local
        add(scene, "cloud-dead", "http://127.0.0.1:1/v1", False)        # unreachable cloud
        check(len(scene.splendor_backends) == 2, "two controlled backends configured")

        print("[2] Reachability check updates each backend's status")
        bpy.ops.splendor.backend_check('EXEC_DEFAULT')
        st = {b.name: b.status for b in scene.splendor_backends}
        check(st["fixture"] == "reachable", "fixture → reachable (real HTTP probe)")
        check(st["cloud-dead"] == "offline", "unreachable cloud → offline")
        check(all(v != "unknown" for v in st.values()), "no status left unknown")

        print("[3] Router from the manager: local-first selects the reachable local backend")
        scene.splendor_route_policy = 'LOCAL_FIRST'
        router = flow.build_router(scene)
        sel = router.select()
        check(sel is not None and sel.name == "fixture", "local-first → fixture")
        res = router.complete(CompletionRequest(messages=[Message("user", "hi")]))
        check("PLAN" in res.text, "router completes via the reachable backend")

        print("[4] Cloud-only policy with no reachable cloud → honest BackendUnavailable")
        scene.splendor_route_policy = 'CLOUD_ONLY'
        try:
            flow.build_router(scene).complete(CompletionRequest(messages=[Message("user", "x")]))
            check(False, "cloud-only should raise")
        except BackendUnavailable:
            check(True, "cloud-only + no reachable cloud → BackendUnavailable (honest)")

        print("[5] The Plan step drives the manager's Router")
        scene.splendor_route_policy = 'LOCAL_FIRST'
        scene.splendor_prompt = "a low-poly potion"
        bpy.ops.splendor.plan('EXEC_DEFAULT')
        check(scene.splendor_run_state == 'PLANNED' and scene.splendor_plan_backend == "fixture",
              "Plan used the manager's reachable backend")

        print("[6] Remove a backend")
        n = len(scene.splendor_backends)
        scene.splendor_backends_index = 0
        bpy.ops.splendor.backend_remove('EXEC_DEFAULT')
        check(len(scene.splendor_backends) == n - 1, "remove works")
    finally:
        splendor_harness.unregister()
        check(not hasattr(bpy.types, "SPLENDOR_PT_backends"), "clean unregister")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — SPL-S2 Model/Backend Manager verified (list, check, policy, feeds Plan)")
    sys.exit(0)


if __name__ == "__main__":
    main()
