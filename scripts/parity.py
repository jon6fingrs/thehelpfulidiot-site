#!/usr/bin/env python3
"""Compare two copies of the site: production and a Cloudflare Pages copy.

    python3 scripts/parity.py https://thehelpfulidiot.com https://thehelpfulidiot.pages.dev
    python3 scripts/parity.py --old-ip 150.136.59.49 https://thehelpfulidiot.com https://thehelpfulidiot.com

--old-ip sends the OLD side to that address (curl --resolve), so after
cutover the live domain can still be compared with the old server.

Checks, for every URL in OLD's sitemap: status and HTML (base URL
normalised); for every same-site asset those pages reference: status and
SHA-256, with images that differ compared by pixels (needs Pillow); the
nginx rules and old WordPress URLs below: status and Location; and a few
headers. Prints a table of differences; exits 1 if there are any.
"""
import argparse
import concurrent.futures
import hashlib
import io
import re
import subprocess
import sys
import tempfile
import urllib.parse

# path -> what to compare. Status/Location come from the real nginx.conf.
PROBES = [
    "/feed", "/feed/", "/rss", "/rss/", "/feed/atom", "/feed/atom/",
    "/comments/feed", "/comments/feed/",
    "/hello-world/feed/", "/category/smart-home/feed/", "/tag/zigbee/feed",
    "/wp-sitemap.xml", "/wp-sitemap-posts-post-1.xml",
    "/sample-page", "/sample-page/",
    "/author/", "/author/jonkatz/", "/author/thehelpfulidiot/",
    "/category/uncategorized", "/category/uncategorized/",
    "/2021", "/2021/", "/2021/09", "/2021/09/", "/2021/10/", "/2021/11/", "/2022/06/",
    "/2022/09/", "/2024/09/", "/2021/09/29/",
    "/wp-admin", "/wp-admin/", "/wp-includes/js/jquery/jquery.js", "/wp-json/",
    "/wp-json/wp/v2/users", "/wp-login.php", "/xmlrpc.php", "/wp-cron.php",
    "/wp-config.php", "/wp-config-sample.php", "/readme.html", "/license.txt",
    "/wp-content/debug.log", "/wp-content/plugins/akismet/readme.txt",
    "/wp-content/themes/twentytwentyone/style.css",
    "/?p=1", "/page/2/", "/page/1/", "/about", "/archive", "/nope-does-not-exist",
    "/js/vx.js", "/js/vxinit.js", "/search_index.en.json", "/robots.txt",
    "/rss.xml", "/atom.xml", "/sitemap.xml", "/tag/zigbee/rss.xml",
    "/wp-content/uploads/2021/11/fire-tablet-mount.stl",
    "/wp-content/uploads/2021/10/tasmota_template.h",
]
HEADERS = ["cache-control", "content-type", "x-robots-tag", "strict-transport-security",
           "x-content-type-options", "x-frame-options", "referrer-policy", "permissions-policy"]


def fetch(url, resolve=None, body=True):
    """(status, headers{name: [values]}, bytes) via curl, without following redirects."""
    with tempfile.NamedTemporaryFile() as out:
        cmd = ["curl", "-sS", "-m", "30", "-o", out.name, "-D", "-", url]
        if resolve:
            u = urllib.parse.urlsplit(url)
            cmd[1:1] = ["--resolve", f"{u.hostname}:{u.port or 443}:{resolve}"]
        if not body:
            cmd[1:1] = ["-I"]
        r = subprocess.run(cmd, capture_output=True, text=True)
        status, headers = 0, {}
        for line in r.stdout.splitlines():
            if line.startswith("HTTP/"):
                if " 200 Connection established" in line.title() or "Connection Established" in line:
                    continue
                status, headers = int(line.split()[1]), {}
            elif ":" in line:
                k, v = line.split(":", 1)
                headers.setdefault(k.strip().lower(), []).append(v.strip())
        return status, headers, out.read()


def norm_cc(values):
    """nginx sent Cache-Control twice; compare the merged directive set."""
    return ", ".join(sorted({d.strip() for v in values for d in v.split(",") if d.strip()}))


def norm_html(data, origin):
    text = data.decode("utf-8", "replace")
    for o in {origin, origin.replace("https://", "http://")}:
        text = text.replace(o + "/", "/").replace(o, "/")
    return text


