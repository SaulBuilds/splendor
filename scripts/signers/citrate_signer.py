#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reference non-custodial signer for Splendor → CitrateNetwork.

Speaks the JSON line protocol that ``splendor.deploy.signer.SubprocessSigner``
uses. Reads one intent from stdin, writes one JSON result to stdout.

    address :  {"op":"address"}                         → {"ok":true,"address":"0x.."}
    encode  :  {"op":"encode","to":..,"function":"f(bytes32,string)","args":[..]}
                                                          → {"ok":true,"calldata":"0x.."}
    send    :  {"op":"send","rpc":..,"chainId":40204,"to":..,"function":..,
                "args":[..],"value":"0x0"}               → {"ok":true,"txHash":"0x..",..}

The private key is read from ``CITRATE_SIGNER_KEY`` (hex, ``0x``-optional) and
never leaves this process — Splendor never sees it (non-custodial). ``encode``
needs no key, so calldata can be tested without funds.

Requires ``eth_account``, ``eth_abi``, ``eth_utils`` and (for ``send``) ``web3`` —
present in the system Python, absent in Blender's bundled Python (hence a
separate process). Run it under a Python that has them, e.g.:

    export CITRATE_SIGNER_KEY=0x<your key>
    echo '{"op":"address"}' | python3 scripts/signers/citrate_signer.py
"""
import json
import os
import re
import sys


def _fail(msg):
    print(json.dumps({"ok": False, "error": str(msg)}))
    sys.exit(0)  # protocol-level failure is reported in JSON, not via exit code


def _split_types(sig):
    """('record', ['bytes32', 'string']) from 'record(bytes32,string)'."""
    m = re.match(r"^\s*([A-Za-z_]\w*)\s*\((.*)\)\s*$", sig)
    if not m:
        raise ValueError(f"bad function signature: {sig!r}")
    name, inner = m.group(1), m.group(2).strip()
    if not inner:
        return name, []
    if "(" in inner or "[" in inner:
        raise ValueError(f"unsupported arg types (tuples/arrays) in {sig!r}")
    return name, [t.strip() for t in inner.split(",")]


def _coerce(t, v):
    if t.startswith(("uint", "int")):
        return int(v, 0) if isinstance(v, str) else int(v)
    if t == "address":
        return v  # eth_abi accepts a hex address string
    if t == "bool":
        return bool(v)
    if t == "string":
        return v
    if t == "bytes" or re.match(r"^bytes\d+$", t):
        if isinstance(v, (bytes, bytearray)):
            return bytes(v)
        s = v[2:] if v.startswith("0x") else v
        return bytes.fromhex(s)
    raise ValueError(f"unsupported abi type: {t}")


def _calldata(function, args):
    from eth_abi import encode as abi_encode
    from eth_utils import keccak
    name, types = _split_types(function)
    if len(args) != len(types):
        raise ValueError(f"{function}: expected {len(types)} args, got {len(args)}")
    selector = keccak(text=f"{name}({','.join(types)})")[:4]
    body = abi_encode(types, [_coerce(t, a) for t, a in zip(types, args)])
    return selector + body


def _account():
    key = os.environ.get("CITRATE_SIGNER_KEY", "").strip()
    if not key:
        raise ValueError("CITRATE_SIGNER_KEY not set (non-custodial: the signer owns the key)")
    from eth_account import Account
    return Account.from_key(key)


def _send(intent, calldata):
    from web3 import Web3
    acct = _account()
    w3 = Web3(Web3.HTTPProvider(intent["rpc"], request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        raise ValueError(f"RPC not reachable: {intent['rpc']}")
    chain_id = int(intent.get("chainId") or w3.eth.chain_id)
    to = Web3.to_checksum_address(intent["to"])
    value = int(str(intent.get("value", "0x0")), 0)
    frm = acct.address
    tx = {
        "from": frm, "to": to, "value": value, "data": "0x" + calldata.hex(),
        "nonce": w3.eth.get_transaction_count(frm, "pending"), "chainId": chain_id,
    }
    # Gas: estimate, with a modest safety margin.
    tx["gas"] = int(w3.eth.estimate_gas({k: tx[k] for k in ("from", "to", "value", "data")}) * 1.25)
    # Fees: EIP-1559 when the chain exposes a base fee, else legacy.
    base = w3.eth.get_block("latest").get("baseFeePerGas")
    if base is not None:
        try:
            priority = w3.eth.max_priority_fee
        except Exception:
            priority = w3.to_wei(1, "gwei")
        tx["maxPriorityFeePerGas"] = int(priority)
        tx["maxFeePerGas"] = int(base * 2 + priority)
        tx["type"] = 2
    else:
        tx["gasPrice"] = w3.eth.gas_price
    signed = acct.sign_transaction(tx)
    # eth_account renamed this attribute: <0.13 uses rawTransaction, >=0.13 raw_transaction.
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = w3.eth.send_raw_transaction(raw)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    return {
        "ok": True, "op": "send", "txHash": tx_hash.hex() if isinstance(tx_hash, (bytes, bytearray)) else str(tx_hash),
        "from": frm, "to": to, "blockNumber": receipt["blockNumber"], "status": receipt["status"],
    }


def main():
    try:
        intent = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        _fail(f"invalid intent JSON: {exc}")
    op = intent.get("op", "send")
    try:
        if op == "address":
            print(json.dumps({"ok": True, "address": _account().address}))
        elif op == "encode":
            data = _calldata(intent["function"], intent.get("args", []))
            print(json.dumps({"ok": True, "calldata": "0x" + data.hex()}))
        elif op == "send":
            data = _calldata(intent["function"], intent.get("args", []))
            print(json.dumps(_send(intent, data)))
        else:
            _fail(f"unknown op: {op!r}")
    except ImportError as exc:
        _fail(f"signer dependency missing ({exc}); run under a Python with eth_account/eth_abi/web3")
    except Exception as exc:  # honest: any failure becomes a protocol error, never a fake tx
        _fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
