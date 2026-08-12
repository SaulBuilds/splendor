# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-MCP — the persistent, in-GUI server (threaded I/O, main-thread bpy).

    blender --background --factory-startup --python tests/splendor/test_spl_mcp_persistent.py

A running Blender can't touch bpy off the main thread. This proves the marshalling
contract: socket I/O runs on background threads, but a governed `tools/call` (which
mutates bpy) is executed on the MAIN thread via the pump — the very thing that would
crash if it ran on the socket thread. The test drives `pump()` itself (Blender's timer
loop doesn't run under `--background`), then confirms the real timer registers/unregisters.
"""
import os
import sys
import threading
import time

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.join(_REPO, "scripts", "addons_core"))

import bpy  # noqa: E402
import splendor_harness  # noqa: E402
from splendor import hic  # noqa: E402
from splendor_mcp.client import MCPClient  # noqa: E402
from splendor_mcp.threaded import ThreadedMCPServer  # noqa: E402

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def _text(resp):
    import json
    return json.loads(resp["result"]["content"][0]["text"])


def main():
    splendor_harness.register()
    # A grant so the external flat_shade call proceeds (geometry class).
    grant = hic.Grant("mcp-session", "mcp:external", hic.HicLevel.BUDGETED, frozenset({"geometry", "scene_config"}))
    srv = ThreadedMCPServer(grant=grant)
    port = srv.start(register_timer=False)  # test drives pump() itself
    results = {}
    main_thread = threading.get_ident()

    def client_seq():
        try:
            cli = MCPClient.connect(port=port)
            results["init"] = cli.initialize()
            results["tools"] = cli.list_tools()
            results["flat"] = cli.call_tool("flat_shade", {"faceted": True})
            results["state"] = cli.call_tool("get_state", {})
            results["res"] = cli.read_resource("splendor://state")
            cli.close()
        except Exception as exc:  # surface client-thread errors to the assertions
            results["error"] = repr(exc)
        results["done"] = True

    try:
        print("[1] Socket I/O on a background thread; bpy marshalled to the main thread")
        t = threading.Thread(target=client_seq, daemon=True)
        t.start()
        # The main thread IS the bpy thread here — pump until the client finishes.
        deadline = time.time() + 20
        pumped = 0
        while not results.get("done") and time.time() < deadline:
            srv.pump()
            pumped += 1
            time.sleep(0.005)
        t.join(timeout=5)

        check(not results.get("error"), f"client sequence completed without error ({results.get('error')})")
        check(results.get("init", {}).get("result", {}).get("serverInfo", {}).get("name") == "splendor-mcp",
              "initialize answered over the threaded server")
        names = {x["name"] for x in results.get("tools", {}).get("result", {}).get("tools", [])}
        check("flat_shade" in names and "get_state" in names, "tools/list served")

        flat = _text(results["flat"])
        check(flat["executed"] and flat["verify"]["faceted"],
              "flat_shade EXECUTED on the main thread + faceted (bpy mutation marshalled, not crashed)")
        st = _text(results["state"])
        check(st["palette_size"] >= 1, f"get_state read scene context via the pump (palette {st['palette_size']})")
        blob = results["res"]["result"]["contents"][0]["text"]
        check("palette_size" in blob, "resources/read marshalled through the main thread")
        check(pumped > 0, "the main-thread pump actually did the work")
    finally:
        srv.stop()

    print("[2] The real bpy.app.timers path registers + unregisters cleanly")
    srv2 = ThreadedMCPServer(grant=grant)
    srv2.start(register_timer=True)
    try:
        check(srv2.timer_registered(), "pump registered as a bpy timer (fires on the GUI loop)")
    finally:
        srv2.stop()
    check(not srv2.timer_registered(), "stop() unregistered the timer")

    print("[3] The in-GUI start/stop operators wire the server + report the port")
    from splendor_harness import mcp_server
    bpy.ops.splendor.mcp_start('EXEC_DEFAULT')
    check(mcp_server.is_running() and bpy.context.scene.splendor_mcp_port > 0,
          f"Start MCP Server → serving on :{bpy.context.scene.splendor_mcp_port}")
    bpy.ops.splendor.mcp_stop('EXEC_DEFAULT')
    check(not mcp_server.is_running() and bpy.context.scene.splendor_mcp_port == 0,
          "Stop MCP Server → stopped, port cleared")

    splendor_harness.unregister()

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — persistent in-GUI MCP server verified (threaded I/O, main-thread bpy)")
    sys.exit(0)


if __name__ == "__main__":
    main()
