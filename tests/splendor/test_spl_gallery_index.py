# SPDX-License-Identifier: GPL-2.0-or-later
"""SPL-P7 — the multi-piece gallery index.

    python3 tests/splendor/test_spl_gallery_index.py

An index is a self-contained page (thumbnails embedded, links relative) that ties N
pieces together — each pinned separately, the index pinned last and referencing them
all. Portable: links are ``/ipfs/<cid>`` so they resolve on whatever gateway serves the
index. Injection-safe hrefs. Live IPFS publish is round-tripped when a daemon is up.
"""
import os
import re
import sys

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
sys.path.insert(0, os.path.join(_REPO, "scripts", "modules"))

from splendor.deploy import (  # noqa: E402
    GalleryItem, IpfsPinning, PinUnavailable, publish_gallery, render_index,
)

_FAIL = []


def check(cond, label):
    print(("  PASS " if cond else "  FAIL ") + label)
    if not cond:
        _FAIL.append(label)


def _no_external(page):
    # External = absolute http(s) or protocol-relative src/href. ipfs:// and /ipfs/ are fine.
    return not re.search(r'(?:src|href)\s*=\s*"(?:https?:)?//', page)


def main():
    items = [
        GalleryItem(title="Health Potion", prompt="PS1 potion", image_png=b"\x89PNG-a",
                    eval_score=0.94, eval_passed=True, palette=16),
        GalleryItem(title="Rusty Sword", prompt="low-poly sword", image_png=b"\x89PNG-b",
                    eval_score=0.88, eval_passed=True, palette=8),
    ]

    print("[1] render_index is self-contained + lists every piece")
    entries = [{"title": it.title, "thumb_png": it.image_png, "href": f"/ipfs/Qm{i}",
                "cid": f"Qm{i}", "subtitle": f"{it.eval_score:.2f}"} for i, it in enumerate(items)]
    idx = render_index(entries, title="My Retro Set")
    check(_no_external(idx), "no external/absolute http resources (data URIs + relative links only)")
    check(idx.count("data:image/png;base64,") == 2, "every thumbnail embedded as a data: URI")
    check(idx.count('href="/ipfs/Qm') == 2, "every piece links via a relative /ipfs/ path")
    for it in items:
        check(it.title in idx, f"index lists '{it.title}'")

    print("[2] Injection-safe: dangerous hrefs + titles are neutralised")
    evil = render_index([{"title": "<script>x</script>", "href": "javascript:alert(1)", "thumb_png": b""}])
    check("javascript:" not in evil, "javascript: href dropped")
    check("<script>x</script>" not in evil and "&lt;script&gt;" in evil, "title escaped")

    print("[3] Publish N pieces + an index that references them all (skip-safe)")
    pin = IpfsPinning()
    try:
        out = publish_gallery(items, pin, title="My Retro Set")
    except PinUnavailable:
        print("     SKIP — no IPFS daemon; publish fails honestly, no fake URLs")
        return _finish()
    index_ref, index_url = out["index"]
    published = out["items"]
    check(len(published) == 2, "each piece was pinned")
    check("/ipfs/" in index_url and index_url.endswith(index_ref.cid), f"index URL points at its CID ({index_url})")
    page = pin.fetch(index_ref.cid).decode("utf-8")
    check(all(ref.cid in page for _it, ref, _u in published), "index references every pinned item CID")
    check(all(len(pin.fetch(ref.cid)) > 0 for _it, ref, _u in published), "each item page is independently fetchable")
    check(_no_external(page), "the published index is self-contained")

    return _finish()


def _finish():
    print()
    if _FAIL:
        print(f"RESULT: FAIL ({len(_FAIL)})")
        for f in _FAIL:
            print("   - " + f)
        sys.exit(1)
    print("RESULT: PASS — gallery index verified (self-contained, portable links, references all pieces)")
    sys.exit(0)


if __name__ == "__main__":
    main()
