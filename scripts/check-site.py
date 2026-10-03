#!/usr/bin/env python3
"""Site checks that `zola check` does not cover.

Each check guards a problem that actually shipped once (see git history /
CLAUDE.md). Run from the repo root:

    python3 scripts/check-site.py            # content checks only
    python3 scripts/check-site.py public     # also check a built site in public/

Exits non-zero if anything fails. No dependencies beyond Python 3.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
STATIC = ROOT / "static"

errors: list[str] = []


def fail(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


def front_matter(text: str) -> tuple[str, str]:
    """Split TOML front matter (+++ ... +++) from the body."""
    m = re.match(r"\+\+\+\n(.*?)\n\+\+\+\n?(.*)", text, re.S)
    return (m.group(1), m.group(2)) if m else ("", text)


def check_content() -> None:
    for md in sorted(CONTENT.rglob("*.md")):
        rel = md.relative_to(ROOT)
        fm, body = front_matter(md.read_text(encoding="utf-8"))
        is_section = md.name == "_index.md"

        if not is_section:
            # Posts keep the flat WordPress URLs (/slug); without `path`
            # they would land at /posts/slug/ and break URL parity.
            if not re.search(r'^path\s*=\s*"[^"/][^"]*"', fm, re.M):
                fail(rel, 'missing `path = "<slug>"` (needed for flat WordPress-style URLs)')
            desc = re.search(r'^description\s*=\s*"(.*)"', fm, re.M)
            if not desc:
                fail(rel, "missing `description` (used for listings, search results, link previews)")
            elif desc.group(1).rstrip().endswith("…"):
                fail(rel, "description is a truncated excerpt (ends in …); write a real one")

        in_fence = False
        for n, line in enumerate(body.splitlines(), 1):
            where = f"{rel} (body line {n})"
            if line.startswith("```"):
                if not in_fence and line.strip() == "```":
                    fail(where, "code fence has no language (use bash/yaml/ini/text/...)")
                in_fence = not in_fence
                continue
            if in_fence:
                # WordPress bold leaked into code as literal tags once; readers
                # copied <strong> into their configs.
                if re.search(r"</?(strong|em|b|span|br)\b", line):
                    fail(where, "HTML tag inside a code block (WordPress formatting leftover?)")
                continue
            for alt, src in re.findall(r"!\[([^\]]*)\]\(([^)\s]+)", line):
                if not alt.strip():
                    fail(where, f"image without alt text: {src}")
                if src.startswith("/") and not (STATIC / src.lstrip("/")).exists():
                    fail(where, f"image file not found under static/: {src}")
        if in_fence:
            fail(rel, "unclosed code fence")


def check_build(public: pathlib.Path) -> None:
    pages = list(public.rglob("*.html"))
    if not pages:
        fail(public, "no HTML found; run `zola build` first")
        return
    for page in pages:
        html = page.read_text(encoding="utf-8")
        rel = page.relative_to(public)
        # tabi's CSP is style-src 'self': inline style attributes are blocked
        # by the browser, which once stripped all syntax highlighting.
        # (Zola minifies HTML, so attributes may be unquoted.)
        if re.search(r"<(?:pre|code|span)\b[^>]*\sstyle=", html):
            fail(rel, "inline style= on code markup; CSP blocks it (markdown.highlighting.style must be \"class\")")
        # Only pages that carry the CSP are affected. Zola's own /page/1/
        # redirect stubs have an inline script but no CSP, so they work.
        has_csp = "Content-Security-Policy" in html
        inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>\s*\S", html)
        if has_csp and any("application/ld+json" not in attrs for attrs in inline):
            fail(rel, "inline <script> on a CSP page; script-src 'self' blocks it, use a file in static/js/")


def main() -> int:
    check_content()
    if len(sys.argv) > 1:
        check_build(ROOT / sys.argv[1])
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print("check-site: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
