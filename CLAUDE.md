# The Helpful Idiot — notes for Claude Code

Personal tech blog (self-hosting, home automation) at https://thehelpfulidiot.com.
Static site: **Zola 0.23.6** + the **tabi** theme (vendored in `themes/tabi/`,
not a submodule). Migrated from WordPress in 2026; URL parity with the old
site matters because posts are indexed and linked from forums.

README.md has the human-facing guide (writing posts, series, deploy). This
file is what an agent needs to avoid breaking things.

## Commands

```bash
zola build                                # → public/ (gitignored)
zola check --skip-external-links          # internal link check; the "linter"
python3 scripts/check-site.py public      # content + CSP checks; the "tests"
zola serve                                # preview incl. drafts
```

Run all three before every push. In cloud sessions, `.claude/hooks/session-start.sh`
installs Zola into `~/.local/bin`. Zola has no package manager entry here; the
hook downloads the GitHub release.

## How it is deployed

- **Production:** nginx container on the owner's home server (`net-server`),
  behind Traefik. The owner runs `git pull` + rebuilds there by hand. Merging
  to `main` does NOT update the live site by itself; say so when relevant.
- **`nginx.conf` is not in the repo** (gitignored: internal hostnames). It
  handles WordPress leftovers: `/feed/` → `/rss.xml`, 410 for `wp-*` and
  per-post `/feed/`, date archives → `/archive/`, first-party Plausible proxy
  at `/js/vx.js` + `/vx/event`, and caching (CSS/JS immutable only when the URL
  has Zola's `?h=` hash). If a change needs nginx edits, give the owner the
  snippet; you cannot apply it.
- **Preview:** `.github/workflows/preview.yml` publishes to
  https://jon6fingrs.github.io/thehelpfulidiot-site/ on every push to `main`
  or `claude/**`. Pages serves from a subfolder, so
  `.github/scripts/preview-fixup.py` prefixes root-relative links, adds
  `noindex`, and strips analytics. Use it to let the owner check changes on
  a phone before merging. Giscus comments on the preview are the REAL ones.

## Hard constraints (each of these broke once)

1. **CSP.** tabi sets `script-src 'self'` and `style-src 'self'`.
   - No inline `<script>` or `style=""`. JS goes in `static/js/*.js` and is
     loaded with `<script src>`; styles go in `static/custom.css`.
   - `[markdown.highlighting] style` must stay `"class"`. `"inline"` emits
     `style=` on every token and the CSP silently strips all code colours.
   - New third-party embeds need their domain in `extra.allowed_domains`.
2. **Taxonomies are singular** (`category`, `tag`) so URLs match WordPress
   (`/category/<slug>/`, `/tag/<slug>/`). Upstream tabi expects `tags`, which
   is why `templates/page.html` and `templates/components/list_posts.html`
   are overridden. Don't rename taxonomies or delete existing terms: their
   archive URLs were in the WordPress sitemap. `self-hosting` and
   `smart-home` exist as both category and tag on purpose.
3. **Every post needs `path = "<slug>"`** in front matter, or it lands at
   `/posts/<slug>/` instead of `/<slug>`. `content/posts/` and
   `content/series/*` are transparent sections.
4. **Media lives at `static/wp-content/uploads/...`** (old WordPress paths,
   served with a 1-year immutable cache). Never rewrite a file at an existing
   path with different pixels; add a new file instead. Lossless optimisation
   is fine.
5. **`i18n/en.toml` replaces tabi's English strings entirely** (it does not
   merge). Only change from upstream: `date_locale = "en_US"`. Re-copy from
   `themes/tabi/i18n/en.toml` if tabi is updated.
6. **iOS/WebKit.** The phone menu (`templates/partials/nav.html` +
   `static/js/navmenu.js`) relies on a `<details>` whose `summary` gets a
   full-screen `::before` layer while open. iOS fires no click for taps on
   plain page areas, and WebKit may not toggle a `display:flex` summary.
   Headless Chromium tests pass where iPhones fail, so say when something
   is untested on a real device and ask the owner to check on their phone.

## Layout of the overrides

| File | Overrides | Why |
|---|---|---|
| `templates/page.html` | tabi page | singular taxonomies; shows categories + tags |
| `templates/components/list_posts.html` | tabi listing | singular taxonomies; category chip |
| `templates/partials/nav.html` | tabi nav | logo, one-line phone header, `<details>` menu |
| `templates/partials/home_banner.html` | tabi banner | tagline as h1; site name not repeated |
| `templates/partials/analytics.html` | tabi analytics | first-party Plausible paths (`vxinit.js`, `vx.js`) |
| `templates/series_index.html` | new | `/series` lists series sections automatically |
| `static/custom.css` | — | all site CSS, sectioned with comments |

Prefer CSS in `custom.css` over new template overrides; each override is a
file to re-diff when tabi updates. Selectors sometimes repeat tabi's ids on
purpose to outrank its SCSS specificity; keep that when editing.

## Content conventions

- Front matter: `title`, `date`, `path`, `description` (real sentence, not a
  truncated excerpt), `[taxonomies] category = [...]`, `tag = [...]`. Reuse
  existing term names exactly.
- Code fences always have a language (`bash`, `yaml`, `ini`, `python`,
  `nginx`, `php`, `json`, `text` for console output).
- Images: `![alt text](/path)` with real alt text; an optional caption is an
  italic line directly underneath (`*Caption*`), styled by `custom.css`.
- **Series.** Whenever a new post continues or follows up an existing one (a
  "Part 2", an update, the next step of the same project), put them in a series
  instead of linking them by hand: a folder under `content/series/<slug>/`
  with an `_index.md` copied from `content/series/email-backup/_index.md`
  (new `title` and `description`), and `git mv` the posts into it. URLs don't
  change because every post sets `path`, and the series adds "Part N of M" and
  next/previous links by itself, so don't add manual "Part 2" or "Update" links
  between them. Posts that merely share a topic or tag (two unrelated Home
  Assistant projects) are not a series. When a draft looks like it belongs with
  an older post, say so and ask before turning it into a series. Done for the
  wall tablet dashboard posts (`content/series/wall-tablet-dashboards/`).
- `updated =` only for real revisions. Many posts carry a bulk 2024-04 date
  from WordPress; listings show only `date` for that reason.

## Verifying visual changes

There is no test suite for layout. What has worked:

1. `zola build -u http://127.0.0.1:PORT -o /tmp/site --force` and serve it with
   `python3 -m http.server PORT --directory /tmp/site` (`--directory` keeps
   serving across rebuilds, which delete and recreate the folder).
2. Playwright with the pre-installed Chromium (`/opt/pw-browsers`; install the
   `playwright` npm package in a scratch dir, never `playwright install`).
   Check every URL in `public/sitemap.xml` in light and dark for console
   errors and failed requests; the only expected failure is `/js/vx.js`
   (exists only behind nginx).
3. Screenshot at 390×844 with `deviceScaleFactor: 2` for phone layout, and
   1280 wide for desktop. The owner mostly reviews on an iPhone.

## Working with the owner

- Not a developer by trade; explain outcomes plainly, give copy-paste
  commands for anything on their server, and keep nginx edits as full files
  or clearly marked snippets.
- Changes go through a branch + PR + preview; merge only when asked.
