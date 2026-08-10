# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor Retro Engine (P1) — the PS1-era look.

S0.2 lands the first real effect: a GPU palette-quantization pass. ``palette``
(pure Python) generates the target palette, provides the CPU ground truth, and
measures the output's color count (feeding the Eval SDK). ``gpu_pass`` runs the
real GPU shader. Affine texture warp, vertex snap (see the S0.3 DSL), dithering,
and vertex/Gouraud lighting are the rest of P1.
"""
from __future__ import annotations

from . import palette, postprocess
from .postprocess import (
    bayer_matrix, dither_quantize, pixelate, reduce_color_depth, retro_frame,
)

__all__ = [
    "palette", "postprocess", "quantize_image_gpu",
    "bayer_matrix", "dither_quantize", "pixelate", "reduce_color_depth", "retro_frame",
]


def quantize_image_gpu(*args, **kwargs):
    """Lazy proxy to :func:`splendor.retro.gpu_pass.quantize_image_gpu` (defers the
    ``gpu`` import so the pure-Python palette tools import without a GPU)."""
    from .gpu_pass import quantize_image_gpu as _q
    return _q(*args, **kwargs)
