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
| `/feed/` | `/rss.xml` (and `/atom.xml`) | nginx 301 |
| `/author/jonkatz/` | — | nginx 301 to `/` |

## Layout

```
config.toml
content/
  _index.md            paginated homepage (10/page, like WordPress)
  posts/_index.md      transparent section — posts resolve at root level
  posts/*.md           standalone posts
  pages/_index.md      render = false; holds standalone pages
  pages/about.md
  archive/_index.md    full post index at /archive
  series/              one folder per series; /series lists them automatically
i18n/en.toml           tabi's English strings, locale changed to en_US
static/
  custom.css           image sizing/captions, series page, category chips
  wp-content/uploads/  migrated media; keeping this path means zero URL rewriting
templates/             overrides of tabi (see comments in each file)
themes/tabi/           vendored, not a submodule
```

`content/posts/_index.md` is `transparent = true`, which is what lets the
homepage paginate the posts while each post still lives at `/<slug>`. Verified
working — don't add `render = false` to it, that is not needed and the
combination is untested.

---

# Writing a new post

New posts go in `content/posts/` (or a series folder, below). Copy this:

```toml
+++
title = "My New Post"
date = 2026-10-03
path = "my-new-post"          # URL becomes /my-new-post — keep the WordPress-style flat URLs
description = "One or two plain sentences. Used for search results, link previews and the homepage listing."
# draft = true                # builds only under `zola serve`

[taxonomies]
category = ["Self Hosting"]   # or "Smart Home" — reuse existing names exactly
tag = ["home assistant"]      # lowercase, reuse existing tags where possible
+++
```

- **`path` is required.** Without it the post lands at `/posts/<slug>/`,
  breaking the flat URL scheme every other post uses.
- **`description` matters.** Without one, listings fall back to the first
  paragraph and link previews get nothing useful.
- **Code fences need a language** (` ```bash `, ` ```yaml `, ` ```ini `,
  ` ```python `, ` ```nginx `, or ` ```text ` for console output). Unlabelled
  fences build, but render as "PLAIN" with no highlighting.
- **Images:** put new ones under `static/img/` (served at `/img/…`), and always
  write alt text: `![What the image shows](/img/foo.png)`. A caption is an
  italic line directly underneath — `custom.css` styles it as a caption:

  ```markdown
  ![Tasmota main menu](/img/tasmota-menu.png)
  *The main menu after flashing*
  ```

  Images are capped to 75% of the viewport height and lazy-loaded
  (`lazy_async_image` in config.toml). Shrink screenshots before committing;
  1 MB PNGs are what made the old posts heavy.
- **`updated = YYYY-MM-DD`** shows "Updated on …" on the post page. Only set it
  for real revisions.
- **Comments** (giscus) are on for every post. Set `[extra] giscus = false`
  to turn them off for one page (the About page does this).

## Series

A series is a folder under `content/series/` with an `_index.md` that sets
`extra.series = true` (copy `content/series/email-backup/_index.md`). Posts in
it get "Part N of M" and next/previous links automatically, and the series
appears on `/series` automatically (`templates/series_index.html`); there is
no hand-maintained list to update. Set the series' `description` in its
`_index.md`; that is what `/series` shows.

## Build and check

```bash
zola build
zola check     # link checker; external failures are warnings
zola serve     # local preview, includes drafts
```

`zola build` deletes and recreates `public/`. Mount the whole project into
both the `zola-build` and `nginx` containers; never mount a volume at
`public/` itself.

## Deployment notes

- nginx config lives outside the repo (`nginx.conf`, gitignored). It handles
  the WordPress leftovers: `/feed/` → `/rss.xml`, 410s for `wp-*` endpoints
  and per-post comment feeds, date archives → `/archive/`, and the
  first-party Plausible proxy (`/js/vx.js`, `/vx/event`).
- **Syntax highlighting must stay `style = "class"`** in config.toml. tabi's
  Content-Security-Policy (`style-src 'self'`) blocks inline styles, so
  `"inline"` silently strips every colour and background from code blocks.
- `i18n/en.toml` is a full copy of tabi's English strings (a site-level file
  replaces the theme's, it does not merge). The only change is
  `date_locale = "en_US"`. Re-copy it if you update tabi.
- `static/favicon.*`, `static/apple-touch-icon.png` and
  `static/social-card.jpg` (the link-preview image) are generated from the
  banjo-cat logo.

## Preview on GitHub Pages

`.github/workflows/preview.yml` publishes a preview to
<https://jon6fingrs.github.io/thehelpfulidiot-site/> on every push to `main`
or a `claude/*` branch (or on demand from the Actions tab). It is noindex'd
and has analytics stripped; production is unaffected. Because Pages serves
from a subfolder, `.github/scripts/preview-fixup.py` prefixes the root-relative
links in post content. One-time setup is described at the top of the
workflow file.

## Known follow-ups

- **Duplicate terms.** `self-hosting` and `smart-home` exist as both a category
  and a tag. Both tag archives were in the WordPress sitemap, so removing the
  tags would 404 indexed URLs. Leave them, or add nginx redirects first.
- **Bulk `updated` dates.** Most posts carry `updated = 2024-04-15` or
  `2024-04-09` from a WordPress bulk save, not real edits. The listing now
  shows only the original date (`post_listing_date = "date"`); post pages
  still show "Updated on". Delete the line from a post to drop it.
- **Unreferenced uploads.** `python3 prune-uploads.py` (dry run) lists
  originals no post uses, including two 8 MB PNGs in `2021/09/`. They may
  still be linked from outside the site; quarantine, don't delete.
