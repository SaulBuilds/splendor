# SPDX-License-Identifier: GPL-2.0-or-later
"""Composable chain interface (P7, D-5.2) — CitrateNetwork-first, EVM/Solana pluggable.

A :class:`ChainAdapter` attests a provenance record (work hash + eval digest + run
trace). :class:`ChainRegistry` makes the target chain a pluggable choice so nothing
chain-specific leaks into P1–P5. :class:`HttpChainAdapter` talks to a configured
endpoint (e.g. Citrate testnet) and raises :class:`ChainUnavailable` when it's unset
or unreachable — never a fabricated attestation. :class:`MemoryChainAdapter` is an
honest in-process adapter (clearly *not* a real chain) for the interface + dev/CI.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .errors import ChainUnavailable


@dataclass
class AttestationRef:
    id: str
    network: str
    digest: str


def digest_record(record: dict) -> str:
    canon = json.dumps(record, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canon.encode()).hexdigest()


class ChainAdapter:
    network: str

    def attest(self, record: dict) -> AttestationRef:
        raise NotImplementedError

    def get_attestation(self, ref) -> dict:
        raise NotImplementedError


class MemoryChainAdapter(ChainAdapter):
    """In-process adapter. Honestly NOT a real chain — attestations live in memory.
    Proves the interface + provenance flow without external infra."""

    def __init__(self, network: str = "memory"):
        self.network = network
        self._store: dict = {}

    def attest(self, record: dict) -> AttestationRef:
        d = digest_record(record)
        self._store[d] = record
        return AttestationRef(id=d, network=self.network, digest=d)

    def get_attestation(self, ref) -> dict:
        d = ref.digest if isinstance(ref, AttestationRef) else ref
        return self._store.get(d)


class HttpChainAdapter(ChainAdapter):
    """Attest to a real chain endpoint. Endpoint from config/env; unset or
    unreachable -> ChainUnavailable (unverified per WP-0), never a fake attestation."""

    def __init__(self, network: str, rpc_url: str = "", timeout: float = 5.0):
        self.network = network
        self.rpc_url = (rpc_url or "").rstrip("/")
        self.timeout = timeout

    def attest(self, record: dict) -> AttestationRef:
        if not self.rpc_url:
            raise ChainUnavailable(f"{self.network}: no RPC endpoint configured (unverified per WP-0)")
        d = digest_record(record)
        try:
            req = urllib.request.Request(
                self.rpc_url + "/attest",
                data=json.dumps({"record": record, "digest": d}).encode(),
                method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError) as exc:
            raise ChainUnavailable(f"{self.network} unreachable: {exc}") from exc
        return AttestationRef(id=body.get("id", d), network=self.network, digest=d)


class ChainRegistry:
    def __init__(self):
        self._adapters: dict = {}

    def register(self, adapter: ChainAdapter) -> ChainAdapter:
        self._adapters[adapter.network] = adapter
        return adapter

    def get(self, network: str) -> ChainAdapter:
        if network not in self._adapters:
            raise KeyError(f"no chain adapter registered for {network!r}")
        return self._adapters[network]

    def networks(self):
        return sorted(self._adapters)
