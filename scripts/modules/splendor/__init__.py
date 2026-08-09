# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor — the governed AI action core.

This package is the design-independent spine every AI surface wires into. The
in-app agent panel and the MCP server both drive the scene through exactly one
path: :func:`splendor.action_api.execute`, gated by :mod:`splendor.hic` (Human In
Control), acting on the typed intents in :mod:`splendor.dsl` via the private
executors in :mod:`splendor.intents`.

Invariants (see ``.agentile/AGENT_ENTRY.md``):
  I-1  one action API — no second, ungoverned path.
  I-2  the HIC gate runs before execution.
  I-3  every action is recorded with principal, grant and HIC level.
"""
from __future__ import annotations

from . import action_api, dsl, hic, intents

__all__ = ["action_api", "dsl", "hic", "intents"]

__version__ = (0, 0, 1)
