# SPDX-License-Identifier: GPL-2.0-or-later
"""A persistent, in-GUI Splendor MCP server — threaded I/O, main-thread bpy.

The `--background` server (`serve_socket`) runs the whole protocol on the calling
thread — fine when there's no GUI loop competing. A *running* Blender is different:
bpy is single-threaded and may only be touched from the main thread. So here the
socket accept/read/write runs on a **background thread**, while every JSON-RPC message
is **marshalled to the main thread** — a `bpy.app.timers` callback drains a queue and
runs `MCPServer.handle` (which is what actually calls the governed action API) there.
The socket thread blocks on a per-request `Event` until the main thread has answered.

`start()` binds + registers the timer + starts the accept thread. `stop()` unwinds
cleanly. `pump()` is the main-thread step — the timer calls it; tests call it directly
(so the marshalling contract is verifiable without a live GUI event loop).
"""
from __future__ import annotations

import json
import queue
import socket
import threading

from .server import MCPServer, grant_from_env


class ThreadedMCPServer:
    def __init__(self, host="127.0.0.1", port=0, principal="mcp:external", grant=None, timeout=5.0):
        self._srv = MCPServer(principal, grant)
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock = None
        self._accept_thread = None
        self._conn_threads = []
        self._req_q: "queue.Queue" = queue.Queue()
        self._running = False
        self.bound_port = None
        # Bind the timer callback ONCE — bpy.app.timers identifies callbacks by object,
        # and a fresh `self.pump` bound method each access would defeat is_registered/unregister.
        self._pump_cb = self.pump

    # ── main-thread side ────────────────────────────────────────────────────────
    def pump(self):
        """Drain queued requests and handle them HERE (the main/bpy thread)."""
        while True:
            try:
                msg, holder, event = self._req_q.get_nowait()
            except queue.Empty:
                break
            try:
                holder["resp"] = self._srv.handle(msg)
            except Exception as exc:  # never let one bad request kill the pump
                holder["resp"] = {"jsonrpc": "2.0", "id": msg.get("id"),
                                  "error": {"code": -32603, "message": f"handler error: {exc}"}}
            event.set()
        # Returning a float reschedules the bpy timer; None (when stopped) unregisters it.
        return 0.02 if self._running else None

    # ── background-thread side ──────────────────────────────────────────────────
    def _dispatch_to_main(self, msg):
        """Enqueue a message for the main thread and block until it's handled."""
        holder, event = {}, threading.Event()
        self._req_q.put((msg, holder, event))
        if not event.wait(timeout=self._timeout):
            return {"jsonrpc": "2.0", "id": msg.get("id"),
                    "error": {"code": -32000, "message": "main-thread timeout"}}
        return holder.get("resp")

    def _serve_conn(self, conn):
        reader = conn.makefile("rb")
        writer = conn.makefile("wb")
        try:
            while self._running:
                line = reader.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                resp = self._dispatch_to_main(msg)
                if resp is not None:  # notifications marshal to None → no reply
                    writer.write((json.dumps(resp) + "\n").encode())
                    writer.flush()
        finally:
            try:
                conn.close()
            except OSError:
                pass

    def _accept_loop(self):
        while self._running:
            try:
                conn, _ = self._sock.accept()
            except OSError:
                break  # socket closed by stop()
            t = threading.Thread(target=self._serve_conn, args=(conn,), daemon=True)
            t.start()
            self._conn_threads.append(t)

    # ── lifecycle ───────────────────────────────────────────────────────────────
    def start(self, register_timer=True):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self._host, self._port))
        self._sock.listen(5)
        self.bound_port = self._sock.getsockname()[1]
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        if register_timer:
            import bpy
            bpy.app.timers.register(self._pump_cb, persistent=True)
        return self.bound_port

    def timer_registered(self) -> bool:
        try:
            import bpy
            return bool(bpy.app.timers.is_registered(self._pump_cb))
        except Exception:
            return False

    def stop(self):
        self._running = False
        if self._sock is not None:
            try:
                self._sock.close()  # unblocks accept()
            except OSError:
                pass
            self._sock = None
        try:
            import bpy
            if bpy.app.timers.is_registered(self._pump_cb):
                bpy.app.timers.unregister(self._pump_cb)
        except Exception:
            pass


def start_persistent(host="127.0.0.1", port=0, grant=None, register_timer=True):
    """Convenience: build + start a persistent server. Grant defaults to the env."""
    srv = ThreadedMCPServer(host=host, port=port, grant=grant if grant is not None else grant_from_env())
    srv.start(register_timer=register_timer)
    return srv
