# SPDX-License-Identifier: GPL-2.0-or-later
"""A tiny content-addressed pinning server fixture (stands in for Citrate pinning).
`POST /pin` stores bytes under sha256 and returns the cid; `GET /pin/<cid>` returns
them. In ``tamper=True`` mode it corrupts the first byte on retrieval, to drive the
integrity negative control. Runs in a daemon thread.
"""
import hashlib
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _cid(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _make_handler(store, tamper):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, data: bytes, code=200):
            self.send_response(code)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if self.path.rstrip("/").endswith("/pin"):
                n = int(self.headers.get("Content-Length", 0))
                data = self.rfile.read(n)
                cid = _cid(data)
                store[cid] = data
                self._send(json.dumps({"cid": cid}).encode())
            else:
                self._send(b"", 404)

        def do_GET(self):
            parts = self.path.strip("/").split("/", 1)
            if len(parts) == 2 and parts[0] == "pin":
                data = store.get(parts[1])
                if data is None:
                    self._send(b"", 404)
                    return
                if tamper and data:
                    data = bytes([data[0] ^ 0xFF]) + data[1:]   # corrupt on retrieval
                self._send(data)
            else:
                self._send(b"", 404)

    return Handler


def start(tamper=False):
    store = {}
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler(store, tamper))
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port, store
