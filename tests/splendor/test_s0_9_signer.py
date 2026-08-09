# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.9 — non-custodial attestation signer.

    python3 tests/splendor/test_s0_9_signer.py

Verifies the delegated signer wiring for on-chain attestation:
  - no signer configured → SignerUnavailable (honest, never a fake attestation);
  - the reference signer encodes real AgentDecisionRegistry.registerDecision calldata
    (golden selector 0xf5d83567) and round-trips the args (zero funds/keys needed);
  - a real attest() against the live chain with an unfunded/unauthorised key surfaces
    the chain's own error — never a fabricated tx.

Signer-dependent checks SKIP honestly when eth_account/eth_abi are absent, so CI stays
deterministic on hosts without the EVM stack.
"""
import importlib.util
import os
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.deploy import (  # noqa: E402
    ATTEST_SELECTOR, ChainUnavailable, CitrateEvmChain, SignerUnavailable, SubprocessSigner,
    content_address, make_provenance, resolve_signer,
)

_FAIL = []
_SIGNER = os.path.join(_REPO, "scripts", "signers", "citrate_signer.py")
_HAVE_ETH = all(importlib.util.find_spec(m) for m in ("eth_account", "eth_abi"))


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    print("[1] Non-custodial by default: no signer env → resolve_signer is None")
    env = {k: v for k, v in os.environ.items()
           if k not in ("SPLENDOR_CITRATE_SIGNER", "CITRATE_SIGNER_KEY")}
    check(resolve_signer(env) is None, "resolve_signer(no signer env) → None")
    check(issubclass(SignerUnavailable, ChainUnavailable), "SignerUnavailable is a ChainUnavailable")

    print("[2] attest() with no signer → SignerUnavailable (honest, not faked)")
    chain = CitrateEvmChain(signer=None)
    # Guarantee no ambient signer is picked up from the environment.
    for k in ("SPLENDOR_CITRATE_SIGNER", "CITRATE_SIGNER_KEY"):
        os.environ.pop(k, None)
    prov = make_provenance(content_address(b"a low-poly potion"), eval_digest="sha256:beef",
                           workflow="potion-workflow", meta={"prompt": "PS1 health potion"})
    try:
        chain.attest(prov)
        check(False, "attest should raise without a signer")
    except SignerUnavailable as exc:
        check("signer" in str(exc).lower(), "attest raised SignerUnavailable (mentions the signer)")

    if not _HAVE_ETH:
        print("[3] SKIP — eth_account/eth_abi absent; signer encode/send checks need the EVM stack")
        return _finish()

    print("[3] Reference signer encodes real registerDecision calldata (golden 0xf5d83567)")
    signer = SubprocessSigner(["python3", _SIGNER])
    args = chain._decision_args(prov)
    calldata = signer.encode(to=chain.registry, function="registerDecision(bytes32,string,bytes32)", args=args)
    check(calldata.startswith(ATTEST_SELECTOR), f"calldata selector == {ATTEST_SELECTOR} (real deployed ABI)")
    # Round-trip the ABI to prove the args land where the contract expects them.
    from eth_abi import decode as abi_decode
    body = bytes.fromhex(calldata[10:])  # strip 0x + 4-byte selector
    agent_id, tool_name, params_hash = abi_decode(["bytes32", "string", "bytes32"], body)
    check(tool_name == "potion-workflow", "toolName round-trips (workflow name)")
    check("0x" + params_hash.hex() == args[2], "paramsHash round-trips (binds the record digest)")

    print("[4] Real attest() against the live chain surfaces the chain's own error (no fake tx)")
    from eth_account import Account
    key = os.environ.get("CITRATE_SIGNER_KEY_FUNDED", "")  # opt-in funded+authorised recorder
    acct = Account.from_key(key) if key else Account.create()
    live = SubprocessSigner(["python3", _SIGNER], env={"CITRATE_SIGNER_KEY": acct.key.hex()})
    lchain = CitrateEvmChain(signer=live)
    if not lchain.reachable():
        print("     SKIP — rpc.citrate.ai unreachable (offline)")
        return _finish()
    try:
        ref = lchain.attest(prov)
        # Only a funded, authorised recorder reaches here — verify the on-chain receipt.
        rec = lchain.get_attestation(ref)
        check(rec["status"] == 1, f"attestation landed on-chain (tx {ref.id[:14]}…, block {rec['block']})")
    except SignerUnavailable as exc:
        low = str(exc).lower()
        honest = any(s in low for s in ("insufficient funds", "notauthorizedrecorder", "revert", "gas"))
        check(honest, f"unfunded/unauthorised key → real chain error, not a fake tx ({str(exc)[:80]}…)")

    return _finish()


def _finish():
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — attestation signer wired (non-custodial; real calldata; honest failures)")
    sys.exit(0)


if __name__ == "__main__":
    main()
