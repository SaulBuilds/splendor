# SPDX-License-Identifier: GPL-2.0-or-later
"""The backend Router (P3) — local-first now, router-ready later.

Selects a backend by *declared capability + reachability + policy*. Today the
policy is local-first (D-2.4); the identical interface can later route by
cost / quality / latency using the Eval SDK's scores (P4) without a rewrite —
that's the "router-ready" seam. When nothing reachable satisfies the request it
raises :class:`BackendUnavailable` — an honest error, never a fabricated result.
"""
from __future__ import annotations

import enum

from .base import BackendUnavailable, CompletionRequest, Modality


class RoutePolicy(enum.Enum):
    LOCAL_FIRST = "local-first"   # prefer local, fall back to cloud
    LOCAL_ONLY = "local-only"
    CLOUD_ONLY = "cloud-only"


class Router:
    def __init__(self, backends=None, policy: RoutePolicy = RoutePolicy.LOCAL_FIRST):
        self._backends = list(backends or [])
        self.policy = policy

    def register(self, backend):
        self._backends.append(backend)
        return backend

    def candidates(self, required_modality: Modality, policy: RoutePolicy = None):
        policy = policy or self.policy
        matches = [b for b in self._backends if required_modality in b.capability.modalities]
        if policy is RoutePolicy.LOCAL_ONLY:
            return [b for b in matches if b.capability.is_local]
        if policy is RoutePolicy.CLOUD_ONLY:
            return [b for b in matches if not b.capability.is_local]
        # LOCAL_FIRST: local backends first, cloud after — stable order otherwise.
        return sorted(matches, key=lambda b: 0 if b.capability.is_local else 1)

    def select(self, required_modality: Modality = Modality.TEXT,
               policy: RoutePolicy = None, timeout: float = 1.5):
        """First reachable candidate under the policy, or None."""
        for backend in self.candidates(required_modality, policy):
            if backend.reachable(timeout=timeout):
                return backend
        return None

    def complete(self, req: CompletionRequest, policy: RoutePolicy = None):
        backend = self.select(req.required_modality, policy)
        if backend is None:
            eff = (policy or self.policy).value
            raise BackendUnavailable(
                f"no reachable backend for '{req.required_modality.value}' under policy '{eff}'")
        return backend.complete(req)
