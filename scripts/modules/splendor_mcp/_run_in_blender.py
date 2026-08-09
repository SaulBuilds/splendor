# SPDX-License-Identifier: GPL-2.0-or-later
"""Launch the Splendor MCP server inside Blender.

    blender --background --factory-startup \
        --python scripts/modules/splendor_mcp/_run_in_blender.py -- --port-file /tmp/p

Inserts the source ``scripts`` paths (until the module is bundled into the built
``bin/5.3/scripts`` by a ``make`` re-sync), registers the harness (for the scene
state), reads the session grant from ``SPLENDOR_MCP_GRANT``, and serves one MCP
client over a socket whose port is written to ``--port-file``.
"""
import os
import sys

_REPO = os.environ.get("SPLENDOR_REPO", os.getcwd())
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import splendor_harness  # noqa: E402
from splendor_mcp import server  # noqa: E402


def _arg(name):
    argv = sys.argv
    if "--" in argv:
        extra = argv[argv.index("--") + 1:]
        for i, tok in enumerate(extra):
            if tok == name and i + 1 < len(extra):
                return extra[i + 1]
    return None


def main():
    splendor_harness.register()  # registers Scene.splendor_palette_size + operators
    grant = server.grant_from_env()
    print(f"[splendor-mcp] serving; grant={grant}", file=sys.stderr)
    server.serve_socket(port_file=_arg("--port-file"), grant=grant)


if __name__ == "__main__":
    main()
