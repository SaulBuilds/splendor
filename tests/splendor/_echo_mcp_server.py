# SPDX-License-Identifier: GPL-2.0-or-later
"""A tiny, non-Splendor MCP server (exposes an ``echo`` tool) used to prove that
the Splendor MCP client can consume an *external* server. Pure Python; runs in a
daemon thread and returns its bound port.
"""
import json
import socket
import threading

_PROTO = "2024-11-05"


def _serve(sock):
    conn, _ = sock.accept()
    reader, writer = conn.makefile("rb"), conn.makefile("wb")

    def send(msg):
        writer.write((json.dumps(msg) + "\n").encode())
        writer.flush()

    while True:
        line = reader.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        mid, method = msg.get("id"), msg.get("method")
        params = msg.get("params") or {}
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": _PROTO, "capabilities": {"tools": {}},
                "serverInfo": {"name": "echo-mcp", "version": "0.0.1"}}})
        elif method == "notifications/initialized":
            pass
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
                {"name": "echo", "description": "echo back text",
                 "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}}}]}})
        elif method == "tools/call":
            text = (params.get("arguments") or {}).get("text", "")
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": text}], "isError": False}})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}})
    conn.close()
    sock.close()


def start():
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    port = sock.getsockname()[1]
    threading.Thread(target=_serve, args=(sock,), daemon=True).start()
    return port
