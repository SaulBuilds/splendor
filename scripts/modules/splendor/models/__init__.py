# SPDX-License-Identifier: GPL-2.0-or-later
"""Model-agnostic backend layer (P3).

A general model-execution abstraction (not just LLM servers): backends declare a
:class:`~splendor.models.base.Capability`, and the :class:`~splendor.models.router.Router`
selects by capability + reachability + policy. Local-first, offline-capable,
router-ready. See ``docs/architecture/SPLENDOR_ARCHITECTURE_SPEC.md`` §P3.
"""
from __future__ import annotations

from . import base, openai_compat, router
from .base import (
    Backend, BackendError, BackendUnavailable, Capability,
    CompletionRequest, CompletionResult, Message, Modality,
)
from .openai_compat import OpenAICompatBackend
from .router import RoutePolicy, Router

__all__ = [
    "base", "openai_compat", "router",
    "Backend", "BackendError", "BackendUnavailable", "Capability",
    "CompletionRequest", "CompletionResult", "Message", "Modality",
    "OpenAICompatBackend", "RoutePolicy", "Router",
]
