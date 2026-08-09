# SPDX-License-Identifier: GPL-2.0-or-later
"""S0.4 acceptance test — MCP server + client, same governed path as in-app.

Run with SYSTEM python3 (the client needs no bpy); it spawns the Splendor MCP
server inside a real Blender subprocess:

    python3 tests/splendor/test_s0_4_mcp_server.py

Exits non-zero on any failure. Negative control (mock-forbidding): an MCP
``tools/call`` with no grant returns ``require-approval`` and leaves the scene
unchanged — identical governance to an in-app action, not a bypass.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))
sys.path.insert(0, os.path.dirname(__file__))

from splendor_mcp.client import MCPClient  # noqa: E402
import _echo_mcp_server  # noqa: E402

BLENDER = os.environ.get("SPLENDOR_BLENDER", "/home/saul/Projects/build_linux/bin/blender")
RUN = os.path.join(_REPO, "scripts", "modules", "splendor_mcp", "_run_in_blender.py")

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def start_server(grant=None, timeout=120):
    pf = tempfile.mktemp(suffix=".port")
    env = dict(os.environ)
    env["SPLENDOR_REPO"] = _REPO
    if grant:
        env["SPLENDOR_MCP_GRANT"] = grant
    else:
        env.pop("SPLENDOR_MCP_GRANT", None)
    proc = subprocess.Popen(
        [BLENDER, "--background", "--factory-startup", "--python", RUN, "--", "--port-file", pf],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if os.path.exists(pf):
            txt = open(pf).read().strip()
            if txt:
                return proc, int(txt)
        if proc.poll() is not None:
            raise RuntimeError(f"MCP server exited early (rc={proc.returncode})")
        time.sleep(0.3)
    proc.kill()
    raise RuntimeError("MCP server never reported a port")


def payload(resp):
    return json.loads(resp["result"]["content"][0]["text"])


def stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except Exception:
        proc.kill()


def test_no_grant_requires_approval():
    print("[1] MCP tools/call WITHOUT a grant -> require-approval (same gate as in-app)")
    proc, port = start_server(grant=None)
    try:
        c = MCPClient.connect(port=port)
        init = c.initialize()
        check(init["result"]["serverInfo"]["name"] == "splendor-mcp", "initialize handshake")
        tools = [t["name"] for t in c.list_tools()["result"]["tools"]]
        check("set_palette" in tools and "snap_vertices" in tools, f"tools/list exposes governed tools {tools}")
        pl = payload(c.call_tool("set_palette", {"colors": 8}))
        check(pl["verdict"] == "require-approval" and pl["rule_code"] == "RC-SPL-001",
              "no grant -> require-approval (RC-SPL-001)")
        check(pl["executed"] is False and pl["verify"]["palette_size"] == 16,
              "NOT executed; scene unchanged (palette stays default 16)")
        c.close()
    finally:
        stop(proc)


def test_with_grant_executes():
    print("[2] MCP tools/call WITH a budgeted grant -> executed + real scene change")
    proc, port = start_server(grant="budgeted:scene_config,geometry")
    try:
        c = MCPClient.connect(port=port)
        c.initialize()
        pl = payload(c.call_tool("set_palette", {"colors": 8}))
        check(pl["executed"] and pl["verdict"] == "proceed", "executed with PROCEED")
        check(pl["verify"]["palette_size"] == 8, "scene palette actually set to 8 (verified read-back)")
        pl2 = payload(c.call_tool("snap_vertices", {"grid": 0.1}))
        check(pl2["executed"] and pl2["verify"]["aligned"], "snap_vertices executed; geometry on-grid")
        pl3 = payload(c.call_tool("set_palette", {"colors": 999}))
        check(not pl3["executed"] and pl3["rule_code"] == "RC-SPL-000", "invalid args -> deny (RC-SPL-000)")
        c.close()
    finally:
        stop(proc)


def test_client_consumes_external_server():
    print("[3] Splendor MCP client consumes an EXTERNAL (non-Splendor) MCP server")
    eport = _echo_mcp_server.start()
    c = MCPClient.connect(port=eport)
    init = c.initialize()
    check(init["result"]["serverInfo"]["name"] == "echo-mcp", "connected to external echo server")
    etools = [t["name"] for t in c.list_tools()["result"]["tools"]]
    check("echo" in etools, f"external tools/list {etools}")
    er = c.call_tool("echo", {"text": "splendor"})
    check(er["result"]["content"][0]["text"] == "splendor", "external tool call round-trips")
    c.close()


def main():
    for t in (test_no_grant_requires_approval, test_with_grant_executes,
              test_client_consumes_external_server):
        t()
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — S0.4 MCP server + client verified (same governed path as in-app)")
    sys.exit(0)


if __name__ == "__main__":
    main()
