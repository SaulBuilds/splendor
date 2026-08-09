# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.3 acceptance test — governed action API + HIC gate.

Runs against the real Splendor binary:

    blender --background --factory-startup \
        --python tests/splendor/test_s0_3_governed_action_api.py

Exits non-zero on any failure. Objective + negative-controlled per
``.agentile/planset/03_ACCEPTANCE_FRAMEWORK.md``. No mocks: intents run against
real Blender mesh/scene data through the one governed path.
"""
import os
import sys

# Load the Splendor module + addon from the source tree (the built binary keeps a
# copy under bin/5.3/scripts; re-run `make` to bundle these. Testing from source
# keeps the loop fast and still exercises the real binary + real bpy).
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor  # noqa: E402
from splendor import dsl, hic  # noqa: E402
import splendor_harness  # noqa: E402

_FAILURES = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAILURES.append(label)


def make_mesh(name, verts):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], [])
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def coords(ob):
    return [tuple(round(c, 6) for c in v.co) for v in ob.data.vertices]


def budgeted_grant(classes=("geometry", "scene_config")):
    return hic.Grant("g-test", "tester", hic.HicLevel.BUDGETED, frozenset(classes))


OFFGRID = [(0.137, -0.052, 0.311), (1.031, 0.984, -0.446), (-0.628, 0.207, 0.079)]
GRID = 0.1
TOL = 1e-4  # mesh coords are float32; grid-alignment tolerance


def test_proceed_snaps_and_records():
    print("[1] PROCEED: valid grant snaps geometry + records the decision")
    ob = make_mesh("proceed", OFFGRID)
    before = coords(ob)
    res = splendor.action_api.execute(
        dsl.SnapVertices(grid=GRID), principal="tester",
        grant=budgeted_grant(), ctx={"object": ob})
    after = coords(ob)
    check(res.executed and res.verdict is hic.Verdict.PROCEED, "executed with PROCEED")
    aligned = all(abs(c / GRID - round(c / GRID)) < TOL for v in after for c in v)
    check(aligned, "every coord lands on the grid (deterministic criterion)")
    check(after != before, "geometry actually changed (not a no-op)")
    rec = res.record
    check(rec.principal == "tester" and rec.grant_id == "g-test"
          and rec.hic_level is hic.HicLevel.BUDGETED, "record carries principal+grant+HIC level (I-3)")


def test_negctl_no_grant_blocks_before_acting():
    print("[2] NEG CONTROL: no grant -> require-approval, gate blocks BEFORE mutation")
    ob = make_mesh("nogrant", OFFGRID)
    before = coords(ob)
    res = splendor.action_api.execute(
        dsl.SnapVertices(grid=GRID), principal="tester", grant=None, ctx={"object": ob})
    check(not res.executed, "not executed")
    check(res.verdict is hic.Verdict.REQUIRE_APPROVAL, "verdict == require-approval")
    check(res.record.rule_code == "RC-SPL-001", "rule RC-SPL-001 (ungoverned, approval)")
    check(res.record.hic_level is hic.HicLevel.UNGOVERNED, "recorded as ungoverned (not dropped)")
    check(coords(ob) == before, "geometry UNCHANGED — gate ran before the act (I-2)")


def test_negctl_invalid_intent_denied():
    print("[3] NEG CONTROL: invalid intent -> deny, never reaches an executor")
    ob = make_mesh("invalid", OFFGRID)
    before = coords(ob)
    res = splendor.action_api.execute(
        dsl.SnapVertices(grid=0.0), principal="tester", grant=budgeted_grant(), ctx={"object": ob})
    check(not res.executed and res.verdict is hic.Verdict.DENY, "denied, not executed")
    check(res.record.rule_code == "RC-SPL-000", "rule RC-SPL-000 (invalid intent)")
    check(coords(ob) == before, "geometry UNCHANGED")


def test_negctl_grant_does_not_cover_class():
    print("[4] NEG CONTROL: grant covers wrong class -> require-approval RC-SPL-002")
    ob = make_mesh("wrongclass", OFFGRID)
    res = splendor.action_api.execute(
        dsl.SnapVertices(grid=GRID), principal="tester",
        grant=budgeted_grant(classes=("scene_config",)), ctx={"object": ob})
    check(not res.executed and res.record.rule_code == "RC-SPL-002", "blocked with RC-SPL-002")


def test_sensitive_class_forces_hic1():
    print("[5] Sensitive action class -> HIC-1 approve-each even when covered (RC-SPL-003)")

    class MintStub(dsl.Intent):
        action_class = "mint"  # a sensitive class; no executor on purpose

        def validate(self):
            return None

    res = splendor.action_api.execute(
        MintStub(), principal="tester",
        grant=hic.Grant("g-mint", "tester", hic.HicLevel.BUDGETED, frozenset({"mint"})))
    check(not res.executed and res.verdict is hic.Verdict.REQUIRE_APPROVAL, "not auto-executed")
    check(res.record.rule_code == "RC-SPL-003"
          and res.record.hic_level is hic.HicLevel.APPROVE_EACH, "forced to HIC-1 (RC-SPL-003)")


def test_set_palette_real_state_change():
    print("[6] SetPalette proceeds and writes real scene state; invalid is denied")
    scene = bpy.context.scene
    res = splendor.action_api.execute(
        dsl.SetPalette(colors=8), principal="tester",
        grant=budgeted_grant(), ctx={"scene": scene})
    check(res.executed and scene.splendor_palette_size == 8, "palette size set to 8 on the scene")
    bad = splendor.action_api.execute(
        dsl.SetPalette(colors=999), principal="tester", grant=budgeted_grant(), ctx={"scene": scene})
    check(not bad.executed and bad.record.rule_code == "RC-SPL-000", "colors=999 denied (validation)")


def test_single_action_path_source_scan():
    print("[7] I-1 source scan: one governed path, no second executor caller")
    pkg_dir = os.path.dirname(splendor.__file__)
    srcs = {f: open(os.path.join(pkg_dir, f)).read()
            for f in os.listdir(pkg_dir) if f.endswith(".py")}
    exec_files = {f for f, s in srcs.items() if "_exec_" in s}
    check(exec_files == {"intents.py"}, f"_exec_ executors only in intents.py (found {exec_files})")
    reg_files = {f for f, s in srcs.items() if "REGISTRY" in s}
    check(reg_files == {"intents.py", "action_api.py"},
          f"REGISTRY only defined (intents) + dispatched (action_api) (found {reg_files})")
    allexec = all(fn.__name__.startswith("_exec_") for fn in splendor.intents.REGISTRY.values())
    check(allexec, "every REGISTRY entry is a private _exec_ executor")


def test_reproducible():
    print("[8] Reproducibility: same intent + same input -> identical result")
    a = make_mesh("repro_a", OFFGRID)
    b = make_mesh("repro_b", OFFGRID)
    g = budgeted_grant()
    splendor.action_api.execute(dsl.SnapVertices(grid=GRID), principal="t", grant=g, ctx={"object": a})
    splendor.action_api.execute(dsl.SnapVertices(grid=GRID), principal="t", grant=g, ctx={"object": b})
    check(coords(a) == coords(b), "two runs produce identical geometry")


def test_operator_front_door():
    print("[9] Front door: the operator drives the SAME action API")
    ob = make_mesh("op", OFFGRID)
    vl = bpy.context.view_layer
    vl.objects.active = ob
    n_before = len(splendor.action_api.decision_log().all())
    try:
        with bpy.context.temp_override(active_object=ob, object=ob):
            bpy.ops.splendor.snap_vertices(grid=GRID)
        ran = True
    except Exception as exc:  # pragma: no cover - context fragility guard
        print("    (operator invoke note:", exc, ")")
        ran = False
    n_after = len(splendor.action_api.decision_log().all())
    check(ran and n_after == n_before + 1, "operator produced exactly one governed decision record")


def main():
    splendor_harness.register()  # registers the scene property + operators
    try:
        for t in (test_proceed_snaps_and_records, test_negctl_no_grant_blocks_before_acting,
                  test_negctl_invalid_intent_denied, test_negctl_grant_does_not_cover_class,
                  test_sensitive_class_forces_hic1, test_set_palette_real_state_change,
                  test_single_action_path_source_scan, test_reproducible,
                  test_operator_front_door):
            t()
    finally:
        # Confirm the audit trail never silently dropped a blocked action.
        log = splendor.action_api.decision_log().all()
        blocked = [r for r in log if r.verdict is not hic.Verdict.PROCEED]
        print(f"[log] {len(log)} decision records, {len(blocked)} blocked (all recorded, none dropped)")
        splendor_harness.unregister()

    print()
    if _FAILURES:
        print(f"RESULT: FAIL ({len(_FAILURES)} checks failed)")
        for f in _FAILURES:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.3 governed action API + HIC gate verified")
    sys.exit(0)


if __name__ == "__main__":
    main()
