# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-MCP depth — expanded tools, MCP resources, and the stdio bridge.

    python3 tests/splendor/test_spl_mcp_depth.py

Runs the Splendor MCP server inside a real Blender subprocess and checks the deeper
surface: the new tools (flat_shade governed; get_state / eval_run read-only), the
resources protocol (list + read), and the pure-Python stdio↔TCP bridge that real MCP
clients (Claude Code, …) use — all over the same governed server.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor_mcp.client import MCPClient  # noqa: E402

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
        if os.path.exists(pf) and open(pf).read().strip():
            return proc, int(open(pf).read().strip())
        if proc.poll() is not None:
            raise RuntimeError(f"MCP server exited early (rc={proc.returncode})")
        time.sleep(0.3)
    proc.kill()
    raise RuntimeError("MCP server never reported a port")


def _text(resp):
    return json.loads(resp["result"]["content"][0]["text"])


def main():
    print("[1] Expanded tools + resources over the governed server")
    proc, port = start_server(grant="budgeted:geometry,scene_config")
    try:
        cli = MCPClient.connect(port=port)
        init = cli.initialize()
        caps = init["result"]["capabilities"]
        check("resources" in caps and "tools" in caps, "initialize advertises tools + resources")

        names = {t["name"] for t in cli.list_tools()["result"]["tools"]}
        check({"set_palette", "snap_vertices", "flat_shade", "get_state", "eval_run"} <= names,
              f"tools/list has the deepened surface ({sorted(names)})")

        # flat_shade — governed, executes under the grant, and really facets.
        r = cli.call_tool("flat_shade", {"faceted": True})
        payload = _text(r)
        check(payload["executed"] and payload["verify"]["faceted"],
              "flat_shade governed → executed + faceted (verified read-back)")

        # get_state — read-only, no gate, returns real scene context.
        st = _text(cli.call_tool("get_state", {}))
        check(st["palette_size"] >= 1 and "run_state" in st, f"get_state reads scene context (palette {st['palette_size']})")

        # eval_run — read-only Eval SDK feedback.
        ev = _text(cli.call_tool("eval_run", {"tri_count": 100, "palette_colors": 8,
                                              "tri_budget": 500, "palette_limit": 16}))
        check(ev["passed_all"] is True and ev["digest"].startswith("sha256:"),
              f"eval_run scores via the Eval SDK (agg {ev['aggregate']:.2f})")

        # resources/list + read.
        res = cli.list_resources()["result"]["resources"]
        uris = {r["uri"] for r in res}
        check({"splendor://state", "splendor://tools", "splendor://eval"} <= uris, f"resources/list ({sorted(uris)})")
        blob = cli.read_resource("splendor://state")["result"]["contents"][0]["text"]
        check("palette_size" in json.loads(blob), "resources/read splendor://state returns JSON state")
        cli.close()
    finally:
        proc.wait(timeout=10)

    print("[2] The stdio↔TCP bridge (what a real MCP client launches)")
    proc2, port2 = start_server(grant="budgeted:geometry,scene_config")
    try:
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},  # notification: no reply
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = os.path.join(_REPO, "scripts", "modules") + os.pathsep + env.get("PYTHONPATH", "")
        out = subprocess.run(
            [sys.executable, "-m", "splendor_mcp", "bridge", "--port", str(port2)],
            input="\n".join(json.dumps(m) for m in msgs) + "\n",
            capture_output=True, text=True, env=env, timeout=30)
        lines = [json.loads(x) for x in out.stdout.strip().splitlines() if x.strip()]
        check(len(lines) == 2, f"bridge returned exactly 2 responses (notification got none) — {len(lines)}")
        by_id = {m.get("id"): m for m in lines}
        check(by_id.get(1, {}).get("result", {}).get("serverInfo", {}).get("name") == "splendor-mcp",
              "bridge relayed the initialize response")
        tool_names = {t["name"] for t in by_id.get(2, {}).get("result", {}).get("tools", [])}
        check("flat_shade" in tool_names, "bridge relayed tools/list through stdio")
    finally:
        proc2.wait(timeout=10)

    print("[3] The Claude Code config stanza is emitted")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(_REPO, "scripts", "modules") + os.pathsep + env.get("PYTHONPATH", "")
    cfg = subprocess.run([sys.executable, "-m", "splendor_mcp", "config", "--port", "5599"],
                         capture_output=True, text=True, env=env, timeout=20)
    stanza = json.loads(cfg.stdout)
    check("splendor" in stanza["mcpServers"] and "bridge" in stanza["mcpServers"]["splendor"]["args"],
          "config emits an mcpServers.splendor bridge stanza")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — MCP depth verified (tools + resources + stdio bridge, all governed)")
    sys.exit(0)


if __name__ == "__main__":
    main()
