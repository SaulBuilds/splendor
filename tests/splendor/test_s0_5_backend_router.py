# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.5 acceptance test — model-agnostic backend Router.

Pure Python (no bpy):  python3 tests/splendor/test_s0_5_backend_router.py

Exits non-zero on any failure. The key negative control (mock-forbidding):
offline + a cloud-only route yields an honest ``BackendUnavailable`` — never a
hang, never a fabricated completion (framework §2).
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.dirname(__file__))

from splendor.models import (  # noqa: E402
    BackendUnavailable, CompletionRequest, Message, Modality, OpenAICompatBackend,
    RoutePolicy, Router,
)
import _openai_compat_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def local_backend():
    _srv, port = _openai_compat_server.start(reply="PLAN: make a PS1 potion")
    return OpenAICompatBackend("local-fixture", f"http://127.0.0.1:{port}/v1",
                               "fixture-model", is_local=True)


# An unreachable "cloud" backend: port 1 is closed -> fast connection-refused,
# so offline detection is quick (not a hang).
def unreachable_cloud():
    return OpenAICompatBackend("cloud-x", "http://127.0.0.1:1/v1", "gpt", is_local=False)


def test_text_plan_routes_through_local():
    print("[1] A text plan runs through the Router → local OpenAI-compatible backend (real HTTP)")
    local = local_backend()
    r = Router([local])
    check(local.reachable(), "local backend reachable via real GET /v1/models")
    res = r.complete(CompletionRequest(messages=[Message("user", "plan a potion")]))
    check("PLAN" in res.text and res.backend == "local-fixture", "text plan routed + real completion returned")


def test_capability_contract():
    print("[2] Capability contract is declared, not hardcoded")
    local = local_backend()
    check(Modality.TEXT in local.capability.modalities, "declares TEXT modality")
    check(local.capability.is_local is True, "declares is_local=True")


def test_offline_cloud_only_is_honest_error():
    print("[3] NEG CONTROL: offline + cloud-only → honest BackendUnavailable (no hang, no fake result)")
    r = Router([local_backend(), unreachable_cloud()])
    try:
        r.complete(CompletionRequest(messages=[Message("user", "hi")]), policy=RoutePolicy.CLOUD_ONLY)
        check(False, "cloud-only with unreachable cloud should raise, not return")
    except BackendUnavailable as exc:
        check(True, f"raised BackendUnavailable honestly: {exc}")


def test_local_first_prefers_local():
    print("[4] local-first policy selects the reachable local backend over cloud")
    local = local_backend()
    r = Router([unreachable_cloud(), local])  # cloud registered first on purpose
    sel = r.select(policy=RoutePolicy.LOCAL_FIRST)
    check(sel is local, "local-first picks local even when cloud is registered first")


def test_works_offline():
    print("[5] Works offline: only local reachable → default route completes (D-2.4)")
    r = Router([local_backend(), unreachable_cloud()])
    res = r.complete(CompletionRequest(messages=[Message("user", "offline?")]))
    check(res.backend == "local-fixture", "offline-capable: default (local-first) route completes via local")


def test_no_backend_at_all_is_honest():
    print("[6] NEG CONTROL: no reachable backend at all → honest error, never fabricated text")
    r = Router([unreachable_cloud()], policy=RoutePolicy.LOCAL_FIRST)
    try:
        r.complete(CompletionRequest(messages=[Message("user", "x")]))
        check(False, "should raise when nothing is reachable")
    except BackendUnavailable:
        check(True, "raised BackendUnavailable (no fabricated completion)")


def main():
    for t in (test_text_plan_routes_through_local, test_capability_contract,
              test_offline_cloud_only_is_honest_error, test_local_first_prefers_local,
              test_works_offline, test_no_backend_at_all_is_honest):
        t()
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.5 model-agnostic backend Router verified (local-first, offline-capable)")
    sys.exit(0)


if __name__ == "__main__":
    main()
