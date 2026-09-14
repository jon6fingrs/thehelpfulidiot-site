# The Helpful Idiot — Zola site

Verified against **Zola 0.23.6** and **tabi** @ `606f4b28` (2026-09-13).
`zola build` was confirmed clean with sample converted posts before delivery.

## Why tabi

110 code blocks and 64 images make this a code-first blog. tabi ships the three
things you would otherwise hand-build on portio: elasticlunr search, generic
taxonomy templates, and syntax highlighting with copy-to-clipboard buttons.

## URL parity with WordPress

The config is set up so nothing you have published changes address:

| WordPress | Zola | How |
|---|---|---|
| `/<slug>` | `/<slug>` | `path = "<slug>"` in each post's front matter |
| `/page/2` | `/page/2` | `paginate_by = 10` on `content/_index.md` |
| `/category/<slug>/` | same | taxonomy named `category`, singular, on purpose |
| `/tag/<slug>/` | same | taxonomy named `tag`, singular |
| `/feed/` | `/atom.xml`, `/rss.xml` | needs an nginx redirect, see below |
| `/author/jonkatz/` | — | needs an nginx redirect to `/` |

## Layout

```
config.toml
content/
  _index.md            paginated homepage (10/page, like WordPress)
  posts/_index.md      transparent section — posts resolve at root level
  posts/*.md           <- converter output goes here
  pages/_index.md      render = false; holds standalone pages
  pages/about.md       already populated from the live site's About text
  archive/_index.md    full post index at /archive
static/
  custom.css           code-block scroll + image sizing
  wp-content/uploads/  <- rsync target; keeping this path means zero URL rewriting
themes/tabi/           vendored, not a submodule
```

`content/posts/_index.md` is `transparent = true`, which is what lets the
homepage paginate the posts while each post still lives at `/<slug>`. Verified
working — don't add `render = false` to it, that is not needed and the
combination is untested.

---

# Runbook

## 1. On the WordPress LXC — extract

```bash
# snapshot the LXC in Proxmox first
./wp-recon.sh                      # already done; re-run after any DB change
./wp2zola.py --src /root/wp-export --dest /root/zola-content
less /root/zola-content/report.txt
```

Check in `report.txt`, in this order:

1. **UNHANDLED BLOCK TYPES** — should be empty. Anything listed needs a renderer.
2. **BROKEN ASSET HOSTS** — the 6 `synology.regester.lan` references. Pull those
   originals out of Synology Photos by hand and drop them into uploads.
3. **URL REWRITES** — confirm every `10.0.0.132` rewrite is an image or a link.
   None should come from inside a code block; the converter does not touch code
   block contents, but read the list anyway.
4. **TODO MARKERS** — grep the output for `<!-- TODO` and resolve each.

## 2. On the WordPress LXC — copy media

```bash
tar czf /root/zola-content.tar.gz -C /root zola-content

rsync -av \
  --exclude='wp-statistics/' --exclude='astra-sites/' --exclude='astra-docs/' \
  --exclude='wpo/' --exclude='1637/' --exclude='1638/' \
  --exclude='*.mmdb' --exclude='.htaccess' --exclude='*.log' \
  /var/www/wordpress/wp-content/uploads/ \
  <dockerhost>:/path/to/site/static/wp-content/uploads/
```

Excluding `wp-statistics/` alone drops 51M of MaxMind GeoIP databases. Expect
roughly 95M of real media to land, dominated by `2021/` at 89M.

Two files in `2021/09` are 7.8M and 8.2M PNGs (`image-3.png`, `image-4.png`).
They will work as-is but they are the whole page weight of those posts — worth
an `oxipng -o4` pass or a resize once the site is up.

## 3. On the Docker host — assemble

```bash
tar xzf zola-content.tar.gz
cp zola-content/posts/*.md  /path/to/site/content/posts/
cp zola-content/pages/*.md  /path/to/site/content/pages/    # overwrites about.md
```

Then verify every referenced asset actually exists:

```bash
cd /path/to/site/static
while read -r p; do [ -f ".$p" ] || echo "MISSING $p"; done \
  < /path/to/zola-content/assets-referenced.txt
```

## 4. Build

```bash
zola --root /path/to/site build
zola --root /path/to/site check     # link checker; external failures are warnings
```

Remember gotcha #1 from last time: `zola build` deletes and recreates `public/`.
Mount the whole project directory into both the `zola-build` and `nginx`
containers — never mount a volume at `public/` itself.

## 5. Go live

Change `base_url` from `https://zola.thehelpfulidiot.com` to
`https://thehelpfulidiot.com` at cutover. It is the only value that changes.

nginx redirects for the WordPress URLs Zola has no equivalent for:

```nginx
location = /feed/            { return 301 /atom.xml; }
location = /feed             { return 301 /atom.xml; }
location ^~ /author/         { return 301 /; }
location ^~ /wp-admin        { return 404; }
location ^~ /wp-login.php    { return 404; }
location ^~ /xmlrpc.php      { return 404; }
```

## Known follow-ups

- **Code fence languages.** WordPress core code blocks store no language, so all
  110 fences arrive unlabelled and render plain. `error_on_missing_language` is
  set to `false` so builds never break while you add them post by post.
- **Plausible.** Not wired up. `[extra]` in tabi has analytics hooks; the
  nginx first-party proxy from the last site transfers directly and you no
  longer need the `code-snippets` PHP shim.
- **Comments.** Off (`iine = false`). Old `#comments` anchors resolve to the page.
- **Duplicate terms.** `self-hosting` and `smart-home` exist as both a category
  and a tag. Worth collapsing in WordPress before a re-run, or by hand after.
- **`hello-world` (post ID 1)** is published with a category and 3 tags. Confirm
  it is real content and not the WordPress default before publishing.
- **Drafts 173 and 221** have no slug; the converter generates one from the
  title and sets `draft = true`, so they build only under `zola serve`.
