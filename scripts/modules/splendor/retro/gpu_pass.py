# SPDX-License-Identifier: GPL-2.0-or-later
"""The real GPU palette-quantization pass (P1).

A fullscreen fragment shader that maps every pixel to its nearest palette color —
the signature PS1 palette-cap look — running on the actual GPU via Blender's
``gpu`` module. The palette is a texture (scales to 256 colors, unlike push
constants). Verified headlessly on this box's NVIDIA GB10 (Vulkan backend) by
rendering into an offscreen buffer and reading it back.

Requires a GPU context: call happens after ``gpu.init()`` (done here). The live
3D-viewport overlay that reuses this shader is a documented follow-up; this pass
is the verified core.
"""
from __future__ import annotations

_SHADER = None


def _build_shader():
    global _SHADER
    if _SHADER is not None:
        return _SHADER
    import gpu

    iface = gpu.types.GPUStageInterfaceInfo("splendor_retro_iface")
    iface.smooth('VEC2', "uv")
    info = gpu.types.GPUShaderCreateInfo()
    info.sampler(0, 'FLOAT_2D', "img")
    info.sampler(1, 'FLOAT_2D', "pal")
    info.push_constant('INT', "pal_n")
    info.vertex_in(0, 'VEC2', "pos")
    info.vertex_in(1, 'VEC2', "uv_in")
    info.vertex_out(iface)
    info.fragment_out(0, 'VEC4', "fragColor")
    info.vertex_source("void main(){ uv = uv_in; gl_Position = vec4(pos, 0.0, 1.0); }")
    info.fragment_source(
        "void main(){"
        "  vec3 c = texture(img, uv).rgb;"
        "  float best = 1e9; vec3 bc = texelFetch(pal, ivec2(0, 0), 0).rgb;"
        "  for (int i = 0; i < pal_n; i++) {"
        "    vec3 p = texelFetch(pal, ivec2(i, 0), 0).rgb;"
        "    float d = distance(c, p);"
        "    if (d < best) { best = d; bc = p; }"
        "  }"
        "  fragColor = vec4(bc, 1.0);"
        "}"
    )
    _SHADER = gpu.shader.create_from_info(info)
    return _SHADER


def quantize_image_gpu(rgba_flat, width, height, palette):
    """Quantize a flat RGBA image to ``palette`` on the GPU; return flat RGBA floats."""
    import gpu
    import numpy as np
    from gpu_extras.batch import batch_for_shader

    gpu.init()
    w, h = int(width), int(height)

    img = gpu.types.GPUTexture(
        (w, h), format='RGBA32F',
        data=gpu.types.Buffer('FLOAT', w * h * 4, list(rgba_flat)))

    pal_flat = []
    for (r, g, b) in palette:
        pal_flat += [float(r), float(g), float(b), 1.0]
    pal = gpu.types.GPUTexture(
        (len(palette), 1), format='RGBA32F',
        data=gpu.types.Buffer('FLOAT', len(palette) * 4, pal_flat))

    shader = _build_shader()
    off = gpu.types.GPUOffScreen(w, h, format='RGBA32F')
    batch = batch_for_shader(
        shader, 'TRI_FAN',
        {"pos": [(-1, -1), (1, -1), (1, 1), (-1, 1)],
         "uv_in": [(0, 0), (1, 0), (1, 1), (0, 1)]})
    try:
        with off.bind():
            shader.bind()
            shader.uniform_sampler("img", img)
            shader.uniform_sampler("pal", pal)
            shader.uniform_int("pal_n", len(palette))
            batch.draw(shader)
            buf = off.texture_color.read()
        return np.array(buf, dtype='float32').reshape(-1).tolist()
    finally:
        off.free()
