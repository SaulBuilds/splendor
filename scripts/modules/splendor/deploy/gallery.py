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


def render_index(entries, title: str = "Splendor Gallery") -> str:
    """A self-contained index page — a grid of pieces, each linking to its own page.

    ``entries`` is a list of dicts: ``{title, thumb_png, href, subtitle, cid}``. Thumbnails
    are embedded as ``data:`` URIs; links go to each piece's pinned page. No external
    requests (CSP-safe / IPFS-servable). Untrusted text is escaped; ``href`` is emitted only
    if it is an ``ipfs:`` / relative link or a gateway ``/ipfs/`` path (never arbitrary http).
    """
    cards = []
    for e in entries:
        thumb = (f'<img alt="" src="{_data_uri(e.get("thumb_png", b""), e.get("image_mime", "image/png"))}">'
                 if e.get("thumb_png") else '<div class="noimg">◻</div>')
        href = _safe_href(e.get("href", ""))
        cid = html.escape(e.get("cid", ""))
        card = (f'<figure>{thumb}<figcaption><b>{html.escape(e.get("title", "untitled"))}</b>'
                f'<span>{html.escape(e.get("subtitle", ""))}</span>'
                f'<code>{cid[:24]}</code></figcaption></figure>')
        cards.append(f'<a class="card" href="{href}">{card}</a>' if href else f'<div class="card">{card}</div>')
    grid = "".join(cards) or '<p class="empty">No pieces yet.</p>'
    t = html.escape(title)
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        f"<title>{t} · Splendor</title><style>"
        "*{box-sizing:border-box}"
        "body{margin:0;background:#0b0b0c;color:#e8e8e6;font:15px/1.5 ui-monospace,Menlo,Consolas,monospace}"
        ".wrap{max-width:1000px;margin:0 auto;padding:32px 20px}"
        f"h1{{font-size:20px;letter-spacing:.04em;margin:0 0 4px;color:{_GREEN}}}"
        ".sub{color:#8a8a86;margin:0 0 24px;font-size:12px;text-transform:uppercase;letter-spacing:.12em}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:16px}"
        ".card{display:block;text-decoration:none;color:inherit;border:1px solid #1c1c1e;background:#0f0f11}"
        f".card:hover{{border-color:{_GREEN}}}"
        ".card figure{margin:0}"
        ".card img,.noimg{width:100%;aspect-ratio:4/3;object-fit:cover;image-rendering:pixelated;"
        "background:#000;display:flex;align-items:center;justify-content:center;color:#333;font-size:32px}"
        "figcaption{padding:10px 12px;display:flex;flex-direction:column;gap:2px}"
        "figcaption b{font-size:13px}figcaption span{color:#8a8a86;font-size:11px}"
        f"figcaption code{{color:{_GREEN};font-size:10px;opacity:.8}}"
        ".empty{color:#666}"
        f"footer{{margin-top:28px;color:#5a5a56;font-size:11px;border-top:1px solid #1c1c1e;padding-top:12px}}"
        f"footer b{{color:{_GREEN}}}"
        "</style></head><body><div class=\"wrap\">"
        f"<h1>{t}</h1><p class=\"sub\">Splendor · PS1 retro · {len(entries)} piece(s) · content-addressed</p>"
        f"<div class=\"grid\">{grid}</div>"
        "<footer>Published with <b>Splendor</b> · self-contained · each piece + this index pinned to IPFS</footer>"
        "</div></body></html>"
    )


def _safe_href(href: str) -> str:
    """Allow only ipfs:, relative, or gateway /ipfs/ links — never arbitrary schemes."""
    if not href:
        return ""
    low = href.lower()
    if low.startswith("ipfs://") or href.startswith("/ipfs/") or "/ipfs/" in href and low.startswith("http"):
        return html.escape(href, quote=True)
    if href.startswith("./") or href.startswith("../") or href.startswith("#"):
        return html.escape(href, quote=True)
    return ""


def publish_gallery(items, pinning, title: str = "Splendor Gallery"):
    """Pin each item's page, then pin an index linking them all.

    Returns ``{"index": (PinRef, url), "items": [(item, PinRef, url), ...]}``. Raises
    PinUnavailable honestly if the backend is unreachable — never a fabricated URL.
    """
    published = []
    entries = []
    for item in items:
        ref, url = publish_item(item, pinning)
        published.append((item, ref, url))
        entries.append({
            "title": item.title, "thumb_png": item.image_png, "image_mime": item.image_mime,
            # Relative /ipfs/<cid> so links resolve on whatever gateway serves the index
            # (portable across gateways; not a host-specific absolute URL).
            "href": f"/ipfs/{ref.cid}", "cid": ref.cid,
            "subtitle": (f"{item.eval_score:.2f}" + (" · PASS" if item.eval_passed else "")
                         + (f" · pal {item.palette}" if item.palette else "")),
        })
    index_bytes = render_index(entries, title=title).encode("utf-8")
    index_ref = pinning.pin(index_bytes)
    return {"index": (index_ref, gateway_url(pinning, index_ref.cid)), "items": published}
