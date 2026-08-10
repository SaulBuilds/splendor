#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Whitelist (or check) a Splendor attestation recorder on CitrateNetwork.

AgentDecisionRegistry.registerDecision is gated by ``authorizedRecorders[msg.sender]``,
set only by governance via ``setAuthorizedRecorder(address,bool)``. This is a
HUMAN-IN-CONTROL ceremony: the governance key is held out-of-band by its owner and
never touches Splendor or this repo. Run this yourself with that key in your env.

    # Read-only — no key needed; reports on-chain status:
    python3 scripts/signers/citrate_authorize_recorder.py 0x<recorder> --check

    # Authorize (the governance ceremony) — governance key stays in YOUR env:
    export CITRATE_GOVERNANCE_KEY=0x<governance key for 0x4fAB35c8…>
    python3 scripts/signers/citrate_authorize_recorder.py 0x<recorder>

The recorder address is the address of the key Splendor will sign with
(``CITRATE_SIGNER_KEY``). Idempotent: a no-op if already authorized. Verifies the
governance identity before spending gas and confirms the flag flipped afterward.

Needs eth_account/eth_abi/web3 (present in the system Python; absent in Blender's).
"""
import os
import sys

RPC = os.environ.get("CITRATE_RPC_URL", "https://rpc.citrate.ai")
REGISTRY = os.environ.get("CITRATE_DECISION_REGISTRY", "0x728dbe86ce56123a5c1ddc248392940d7d2d30f9")
CHAIN_ID = 40204


def _die(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    check_only = "--check" in argv
    if not args:
        _die("usage: citrate_authorize_recorder.py 0x<recorder> [--check]")
    try:
        from web3 import Web3
    except ImportError as exc:
        _die(f"missing dependency ({exc}); run under a Python with web3/eth_account/eth_abi")

    w3 = Web3(Web3.HTTPProvider(RPC, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        _die(f"RPC not reachable: {RPC}")
    recorder = Web3.to_checksum_address(args[0])
    registry = Web3.to_checksum_address(REGISTRY)

    def governance():
        return Web3.to_checksum_address("0x" + w3.eth.call({"to": registry, "data": "0x5aa6e675"}).hex()[-40:])

    def is_authorized(addr):
        data = "0xac9a5e9a" + addr[2:].lower().rjust(64, "0")
        return int(w3.eth.call({"to": registry, "data": data}).hex(), 16) != 0

    gov = governance()
    already = is_authorized(recorder)
    print(f"registry   : {registry}")
    print(f"governance : {gov}")
    print(f"recorder   : {recorder}")
    print(f"authorized : {already}")
    if check_only:
        return 0
    if already:
        print("→ already an authorized recorder; nothing to do.")
        return 0

    key = os.environ.get("CITRATE_GOVERNANCE_KEY", "").strip()
    if not key:
        _die("CITRATE_GOVERNANCE_KEY not set — the governance ceremony needs the "
             f"governor's key ({gov}). It never leaves your environment.")
    from eth_abi import encode as abi_encode
    from eth_account import Account
    acct = Account.from_key(key)
    if acct.address.lower() != gov.lower():
        _die(f"the provided key is {acct.address}, but governance is {gov}. "
             "Only the governor can authorize recorders.")

    # setAuthorizedRecorder(address,bool) = 0x272d023a
    data = "0x272d023a" + abi_encode(["address", "bool"], [recorder, True]).hex()
    tx = {"from": acct.address, "to": registry, "value": 0, "data": data,
          "nonce": w3.eth.get_transaction_count(acct.address, "pending"), "chainId": CHAIN_ID}
    tx["gas"] = int(w3.eth.estimate_gas({k: tx[k] for k in ("from", "to", "value", "data")}) * 1.25)
    base = w3.eth.get_block("latest").get("baseFeePerGas")
    if base is not None:
        try:
            prio = w3.eth.max_priority_fee
        except Exception:
            prio = w3.to_wei(1, "gwei")
        tx.update(maxPriorityFeePerGas=int(prio), maxFeePerGas=int(base * 2 + prio), type=2)
    else:
        tx["gasPrice"] = w3.eth.gas_price
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    print(f"→ setAuthorizedRecorder tx: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        _die(f"tx reverted (status 0): {tx_hash.hex()}")
    if not is_authorized(recorder):
        _die("tx succeeded but recorder still not authorized — investigate.")
    print(f"✓ authorized (block {receipt['blockNumber']}). {recorder} can now record attestations.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
