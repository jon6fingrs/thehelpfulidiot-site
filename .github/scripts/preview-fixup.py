#!/usr/bin/env python3
"""Adapt a Zola build for the GitHub Pages preview.

GitHub Pages serves this project under a subfolder:
    https://jon6fingrs.github.io/thehelpfulidiot-site/

Zola's own links honour --base-url, but post content links images and other
posts with root paths (`/wp-content/...`, `/hello-world`), which would point
at the github.io root and 404. This rewrites those to include the subfolder.

Also, for a preview only:
  - adds <meta name="robots" content="noindex"> so search engines never
    index a duplicate of the real site;
  - drops the Plausible script tags (the /js/vx.js proxy only exists behind
    nginx, so they would just 404 and pollute nothing but the console).

Usage: preview-fixup.py <public_dir> <subpath>     e.g. public /thehelpfulidiot-site
"""
import pathlib
import re
import sys

root, prefix = pathlib.Path(sys.argv[1]), sys.argv[2].rstrip("/")

# src=/x, href="/x", href='/x' — but not protocol-relative //host
attr = re.compile(r"""\b(src|href)=(["']?)/(?!/)""")
plausible = re.compile(r"<script[^>]*/js/vx(init)?\.js[^>]*></script>")

count = 0
for page in root.rglob("*.html"):
    html = page.read_text(encoding="utf-8")
    new = attr.sub(lambda m: f"{m[1]}={m[2]}{prefix}/", html)
    new = plausible.sub("", new)
    if "<head>" in new:
        new = new.replace("<head>", '<head><meta name="robots" content="noindex">', 1)
    if new != html:
        page.write_text(new, encoding="utf-8")
        count += 1
print(f"preview-fixup: rewrote {count} pages under {prefix}/")
