# SPDX-License-Identifier: GPL-2.0-or-later
"""Non-custodial transaction signing (P7) — delegated to an external process.

Splendor runs inside Blender's bundled Python, which has no EVM signing stack
(``eth_account``/``eth_abi``/``web3`` are absent) and, by design, never holds a
private key. Signing is therefore delegated to a separate **signer process** that
owns the key material — matching Citrate's own pattern (emit unsigned intent, a
non-custodial signer signs + broadcasts).

The signer is any executable speaking a tiny JSON line protocol on stdin/stdout:

    intent  →  {"op": "send", "rpc": ..., "chainId": 40204, "to": "0x..",
                "function": "record(bytes32,string)", "args": ["0x..", "Qm.."],
                "value": "0x0"}
    result  ←  {"ok": true, "op": "send", "txHash": "0x..", "from": "0x..",
                "blockNumber": 123, "status": 1}

Other ops: ``{"op": "address"}`` → ``{"ok": true, "address": "0x.."}`` and
``{"op": "encode", ...}`` → ``{"ok": true, "calldata": "0x.."}`` (no key needed,
used to unit-test calldata without funds). Failures return
``{"ok": false, "error": "..."}`` and surface here as SignerUnavailable.

A reference signer that speaks this protocol ships at
``scripts/signers/citrate_signer.py`` (uses eth_account + eth_abi + web3, reading
the key from ``CITRATE_SIGNER_KEY``). Point Splendor at any signer via
``SPLENDOR_CITRATE_SIGNER`` (a shell command); with only ``CITRATE_SIGNER_KEY``
set, the bundled reference signer is used. With neither, there is no signer and
attestation fails honestly — never faked.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys

from .errors import SignerUnavailable


def _repo_root() -> str:
    # …/scripts/modules/splendor/deploy/signer.py → repo root is four levels up.
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir, os.pardir))


def default_signer_script() -> str:
    return os.path.join(_repo_root(), "scripts", "signers", "citrate_signer.py")


class SubprocessSigner:
    """A signer invoked as a subprocess, one JSON intent per call.

    ``command`` is the argv list to run (e.g. ``["python3", "…/citrate_signer.py"]``).
    Each call spawns the process fresh, writes the intent JSON to stdin, and reads a
    single JSON result from stdout. The private key never crosses this boundary — it
    lives only in the signer process's own environment.
    """

    def __init__(self, command, timeout: float = 180.0, env: dict | None = None):
        self.command = list(command)
        self.timeout = timeout
        # The signer inherits the environment (so CITRATE_SIGNER_KEY reaches it),
        # optionally overlaid with extra vars.
        self._env = dict(os.environ)
        if env:
            self._env.update(env)

    def _invoke(self, payload: dict) -> dict:
        try:
            proc = subprocess.run(
                self.command, input=json.dumps(payload), capture_output=True,
                text=True, timeout=self.timeout, env=self._env,
            )
        except FileNotFoundError as exc:
            raise SignerUnavailable(f"signer command not found: {self.command!r} ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise SignerUnavailable(f"signer timed out after {self.timeout}s: {self.command!r}") from exc
        if proc.returncode != 0 and not proc.stdout.strip():
            raise SignerUnavailable(
                f"signer exited {proc.returncode}: {proc.stderr.strip() or '(no output)'}")
        try:
            result = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise SignerUnavailable(
                f"signer produced no JSON result: {proc.stdout.strip()[:200]!r} "
                f"stderr={proc.stderr.strip()[:200]!r}") from exc
        if not result.get("ok"):
            raise SignerUnavailable(f"signer error: {result.get('error', result)}")
        return result

    def address(self) -> str:
        return self._invoke({"op": "address"})["address"]

    def encode(self, to: str, function: str, args: list) -> str:
        return self._invoke({"op": "encode", "to": to, "function": function, "args": list(args)})["calldata"]

    def send(self, rpc: str, chain_id: int, to: str, function: str, args: list, value: int = 0) -> dict:
        return self._invoke({
            "op": "send", "rpc": rpc, "chainId": chain_id, "to": to,
            "function": function, "args": list(args), "value": hex(value),
        })


def resolve_signer(env: dict | None = None):
    """Return a configured non-custodial signer, or None if none is configured.

    Precedence (both are explicit user opt-in — Splendor never invents a key):
      1. ``SPLENDOR_CITRATE_SIGNER`` — a shell command to run as the signer.
      2. ``CITRATE_SIGNER_KEY`` present → the bundled reference signer
         (``scripts/signers/citrate_signer.py``) run under ``python3``.
    Returns None when neither is set → callers raise honestly.
    """
    env = env if env is not None else os.environ
    command = env.get("SPLENDOR_CITRATE_SIGNER", "").strip()
    if command:
        return SubprocessSigner(shlex.split(command))
    if env.get("CITRATE_SIGNER_KEY", "").strip():
        script = default_signer_script()
        if os.path.exists(script):
            # Prefer an explicit interpreter; fall back to PATH's python3 (Blender's
            # bundled python lacks the eth stack, so never sys.executable here).
            python = env.get("SPLENDOR_SIGNER_PYTHON", "python3")
            return SubprocessSigner([python, script])
    return None
