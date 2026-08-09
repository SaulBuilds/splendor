# SPDX-License-Identifier: GPL-2.0-or-later
"""Identity (P7, D-5.4) — account-abstraction sign-in for vibe creators.

Honest by construction: the AA flow (email/passkey -> smart account, invisible
gas) is NOT YET implemented, so it says so — it never fakes a signature. Custody
is non-custodial by design (D-9.9); the real flow is counsel-gated before Phase 1
(D-9.7) and lands with the SPL-S1 mock.
"""
from __future__ import annotations

from .errors import IdentityNotAvailable


class Identity:
    def address(self) -> str:
        raise NotImplementedError

    def sign(self, message: bytes) -> bytes:
        raise NotImplementedError


class SmartAccountIdentity(Identity):
    def __init__(self, login_hint=None):
        self.login_hint = login_hint

    def address(self) -> str:
        raise IdentityNotAvailable(
            "account-abstraction sign-in not yet implemented (D-5.4); coming with the SPL-S1 mock")

    def sign(self, message: bytes) -> bytes:
        raise IdentityNotAvailable(
            "account-abstraction signing not yet implemented (non-custodial, D-9.9)")
