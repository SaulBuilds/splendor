# SPDX-License-Identifier: GPL-2.0-or-later
"""Citrate-green accent (the mock's 'green replaces Blender blue' decision).

Applies Citrate green as the active/selected accent so the app reads as
chain-native from the first pixel, without otherwise disturbing Blender's theme.
Reversible; only touches the select/active colors.
"""
from __future__ import annotations

import bpy

# #8ecc09 / #ffbd10 / #0f2a1a as 0..1 sRGB floats (Blender theme color space).
CITRATE_GREEN = (0.557, 0.800, 0.035)
CITRATE_YELLOW = (1.000, 0.741, 0.063)
EVERGREEN = (0.059, 0.165, 0.102)


def apply_accent():
    """Set the green accent on the key select/active colors. Returns green for verify."""
    theme = bpy.context.preferences.themes[0]
    v3d = theme.view_3d
    v3d.object_active = CITRATE_GREEN
    v3d.object_selected = CITRATE_GREEN
    ui = theme.user_interface
    ui.wcol_tool.inner_sel = (*CITRATE_GREEN, 1.0)
    ui.wcol_option.inner_sel = (*CITRATE_GREEN, 1.0)
    return tuple(v3d.object_active)