def pixels_equal(a, b):
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    try:
        ia, ib = Image.open(io.BytesIO(a)).convert("RGBA"), Image.open(io.BytesIO(b)).convert("RGBA")
    except Exception:
        return None
    if ia.size != ib.size:
        return False
    hi = max(hi for _, hi in ImageChops.difference(ia, ib).getextrema())
    return hi <= 8          # re-encoding may shift a few levels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--old-ip", help="send OLD requests to this IP (curl --resolve)")
    ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    old, new = a.old.rstrip("/"), a.new.rstrip("/")
    diffs = []

    def diff(kind, path, o, n):
        diffs.append((kind, path, str(o), str(n)))

    get_old = lambda p, **k: fetch(old + p, a.old_ip, **k)
    get_new = lambda p, **k: fetch(new + p, **k)

    s, _, sm = get_old("/sitemap.xml")
    pages = [urllib.parse.urlsplit(u).path for u in re.findall(rb"<loc>([^<]+)</loc>", sm and sm or b"")]
    pages = [p.decode() for p in pages]
    print(f"{len(pages)} sitemap URLs", file=sys.stderr)

    assets = set()
    asset_re = re.compile(r'(?:src|href|content)=["\']?([^"\'\s>]+)')

    def page(p):
        so, ho, bo = get_old(p)
        sn, hn, bn = get_new(p)
        return p, so, sn, bo, bn

    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        for p, so, sn, bo, bn in ex.map(page, pages):
            if so != sn:
                diff("page status", p, so, sn)
                continue
            to, tn = norm_html(bo, old), norm_html(bn, new)
            if to != tn:
                at = next((i for i, (x, y) in enumerate(zip(to, tn)) if x != y), min(len(to), len(tn)))
                diff("page html", p, to[max(0, at - 40):at + 60], tn[max(0, at - 40):at + 60])
            for ref in asset_re.findall(to):
                ref = ref.split("#")[0]
                if ref.startswith("/") and not ref.startswith("//") and not ref.endswith("/"):
                    assets.add(ref)
    assets -= set(pages)
    print(f"{len(assets)} assets", file=sys.stderr)

    def asset(p):
        so, ho, bo = get_old(p)
        sn, hn, bn = get_new(p)
        return p, so, sn, ho, hn, bo, bn

    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex:
        for p, so, sn, ho, hn, bo, bn in ex.map(asset, sorted(assets)):
            if so != sn:
                diff("asset status", p, so, sn)
            elif re.search(r"\.(xml|json|txt|xsl)$", p) and norm_html(bo, old) == norm_html(bn, new):
                pass        # feeds and the search index embed the base URL
            elif hashlib.sha256(bo).digest() != hashlib.sha256(bn).digest():
                same = pixels_equal(bo, bn)
                if same is not True:
                    diff("asset bytes", p, f"{len(bo)} B", f"{len(bn)} B" + (" (pixels differ)" if same is False else ""))

    for p in PROBES:
        so, ho, bo = get_old(p)
        sn, hn, bn = get_new(p)
        lo = (ho.get("location") or [""])[0].replace(old, "")
        ln = (hn.get("location") or [""])[0].replace(new, "")
        if (so, lo) != (sn, ln):
            diff("rule", p, f"{so} {lo}".strip(), f"{sn} {ln}".strip())
        for h in HEADERS:
            vo = norm_cc(ho.get(h, [])) if h == "cache-control" else ", ".join(ho.get(h, []))
            vn = norm_cc(hn.get(h, [])) if h == "cache-control" else ", ".join(hn.get(h, []))
            if h == "content-type" and 300 <= so < 400:
                continue    # body of a redirect; nobody sees it
            if vo != vn and so == sn:
                diff(f"header {h}", p, vo or "-", vn or "-")

    if not diffs:
        print("No differences.")
        return 0
    w = max(len(d[1]) for d in diffs)
    print(f"| kind | path | {old} | {new} |\n|---|---|---|---|")
    for k, p, o, n in diffs:
        esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
        print(f"| {k} | `{p}` | {esc(o)} | {esc(n)} |")
    return 1


if __name__ == "__main__":
    sys.exit(main())
