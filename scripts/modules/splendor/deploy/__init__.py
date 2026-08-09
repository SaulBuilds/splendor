# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor deploy layer (P7) — ship work to the web and CitrateNetwork.

Content-addressed pinning, a composable chain interface (CitrateNetwork-first,
EVM/Solana pluggable), provenance records tying asset + eval + workflow, and
account-abstraction identity. Honest by construction: unreachable endpoints and
unbuilt sign-in fail loudly, never fake success. Pure Python, bpy-independent.
"""
from __future__ import annotations

from . import chain, citrate, identity, pinning, provenance
from .chain import (
    AttestationRef, ChainAdapter, ChainRegistry, HttpChainAdapter, MemoryChainAdapter,
)
from .citrate import CITRATE_TESTNET, CitrateEvmChain, IpfsPinning, citrate_config
from .errors import (
    ChainUnavailable, DeployError, IdentityNotAvailable, IntegrityError, PinUnavailable,
)
from .identity import Identity, SmartAccountIdentity
from .pinning import HttpPinning, PinRef, PinningBackend, content_address
from .provenance import make_provenance

__all__ = [
    "chain", "identity", "pinning", "provenance",
    "AttestationRef", "ChainAdapter", "ChainRegistry", "HttpChainAdapter", "MemoryChainAdapter",
    "ChainUnavailable", "DeployError", "IdentityNotAvailable", "IntegrityError", "PinUnavailable",
    "Identity", "SmartAccountIdentity",
    "HttpPinning", "PinRef", "PinningBackend", "content_address", "make_provenance",
    "CITRATE_TESTNET", "CitrateEvmChain", "IpfsPinning", "citrate_config",
]
__version__ = (0, 0, 1)
