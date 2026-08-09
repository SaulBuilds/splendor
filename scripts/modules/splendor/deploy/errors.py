# SPDX-License-Identifier: GPL-2.0-or-later
"""Deploy-layer errors — all honest failures, never silent fake success."""
from __future__ import annotations


class DeployError(Exception):
    pass


class PinUnavailable(DeployError):
    """Pinning endpoint unreachable."""


class ChainUnavailable(DeployError):
    """Chain endpoint unreachable or unconfigured."""


class IntegrityError(DeployError):
    """Content hash did not match the CID (tampered / wrong payload)."""


class IdentityNotAvailable(DeployError):
    """A sign-in / signing path that is honestly not implemented yet."""
