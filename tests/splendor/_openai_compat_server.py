# SPDX-License-Identifier: GPL-2.0-or-later
"""A tiny real HTTP server speaking the OpenAI `/v1` shape — a stand-in for a
local llama.cpp / Ollama server (identical protocol). The backend adapter makes
real HTTP calls to it; only the model output is canned. Runs in a daemon thread.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _make_handler(reply):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.rstrip("/").endswith("/models"):
                self._json({"object": "list", "data": [{"id": "fixture-model", "object": "model"}]})
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            self._json({
                "id": "cmpl-fixture", "object": "chat.completion",
                "model": req.get("model", "fixture-model"),
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": reply}}],
            })

    return Handler


def start(reply="PLAN: box → snap grid 0.1 → palette 16"):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(reply))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port
