# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor deploy layer (P7) — ship work to the web and CitrateNetwork.

Content-addressed pinning, a composable chain interface (CitrateNetwork-first,
EVM/Solana pluggable), provenance records tying asset + eval + workflow, and
account-abstraction identity. Honest by construction: unreachable endpoints and
unbuilt sign-in fail loudly, never fake success. Pure Python, bpy-independent.
"""
from __future__ import annotations

from . import chain, citrate, gallery, identity, pinning, provenance, signer
from .gallery import (
    GalleryItem, gateway_url, page_cid, publish_gallery, publish_item, render_index, render_item_page,
)
from .chain import (
    AttestationRef, ChainAdapter, ChainRegistry, HttpChainAdapter, MemoryChainAdapter,
)
from .citrate import (
    ATTEST_FUNCTION, ATTEST_SELECTOR, CITRATE_TESTNET, CitrateEvmChain, IpfsPinning, citrate_config,
)
from .errors import (
    ChainUnavailable, DeployError, IdentityNotAvailable, IntegrityError, PinUnavailable,
    SignerUnavailable,
)
from .identity import Identity, SmartAccountIdentity
from .pinning import HttpPinning, PinRef, PinningBackend, content_address
from .provenance import make_provenance
from .signer import SubprocessSigner, default_signer_script, resolve_signer

__all__ = [
    "chain", "identity", "pinning", "provenance", "signer",
    "AttestationRef", "ChainAdapter", "ChainRegistry", "HttpChainAdapter", "MemoryChainAdapter",
    "ChainUnavailable", "DeployError", "IdentityNotAvailable", "IntegrityError", "PinUnavailable",
    "SignerUnavailable",
    "Identity", "SmartAccountIdentity",
    "HttpPinning", "PinRef", "PinningBackend", "content_address", "make_provenance",
    "ATTEST_FUNCTION", "ATTEST_SELECTOR", "CITRATE_TESTNET", "CitrateEvmChain", "IpfsPinning", "citrate_config",
    "SubprocessSigner", "default_signer_script", "resolve_signer",
    "gallery", "GalleryItem", "gateway_url", "page_cid", "publish_item", "render_item_page",
    "publish_gallery", "render_index",
]
__version__ = (0, 0, 1)
