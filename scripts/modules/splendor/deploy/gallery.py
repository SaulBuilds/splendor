# SPDX-License-Identifier: GPL-2.0-or-later
"""The web gallery substrate (P7) — publish a finished piece to a self-contained page.

The last pillar: a creator's work goes to the internet as a **single, self-contained
HTML page** (inline CSS, the image embedded as a `data:` URI — no external requests,
so it's CSP-safe and servable straight from IPFS). The page shows the **provenance**
that ties the other pillars together: prompt, eval score, palette, workflow, the pinned
asset CID, and any on-chain attestation. Content-addressed, so the page *is* its own
identity.

Pure Python (no bpy): builds + hashes the page and, given a pinning backend, publishes
it. Deterministic — the same item yields byte-identical HTML and the same CID.
"""
from __future__ import annotations

import base64
import html
from dataclasses import dataclass, field

from .pinning import content_address

_GREEN = "#8ecc09"  # Citrate accent (green replaces blue), from the SPL-S1 mock.


@dataclass
class GalleryItem:
    title: str
    prompt: str = ""
    image_png: bytes = b""
    image_mime: str = "image/png"
    eval_score: float = 0.0
    eval_passed: bool = False
    palette: int = 0
    tris: int = 0
    workflow: str = ""
    asset_cid: str = ""       # the pinned asset CID (P7), if any
    attestation: str = ""     # on-chain tx hash / provenance digest, if any
    created: str = ""         # ISO-8601 string, supplied by the caller (kept deterministic)
    extra: dict = field(default_factory=dict)


def _data_uri(data: bytes, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


def _row(label: str, value: str) -> str:
    if not value:
        return ""
    return f'<tr><th>{html.escape(label)}</th><td>{html.escape(value)}</td></tr>'


def render_item_page(item: GalleryItem) -> str:
    """A self-contained retro/Citrate HTML page for one piece. No external resources."""
    img = (f'<img alt="{html.escape(item.title)}" src="{_data_uri(item.image_png, item.image_mime)}">'
           if item.image_png else '<div class="noimg">no image</div>')
    score = f"{item.eval_score:.2f}" + (" · PASS" if item.eval_passed else " · —")
    rows = "".join([
        _row("prompt", item.prompt),
        _row("eval", score),
        _row("palette", str(item.palette) if item.palette else ""),
        _row("tris", str(item.tris) if item.tris else ""),
        _row("workflow", item.workflow),
        _row("asset CID", item.asset_cid),
        _row("attestation", item.attestation),
        _row("created", item.created),
    ] + [_row(k, str(v)) for k, v in item.extra.items()])
    title = html.escape(item.title or "Splendor piece")
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{title} · Splendor</title><style>"
        "*{box-sizing:border-box}"
        f"body{{margin:0;background:#0b0b0c;color:#e8e8e6;font:15px/1.5 ui-monospace,Menlo,Consolas,monospace}}"
        ".wrap{max-width:860px;margin:0 auto;padding:32px 20px}"
        f"h1{{font-size:20px;letter-spacing:.04em;margin:0 0 4px;color:{_GREEN}}}"
        ".sub{color:#8a8a86;margin:0 0 24px;font-size:12px;text-transform:uppercase;letter-spacing:.12em}"
        "figure{margin:0 0 24px}"
        "img{width:100%;height:auto;image-rendering:pixelated;border:1px solid #222;"
        "background:#000;display:block}"
        ".noimg{padding:60px;text-align:center;color:#666;border:1px dashed #333}"
        "table{width:100%;border-collapse:collapse;font-size:13px}"
        "th,td{text-align:left;padding:8px 10px;border-bottom:1px solid #1c1c1e;vertical-align:top}"
        "th{color:#8a8a86;font-weight:600;width:140px;text-transform:uppercase;letter-spacing:.08em;font-size:11px}"
        "td{word-break:break-word}"
        f"footer{{margin-top:28px;color:#5a5a56;font-size:11px;border-top:1px solid #1c1c1e;padding-top:12px}}"
        f"footer b{{color:{_GREEN}}}"
        "</style></head><body><div class=\"wrap\">"
        f"<h1>{title}</h1><p class=\"sub\">Splendor · PS1 retro · provenance-carried</p>"
        f"<figure>{img}</figure>"
        f"<table>{rows}</table>"
        "<footer>Published with <b>Splendor</b> · self-contained · content-addressed · "
        "export FREE · protocol fees fund stewardship</footer>"
        "</div></body></html>"
    )


def page_cid(item: GalleryItem) -> str:
    """The content address (sha256) of the item's page — deterministic identity."""
    return content_address(render_item_page(item).encode("utf-8"))


def gateway_url(pinning, cid: str) -> str:
    base = getattr(pinning, "gateway_url", "").rstrip("/")
    return f"{base}/ipfs/{cid}" if base else f"ipfs://{cid}"


def publish_item(item: GalleryItem, pinning):
    """Render + pin the page. Returns ``(PinRef, url)``; raises PinUnavailable honestly
    if the pinning backend is unreachable — never a fabricated URL."""
    html_bytes = render_item_page(item).encode("utf-8")
    ref = pinning.pin(html_bytes)
    return ref, gateway_url(pinning, ref.cid)
