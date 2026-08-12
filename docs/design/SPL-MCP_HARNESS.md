---
created: 2026-08-10
branch: feat/spl-mcp-depth
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# SPL-MCP — the native MCP harness (depth)

Splendor is an MCP **server** (external agents drive the scene through it) and **client**
(it reaches other MCP servers). Every `tools/call` runs through the single governed path
`splendor.action_api.execute`, so an external agent hits the *same* HIC gate an in-app action
does (invariant I-1). No tool is a bypass.

## Surface
- **Governed tools** (build a typed intent → the gate → act): `set_palette`, `snap_vertices`,
  `flat_shade`. A blocked verdict returns `isError` + the rule code, so the agent learns it needs
  approval.
- **Read-only tools** (no gate, never mutate): `get_state` (HIC level, palette, run + eval state),
  `eval_run` (score a subject with the Eval SDK — real feedback).
- **Resources** (`resources/list` / `resources/read`): `splendor://state`, `splendor://tools`,
  `splendor://eval` — context an agent reads, not just acts on.

## Transport — connecting a real client (Claude Code, Cursor, llama.cpp agents)
The server runs inside Blender over a local TCP socket (Blender's stdout logging can't corrupt the
JSON-RPC stream). Real clients speak stdio, so a pure-Python **bridge** links them:

```bash
# 1) start the server inside Blender (writes its port to a file):
SPLENDOR_REPO=$PWD SPLENDOR_MCP_GRANT=budgeted:geometry,scene_config \
  blender --background --factory-startup \
  --python scripts/modules/splendor_mcp/_run_in_blender.py -- --port-file /tmp/spl.port

# 2) emit a Claude Code / Cursor stanza (or hand-write .mcp.json):
PYTHONPATH=scripts/modules python -m splendor_mcp config --port "$(cat /tmp/spl.port)"
```

The stanza runs `python -m splendor_mcp bridge --port <p>` (stdio↔TCP). The **session grant**
comes from `SPLENDOR_MCP_GRANT` (`level:cls1,cls2`); **default is no grant** — external agents are
ungoverned by default, so their acts require HIC-1 approval. Safe by default, on purpose.

## Verified
`test_spl_mcp_depth.py` (real Blender subprocess): the deepened tool list; `flat_shade` governed +
faceted; `get_state` / `eval_run` read-only; `resources/list` + `read`; and the stdio bridge
relaying `initialize` + `tools/list` (a notification correctly gets no reply). `test_s0_4` still
proves the no-grant negative control (an external call → `require-approval`, scene unchanged).

## Persistent in-GUI server — DONE

A *running* Blender can serve external agents live. `splendor_mcp.threaded.ThreadedMCPServer`
runs socket accept/read/write on background threads, but **marshals every JSON-RPC message to
the main thread** — a `bpy.app.timers` callback drains a queue and runs `MCPServer.handle` (the
governed path) there; the socket thread blocks on a per-request `Event` until answered. So a
`tools/call` that mutates bpy runs on the main thread (never crashes on a worker thread).

- In the product: **Start / Stop MCP Server** (the *MCP Server (live)* panel). The session
  autonomy is the **scene HIC level** — the Control Bar governs external agents exactly as it
  governs in-app actions; `Ungoverned` grants no session grant, so external acts require approval.
- Real clients still connect via `python -m splendor_mcp bridge --port <p>`.

Verified (`test_spl_mcp_persistent.py`): a background-thread client's `tools/call` (`flat_shade`)
executes + facets on the main thread via the pump; `get_state` / `resources/read` marshal too; the
timer registers/unregisters; the Start/Stop operators wire it and report the port.

## Still open (honest)
- HTTP-SSE transport alongside the stdio bridge.
