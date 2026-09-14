#!/usr/bin/env python3
"""Quarantine unreferenced files under static/wp-content/uploads/.

Run from the site root:
    python3 prune-uploads.py            # dry run, shows what would move
    python3 prune-uploads.py --apply    # moves them to ../thi-unused-uploads/

MOVES rather than deletes, preserving relative paths, so you can put anything
back with a single rsync if a page turns out to need it.

Scans content/, templates/, static/custom.css, static/js/ and config.toml for
references. A file is kept if its path, or just its basename, appears anywhere
in those — basename matching is deliberately loose, to avoid deleting something
referenced by a relative or templated path.
"""
import re
import shutil
import sys
from pathlib import Path

APPLY = "--apply" in sys.argv
UPLOADS = Path("static/wp-content/uploads")
QUARANTINE = Path("../thi-unused-uploads")

SEARCH_PATHS = ["content", "templates", "config.toml", "README.md",
                "static/custom.css", "static/js"]

if not UPLOADS.is_dir():
    print("Run from the site root (static/wp-content/uploads not found)")
    sys.exit(1)

# ---- gather every text file that might reference an upload -------------------
haystack = []
for sp in SEARCH_PATHS:
    p = Path(sp)
    if p.is_file():
        haystack.append(p)
    elif p.is_dir():
        haystack.extend(f for f in p.rglob("*") if f.is_file())

text = ""
for f in haystack:
    try:
        text += f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass

# ---- decide what's referenced ------------------------------------------------
on_disk = sorted(f for f in UPLOADS.rglob("*") if f.is_file())
used, unused = [], []

for f in on_disk:
    web_path = "/" + str(f.relative_to("static"))
    if web_path in text or f.name in text:
        used.append(f)
    else:
        unused.append(f)

def mb(paths):
    return sum(p.stat().st_size for p in paths) / 1024 / 1024

print(f"on disk     : {len(on_disk):4}  ({mb(on_disk):7.1f} MB)")
print(f"referenced  : {len(used):4}  ({mb(used):7.1f} MB)")
print(f"unreferenced: {len(unused):4}  ({mb(unused):7.1f} MB)")
print()

# ---- flag the risky ones ----------------------------------------------------
# WordPress linked inline thumbnails to their full-size original. Those
# full-size URLs may be indexed by Google Images even though no page links
# them now. Sized variants (-800x600) are far less likely to be linked
# anywhere but the page that used them.
sized = re.compile(r"-\d+x\d+\.[a-z0-9]+$", re.I)
originals = [f for f in unused if not sized.search(f.name)]
variants = [f for f in unused if sized.search(f.name)]

print(f"  of the unreferenced:")
print(f"    {len(variants):4} generated size variants   ({mb(variants):7.1f} MB)  low risk")
print(f"    {len(originals):4} full-size originals       ({mb(originals):7.1f} MB)  may be indexed")
print()

if originals:
    print("  largest full-size originals (check these before applying):")
    for f in sorted(originals, key=lambda p: -p.stat().st_size)[:10]:
        print(f"    {f.stat().st_size/1024/1024:6.1f} MB  /{f.relative_to('static')}")
    print()

if not APPLY:
    print("Dry run. Re-run with --apply to move the unreferenced files to")
    print(f"{QUARANTINE.resolve()}")
    sys.exit(0)

# ---- move --------------------------------------------------------------------
moved = 0
for f in unused:
    dest = QUARANTINE / f.relative_to("static")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(f), str(dest))
    moved += 1

print(f"moved {moved} files to {QUARANTINE.resolve()}")
print()
print("Next:")
print("  1. rebuild, then load a few image-heavy posts and check nothing broke:")
print("       the Oracle Cloud post, the XMCOSY post, the Fire Tablet post")
print("  2. if anything is missing, put it back:")
print(f"       rsync -av {QUARANTINE}/ static/")
print("  3. when happy, amend the single commit so the bytes actually leave")
print("     the repo rather than staying in history:")
print("       git add -A && git commit --amend --no-edit")
print("       git push --force-with-lease")
