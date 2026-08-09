# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.6 acceptance test — the Eval SDK (standalone, importable).

Pure Python (no bpy):  python3 tests/splendor/test_s0_6_eval_sdk.py

Exits non-zero on any failure. Acceptance (framework §5, D-3.3):
  - scores a subject with deterministic criteria (tri/palette);
  - records reproducibly under a seed (fixed-seed rerun is bit-identical);
  - NEG CONTROL: corrupting the reference/criterion drops the score below
    threshold (the scorer discriminates — no 'check that cannot fail');
  - the seed is genuinely load-bearing (different seed → different digest);
  - the record is content-hashed → pinnable as provenance.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor_eval import (  # noqa: E402
    EvalHarness, PaletteAdherence, ReferenceSimilarity, SeededSampleMean, TriBudget,
)

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


REF = [1.0, 2.0, 3.0, 4.0]
GOOD = {
    "tri_count": 480,
    "palette_colors": 16,
    "signature": [1.0, 2.0, 3.0, 4.0],   # same direction as REF → cosine 1.0
    "samples": [float(i) for i in range(20)],
}


def make_harness(reference=REF):
    return EvalHarness([
        TriBudget(500),
        PaletteAdherence(16),
        ReferenceSimilarity(reference, threshold=0.9),
        SeededSampleMean(threshold=16.0, k=8),   # max possible 8-mean < 16 → always passes
    ])


def test_scores_good_subject():
    print("[1] Scores a good subject with deterministic criteria")
    rec = make_harness().evaluate(GOOD, "asset-good", seed=42)
    check(rec.passed_all, "all criteria pass on a within-budget subject")
    by = {r.name: r for r in rec.results}
    check(by["tri_budget"].passed and by["tri_budget"].value == 1.0, "tri_budget within budget")
    check(by["palette_adherence"].passed, "palette within cap")
    check(by["reference_similarity"].value >= 0.9, "signature matches reference (cosine ≥ 0.9)")
    check(rec.digest.startswith("sha256:"), "record carries a content digest (pinnable provenance)")


def test_reproducible_under_seed():
    print("[2] Fixed-seed rerun is bit-identical")
    h = make_harness()
    a = h.evaluate(GOOD, "asset-good", seed=42)
    b = h.evaluate(GOOD, "asset-good", seed=42)
    check(h.canonical(a) == h.canonical(b), "canonical serialization is byte-identical")
    check(a.digest == b.digest, "digest identical across reruns (reproducible)")


def test_seed_is_load_bearing():
    print("[3] The seed genuinely affects the record")
    h = make_harness()
    digests = {h.evaluate(GOOD, "asset-good", seed=s).digest for s in range(1, 8)}
    check(len(digests) > 1, f"different seeds produce different digests ({len(digests)} distinct)")


def test_negctl_corrupt_reference():
    print("[4] NEG CONTROL: corrupting the reference drops the score below threshold")
    corrupted = [-x for x in REF]  # opposite direction → cosine → clamped 0
    rec = make_harness(reference=corrupted).evaluate(GOOD, "asset-good", seed=42)
    sim = {r.name: r for r in rec.results}["reference_similarity"]
    check(not sim.passed and sim.value < 0.9, f"similarity fails (value={sim.value})")
    check(not rec.passed_all, "passed_all flips to False when a criterion fails")


def test_negctl_over_budget():
    print("[5] NEG CONTROL: over-budget mesh/palette is detected by the deterministic scorer")
    bad = dict(GOOD, tri_count=900, palette_colors=17)
    rec = make_harness().evaluate(bad, "asset-bad", seed=42)
    by = {r.name: r for r in rec.results}
    check(not by["tri_budget"].passed and by["tri_budget"].value < 1.0, "900 tris > 500 budget → fails")
    check(not by["palette_adherence"].passed, "17 colors > 16 cap → fails")
    check(not rec.passed_all, "record fails overall")


def test_digest_changes_with_result():
    print("[6] Provenance: digest tracks the actual result")
    h = make_harness()
    good = h.evaluate(GOOD, "asset-good", seed=42).digest
    bad = h.evaluate(dict(GOOD, tri_count=900), "asset-good", seed=42).digest
    check(good != bad, "a different measured result yields a different digest")


def main():
    for t in (test_scores_good_subject, test_reproducible_under_seed, test_seed_is_load_bearing,
              test_negctl_corrupt_reference, test_negctl_over_budget, test_digest_changes_with_result):
        t()
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.6 Eval SDK verified (deterministic, reproducible, discriminating)")
    sys.exit(0)


if __name__ == "__main__":
    main()
