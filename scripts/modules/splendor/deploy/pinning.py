# SPDX-License-Identifier: GPL-2.0-or-later
"""Content-addressed pinning (P7).

Assets are addressed by the hash of their bytes (``sha256:...``), so retrieval is
self-verifying: :meth:`HttpPinning.fetch` recomputes the hash and raises
:class:`IntegrityError` if the bytes don't match the CID — a tampered or wrong
payload can never be trusted. Endpoint-agnostic (Citrate pinning is one backend);
an unreachable endpoint raises :class:`PinUnavailable`, never a fake success.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .errors import IntegrityError, PinUnavailable


def content_address(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass
class PinRef:
    cid: str
    size: int


class PinningBackend:
    def pin(self, data: bytes) -> PinRef:
        raise NotImplementedError

    def fetch(self, cid: str) -> bytes:
        raise NotImplementedError

    def verify(self, cid: str, data: bytes) -> bool:
        return content_address(data) == cid


class HttpPinning(PinningBackend):
    """Pins over HTTP (``POST /pin`` -> {cid}, ``GET /pin/<cid>`` -> bytes).
    Verifies the CID on pin *and* on every fetch."""

    def __init__(self, base_url: str, timeout: float = 5.0):
        self.base_url = (base_url or "").rstrip("/")
        self.timeout = timeout

    def pin(self, data: bytes) -> PinRef:
        try:
            req = urllib.request.Request(
                self.base_url + "/pin", data=data, method="POST",
                headers={"Content-Type": "application/octet-stream"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError) as exc:
            raise PinUnavailable(f"pinning unreachable: {exc}") from exc
        cid = body.get("cid")
        expected = content_address(data)
        if cid != expected:
            raise IntegrityError(f"pin returned cid {cid} != {expected}")
        return PinRef(cid, len(data))

    def fetch(self, cid: str) -> bytes:
        try:
            with urllib.request.urlopen(self.base_url + "/pin/" + cid, timeout=self.timeout) as resp:
                data = resp.read()
        except (urllib.error.URLError, OSError) as exc:
            raise PinUnavailable(f"pinning unreachable: {exc}") from exc
        if content_address(data) != cid:
            raise IntegrityError(f"retrieved bytes do not match cid {cid} (tampered?)")
        return data
