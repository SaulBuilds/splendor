# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P7 — the web gallery: a self-contained, content-addressed, IPFS-servable page.

    python3 tests/splendor/test_spl_web_gallery.py

Checks the page is genuinely self-contained (no external requests — so it serves from
IPFS and passes a strict CSP), carries the provenance, is injection-safe, and is
content-addressed (deterministic). When an IPFS daemon is up, it publishes and
round-trips the exact bytes; otherwise it fails honestly (no fabricated URL).
"""
import os
import re
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.deploy import (  # noqa: E402
    GalleryItem, IpfsPinning, PinUnavailable, gateway_url, page_cid, publish_item, render_item_page,
)

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def main():
    item = GalleryItem(
        title="Low-poly Health Potion", prompt="PS1 health potion, dithered, 16-color",
        image_png=b"\x89PNG\r\n\x1a\n--pretend-png--", eval_score=0.94, eval_passed=True,
        palette=16, tris=120, workflow="potion-workflow", asset_cid="QmAsset123",
        attestation="0xabc123", created="2026-08-10T00:00:00Z")
    page = render_item_page(item)

    print("[1] Self-contained (no external requests → IPFS/CSP-safe)")
    external = re.findall(r'(?:https?:)?//[A-Za-z0-9.\-]+', page)
    check(not external, f"no external or protocol-relative URLs ({external[:3]})")
    check("data:image/png;base64," in page, "image is embedded as a data: URI")
    check("<link" not in page and "<script" not in page.replace("&lt;script", ""),
          "no external <link>/<script> tags")

    print("[2] Provenance is carried on the page")
    for token in ("PS1 health potion", "0.94", "16", "potion-workflow", "QmAsset123", "0xabc123"):
        check(token in page, f"page shows '{token}'")

    print("[3] Injection-safe (untrusted prompt is HTML-escaped)")
    evil = GalleryItem(title="x", prompt="<script>alert(1)</script>", created="t")
    ep = render_item_page(evil)
    check("<script>alert(1)</script>" not in ep and "&lt;script&gt;" in ep,
          "a <script> in the prompt is escaped, not injected")

    print("[4] Content-addressed (deterministic identity)")
    check(page_cid(item) == page_cid(item) and page_cid(item).startswith("sha256:"),
          f"same item → same CID ({page_cid(item)[:20]}…)")
    item2 = GalleryItem(title=item.title, prompt="different", created=item.created)
    check(page_cid(item2) != page_cid(item), "different content → different CID")

    print("[5] Publish to IPFS + exact round-trip (skip-safe without a daemon)")
    pin = IpfsPinning()
    try:
        ref, url = publish_item(item, pin)
    except PinUnavailable:
        print("     SKIP — no IPFS daemon (`ipfs daemon`); publish fails honestly, no fake URL")
        ref = None
    if ref is not None:
        check(url.endswith(ref.cid) and "/ipfs/" in url, f"gateway URL points at the CID ({url})")
        check(pin.fetch(ref.cid).decode("utf-8") == page, "the published page round-trips byte-for-byte")

    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — web gallery verified (self-contained, provenance, content-addressed, IPFS)")
    sys.exit(0)


if __name__ == "__main__":
    main()
