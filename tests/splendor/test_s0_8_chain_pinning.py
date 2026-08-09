# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.8 acceptance test — chain/pinning/identity adapter (P7 seam).

Pure Python:  python3 tests/splendor/test_s0_8_chain_pinning.py

Exits non-zero on any failure. Acceptance: a tampered asset fails hash
verification on retrieval; an unreachable endpoint shows an honest error, never a
fake success; AA sign-in is named honestly ("not yet"), not faked. Bonus: a
provenance record ties the pinned asset (P7) + eval digest (P4) + workflow (P5),
attested through the composable chain interface.
"""
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.dirname(__file__))

from splendor.deploy import (  # noqa: E402
    ChainRegistry, ChainUnavailable, HttpChainAdapter, HttpPinning, IdentityNotAvailable,
    IntegrityError, MemoryChainAdapter, PinUnavailable, SmartAccountIdentity, content_address,
    make_provenance,
)
from splendor.graph import Edge, END, Node, START, WorkflowGraph, dumps  # noqa: E402
from splendor_eval import EvalHarness, PaletteAdherence  # noqa: E402
import _pinning_server  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


ASSET = b"SPLENDOR glTF bytes (a low-poly PS1 potion) ..."


def test_pin_fetch_verify_roundtrip():
    print("[1] Content-addressed pin → fetch → verify round-trip")
    _srv, port, _store = _pinning_server.start()
    pin = HttpPinning(f"http://127.0.0.1:{port}")
    ref = pin.pin(ASSET)
    check(ref.cid == content_address(ASSET), "CID is the sha256 content address")
    got = pin.fetch(ref.cid)
    check(got == ASSET and pin.verify(ref.cid, got), "fetched bytes match + verify OK")


def test_tampered_asset_fails_integrity():
    print("[2] NEG CONTROL: a tampered asset fails hash verification on retrieval")
    _srv, port, _store = _pinning_server.start(tamper=True)
    pin = HttpPinning(f"http://127.0.0.1:{port}")
    ref = pin.pin(ASSET)   # stored fine; retrieval corrupts
    try:
        pin.fetch(ref.cid)
        check(False, "tampered fetch should raise IntegrityError")
    except IntegrityError:
        check(True, "retrieved bytes ≠ CID → IntegrityError (no silent trust)")


def test_unreachable_is_honest():
    print("[3] NEG CONTROL: unreachable endpoints → honest errors, never fake success")
    dead = HttpPinning("http://127.0.0.1:1")
    try:
        dead.pin(ASSET); check(False, "dead pinning should raise")
    except PinUnavailable:
        check(True, "unreachable pinning → PinUnavailable")
    try:
        HttpChainAdapter("citrate-testnet", "").attest({"x": 1}); check(False, "unconfigured chain should raise")
    except ChainUnavailable:
        check(True, "no RPC endpoint configured → ChainUnavailable (unverified per WP-0)")
    try:
        HttpChainAdapter("citrate-testnet", "http://127.0.0.1:1").attest({"x": 1}); check(False, "dead chain should raise")
    except ChainUnavailable:
        check(True, "unreachable chain endpoint → ChainUnavailable")


def test_composable_chain_and_provenance():
    print("[4] Composable chain interface + provenance ties asset (P7) + eval (P4) + workflow (P5)")
    # pin the asset
    _srv, port, _store = _pinning_server.start()
    pin = HttpPinning(f"http://127.0.0.1:{port}")
    cid = pin.pin(ASSET).cid
    # eval digest (P4)
    eval_digest = EvalHarness([PaletteAdherence(16)]).evaluate({"palette_colors": 16}, "potion").digest
    # workflow (P5)
    wf = dumps(WorkflowGraph([Node("p", "prompt"), Node("m", "model")],
                             [Edge(START, "p"), Edge("p", "m"), Edge("m", END)]))
    prov = make_provenance(cid, eval_digest=eval_digest, workflow=wf, meta={"creator": "vibe-artist"})
    check(prov["asset"] == cid and prov["eval"] == eval_digest and prov["workflow"] == wf,
          "provenance record references pinned asset + eval digest + workflow")

    # composable registry: CitrateNetwork-first, EVM pluggable
    reg = ChainRegistry()
    reg.register(MemoryChainAdapter("citrate"))
    reg.register(MemoryChainAdapter("evm:base"))
    check(reg.networks() == ["citrate", "evm:base"], "registry is composable across chains (D-5.2)")

    ref = reg.get("citrate").attest(prov)
    back = reg.get("citrate").get_attestation(ref)
    check(back == prov and ref.network == "citrate", "attest + retrieve round-trips the provenance record")


def test_identity_named_honestly():
    print("[5] AA sign-in is named honestly ('not yet'), not faked")
    ident = SmartAccountIdentity(login_hint="creator@example.com")
    for fn, what in ((ident.address, "address"), (lambda: ident.sign(b"msg"), "sign")):
        try:
            fn(); check(False, f"{what} should raise IdentityNotAvailable")
        except IdentityNotAvailable:
            check(True, f"{what}() honestly raises IdentityNotAvailable (no fake signature)")


def test_live_citrate_optional():
    print("[6] Live Citrate endpoints (optional): reachable → real pin, else honest 'unverified'")
    url = os.environ.get("SPLENDOR_CITRATE_PINNING")
    if not url:
        print("     (SPLENDOR_CITRATE_PINNING unset → Citrate live pinning UNVERIFIED per WP-0; interface + hashing verified above)")
        return
    try:
        HttpPinning(url).pin(ASSET)
        print("     live Citrate pinning reachable — real pin succeeded")
    except PinUnavailable as exc:
        print(f"     live Citrate pinning unreachable (honest): {exc}")


def main():
    for t in (test_pin_fetch_verify_roundtrip, test_tampered_asset_fails_integrity,
              test_unreachable_is_honest, test_composable_chain_and_provenance,
              test_identity_named_honestly, test_live_citrate_optional):
        t()
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.8 chain/pinning/identity verified (content-addressed, honest, composable)")
    sys.exit(0)


if __name__ == "__main__":
    main()
