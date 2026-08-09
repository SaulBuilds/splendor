# SPDX-License-Identifier: GPL-2.0-or-later
"""The typed intent DSL — the reviewable, benchmarkable unit the AI emits.

Intents are plain, validated data. They carry an ``action_class`` (used by the
HIC gate) and a ``validate()`` with deterministic acceptance criteria. They are
*compiled* to bpy operators / nodes by the executors in :mod:`splendor.intents`
(D-2.3: hybrid DSL over nodes+ops). The DSL never touches Blender directly — that
separation is what makes an intent reproducible and model-agnostic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Intent:
    """Base typed intent. Subclasses set ``action_class`` and override ``validate``."""

    # Class attribute (not a dataclass field) so subclass inheritance stays simple.
    action_class: str = "generic"

    @property
    def type(self) -> str:
        return type(self).__name__

    def validate(self) -> None:
        """Raise ``ValueError`` if malformed. Deterministic, mock-forbidding."""
        return None


@dataclass(frozen=True)
class SnapVertices(Intent):
    """Snap the target mesh's vertices to a grid of ``grid`` units (PS1 vertex snap)."""

    grid: float = 0.1
    action_class = "geometry"

    def validate(self) -> None:
        if not (self.grid > 0.0):
            raise ValueError("grid must be > 0")


@dataclass(frozen=True)
class SetPalette(Intent):
    """Set the scene's retro palette size (``colors`` in [1, 256])."""

    colors: int = 16
    action_class = "scene_config"

    def validate(self) -> None:
        if not (1 <= self.colors <= 256):
            raise ValueError("colors must be in [1, 256]")
