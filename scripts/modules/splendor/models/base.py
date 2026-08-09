# SPDX-License-Identifier: GPL-2.0-or-later
"""Model-agnostic backend contract (P3).

No feature hardcodes a model or provider (CLAUDE Rule 6). Every backend declares
a :class:`Capability`; the :mod:`splendor.models.router` selects by *declared
capability + reachability + policy*, never by a hardcoded name. Local-first now,
router-ready for a cost/quality/eval-scored router later (D-2.4).

Pure Python + stdlib ``urllib`` only — no third-party client, so the layer works
in Blender's bundled Python and offline.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Optional


class Modality(enum.Enum):
    TEXT = "text"
    VISION = "vision"
    EMBEDDING = "embedding"
    IMAGE_GEN = "image-gen"


@dataclass(frozen=True)
class Capability:
    """What a backend can do — the contract the Router selects against."""

    modalities: frozenset
    is_local: bool
    context_tokens: Optional[int] = None
    supports_tools: bool = False


@dataclass
class Message:
    role: str      # "system" | "user" | "assistant"
    content: str


@dataclass
class CompletionRequest:
    messages: list          # list[Message]
    max_tokens: int = 256
    temperature: float = 0.2
    required_modality: Modality = Modality.TEXT


@dataclass
class CompletionResult:
    text: str
    backend: str
    model: str
    raw: dict = field(default_factory=dict)


class BackendError(Exception):
    """Base class for backend failures."""


class BackendUnavailable(BackendError):
    """The backend could not be reached — an *honest* failure, never a fake result."""


class Backend:
    """Abstract backend. Subclasses declare ``name`` + ``capability`` and implement
    :meth:`reachable` and :meth:`complete`."""

    name: str
    capability: Capability

    def reachable(self, timeout: float = 1.5) -> bool:
        raise NotImplementedError

    def complete(self, req: CompletionRequest, timeout: float = 30.0) -> CompletionResult:
        raise NotImplementedError
