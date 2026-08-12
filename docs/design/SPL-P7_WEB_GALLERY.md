---
created: 2026-08-10
branch: feat/spl-web-gallery
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# SPL-P7 — the web gallery substrate

The last pillar: a creator's finished piece goes to the internet as a **single,
self-contained HTML page**, content-addressed, carrying the provenance that ties the
other pillars together. This is the "future web deploy/gallery (its own substrate)"
the SPL-S1 mock pointed at.

## Design
- **`splendor.deploy.gallery`** (pure Python): `GalleryItem` → `render_item_page` builds a
  retro/Citrate-styled page with the image embedded as a `data:` URI — **no external
  requests**, so it passes a strict CSP and serves straight from IPFS. It shows the
  provenance: prompt, eval score, palette, tris, workflow, the pinned asset CID, and any
  on-chain attestation. Untrusted text is HTML-escaped.
- **Content-addressed**: `page_cid(item)` is deterministic — the page *is* its identity.
- **`publish_item(item, pinning)`** pins the page (reusing `IpfsPinning`) → `(PinRef, url)`;
  unreachable fails honestly (no fabricated URL).

## In the product
`SPLENDOR_OT_publish_gallery` (Deploy panel) takes the last retro/affine image, builds a
`GalleryItem` from scene state, pins it, and reports the gateway URL — or an honest
`unreachable:` when no daemon is up.

## Verified
- `test_spl_web_gallery.py` — self-contained (no external URLs), image as `data:` URI,
  provenance present, **injection-safe** (a `<script>` in the prompt is escaped),
  deterministic CID, and a **live IPFS publish that round-trips byte-for-byte**.
- `test_spl_web_gallery_ui.py` — the operator publishes a real image datablock to a
  content-addressed IPFS URL (or fails honestly offline).
- A sample page from the real Suzanne render: `docs/design/spl-web-gallery.html`.

## Multi-piece index — DONE

`render_index` builds a self-contained index (thumbnails embedded, **relative `/ipfs/<cid>`
links** so they resolve on whatever gateway serves the index — portable, not host-specific).
`publish_gallery(items, pinning)` pins each piece's page, then pins the index referencing them
all. In the product: **Add to Gallery** accumulates the current piece into a per-scene
collection, **Publish Gallery Index** publishes N pages + the linking index (`SPLENDOR_PT_gallery`).

Verified (`test_spl_gallery_index.py`, `_ui.py`): self-contained (no external http; data URIs +
relative links only), injection-safe hrefs (`javascript:` dropped), the published index references
every pinned item CID and each page is independently fetchable. Sample:
`docs/design/spl-web-gallery-index.html`.

## Still open (honest)
- Pinning-service redundancy (a second pin target) and an ENS/DNSLink human name for the CID.
