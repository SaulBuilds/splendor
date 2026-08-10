# SPDX-License-Identifier: GPL-2.0-or-later
"""Splendor MCP CLI — a stdio↔TCP bridge and a Claude Code config emitter.

Real MCP clients (Claude Code, Cursor, llama.cpp agents) speak MCP over **stdio**.
The Splendor server runs inside Blender over a TCP socket (so Blender's own stdout
logging can't corrupt the stream). This bridge is the missing link: a pure-Python
(no bpy) stdio front end that forwards JSON-RPC lines to that TCP server, so an
external client launches ``python -m splendor_mcp bridge --port <p>`` and talks to a
running Blender instance natively.

    # 1) start the server inside Blender (writes its port):
    blender --background --factory-startup \
        --python scripts/modules/splendor_mcp/_run_in_blender.py -- --port-file /tmp/spl.port
    # 2) point a client at the bridge:
    python -m splendor_mcp bridge --port $(cat /tmp/spl.port)
    # or emit a Claude Code stanza:
    python -m splendor_mcp config --port $(cat /tmp/spl.port)

Notifications (no ``id``) are forwarded without awaiting a reply — matching the
server, which returns nothing for them. One request → one response line.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys


def bridge(host: str, port: int, stdin=None, stdout=None) -> int:
    """Pump newline-delimited JSON-RPC between stdio and the TCP MCP server."""
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    try:
        sock = socket.create_connection((host, port), timeout=10.0)
    except OSError as exc:
        sys.stderr.write(f"[splendor-mcp] cannot reach server at {host}:{port}: {exc}\n")
        return 2
    reader = sock.makefile("rb")
    writer = sock.makefile("wb")
    try:
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            writer.write((json.dumps(msg) + "\n").encode())
            writer.flush()
            if msg.get("id") is None:
                continue  # notification — the server sends no reply
            resp = reader.readline()
            if not resp:
                break
            stdout.write(resp.decode())
            stdout.flush()
    finally:
        for c in (writer, reader, sock):
            try:
                c.close()
            except OSError:
                pass
    return 0


def config_stanza(host: str, port: int, name: str = "splendor") -> dict:
    """A Claude Code / Cursor ``.mcp.json`` stanza pointing at the bridge."""
    return {"mcpServers": {name: {
        "command": sys.executable or "python3",
        "args": ["-m", "splendor_mcp", "bridge", "--host", host, "--port", str(port)],
    }}}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="splendor_mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bridge", help="stdio↔TCP bridge to a running Blender MCP server")
    b.add_argument("--host", default="127.0.0.1")
    b.add_argument("--port", type=int, required=True)
    c = sub.add_parser("config", help="print a Claude Code MCP stanza for the bridge")
    c.add_argument("--host", default="127.0.0.1")
    c.add_argument("--port", type=int, required=True)
    c.add_argument("--name", default="splendor")
    args = parser.parse_args(argv)
    if args.cmd == "bridge":
        return bridge(args.host, args.port)
    if args.cmd == "config":
        print(json.dumps(config_stanza(args.host, args.port, args.name), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
