+++
title = "Moving Four Websites Off My Home Server and Onto Cloudflare Pages"
date = 2026-11-01
path = "moving-four-websites-off-my-home-server-to-cloudflare-pages"
description = "How I moved four self-hosted websites from a home server behind an Oracle VPS to Cloudflare Pages, using GitHub Actions for the two Zola sites and Cloudflare's own Git integration for the two plain HTML sites, plus what bit me along the way."

[taxonomies]
category = ["Self Hosting"]
tag = ["home lab", "cloudflare", "zola", "github actions", "claude"]
+++

A few weeks ago I [moved this blog from WordPress to Zola](/goodbye-wordpress-hello-zola). That left me with a pile of static files, which raised an uncomfortable question: why was I serving them from a server in my house? WordPress needs PHP and a database, so a free host is hard to find. Static files can live almost anywhere.

So I moved four sites to Cloudflare Pages: this blog, my personal site, and two small calculators.

## Where things were

The setup was the one from [Create a FREE public endpoint for self-hosted services using Oracle Cloud and OPNsense](/create-a-free-public-endpoint-for-self-hosted-services-using-oracle-cloud-and-opnsense). A free Oracle VPS held the public IP, and a WireGuard tunnel carried traffic to my house.

![The old setup: a visitor's request goes from Cloudflare DNS to the Oracle VPS, through a WireGuard tunnel to my house, then through OPNsense and Traefik to nginx containers](/img/2026/11/old-flow.svg)
*The old path. Every stop had to work.*

It mostly worked, but the connection was often unstable. Pages needed several reloads, and it got worse when more than one person visited at once. With that many hops I could never tell which one was at fault.

## Why Cloudflare

My DNS already lived there, and Pages is a free static host. Moving a site meant pointing the name somewhere else. Now the sites don't depend on my house having power.

![The new setup: I push to GitHub; GitHub Actions builds and deploys the Zola sites, while Cloudflare watches the repo for the two plain HTML sites; Cloudflare Pages serves all four](/img/2026/11/new-flow.svg)
*The new path*

## Two ways onto Pages

### The Zola sites: GitHub Actions

These need a build, so GitHub Actions does it. On every push to the main branch it builds the site, runs the link check and the site's tests, and **only if all of that passes** uploads the result with `wrangler pages deploy`. A red check never deploys.

{% raw %}
```yaml
deploy:
  needs: build
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
  steps:
    # ...download the built site, then:
    - run: npx --yes wrangler@4.156.0 pages deploy --branch main --commit-hash "$GITHUB_SHA"
```
{% endraw %}

The deploy uploads the exact folder the tests ran against, and I pinned the wrangler version so an update can't change my deploys. Setup was a Cloudflare API token with one permission (**Cloudflare Pages: Edit**) plus my account ID, both stored as GitHub secrets. The workflow skips the deploy if they're missing, so I could merge it before Cloudflare was ready.

### The calculators: Cloudflare watches the repo

Each calculator is one `index.html`, so there's nothing to build and a workflow would only copy a file. Instead, Cloudflare Pages connects to the GitHub repo directly. Both calculators live in one repo, so I made two Pages projects, each watching its own folder with no build command:

```text
ophtho-sites/
├── munnerlyn/
│   ├── index.html
│   ├── 404.html
│   └── _headers
└── randleman/
    └── (same)
```

No CI, no secrets, no token to rotate. The cost is that there's no gate either: whatever lands on the branch is published. And as far as I can tell, a Pages project is either Git-connected or direct-upload, with no switching later, so decide before you create it.

## What nginx used to do

| Old job | New home |
|---|---|
| Redirects (`/feed` to `/rss.xml`) | `_redirects` |
| Cache and security headers | `_headers` |
| `410 Gone` for WordPress leftovers like `/wp-login.php` | Functions |
| Self-hosted Plausible analytics proxy | Functions |
| Contact form on my personal site | A Function that sends through Fastmail |
| A real 404 page | `404.html` |

Functions are small JavaScript files that only run on the paths listed in `_routes.json`. Forget to list one and it just never runs, with no error. The contact form's password lives in Cloudflare secrets, and secrets only take effect on the *next* deploy, so I had to re-run the workflow before the form worked.

## Cutover

Since the DNS was already in Cloudflare, cutover was adding the domain under *Custom domains* in the Pages project. Cloudflare handled the DNS record and certificate. I left the mail records alone. Beforehand I compared each site on its `pages.dev` address against the live one, and for the blog I used a script that checks every sitemap URL, every asset and the old WordPress addresses.

## Lessons learned

Most of these fail silently.

- **`/x` and `/x/` are different paths.** nginx can cover both in one rule. In `_redirects`, list each.
- **A path matching two `Cache-Control` rules gets both, joined.** Make sure each path matches one.
- **No `404.html` means every unknown URL returns `index.html` with a 200.** Adding one brought real 404s back.
- **Noindex the `pages.dev` copies**, or Google may index them as duplicates. A `_headers` rule for those hostnames fixes it.
- **Delete your testing workarounds.** I had a variable that kept links on the `pages.dev` copy. Left in place after cutover, the live site would have linked to the wrong place.
- **Match the CSP to the page.** The Zola sites forbid inline scripts. The calculators are single files with inline scripts, so they need a looser policy.
- **Test your rules.** A small test that fails when the redirects and `_routes.json` drift apart catches it in CI instead of as a 404.

## Was it worth it?

Yes. As with the [WordPress move](/goodbye-wordpress-hello-zola), I leaned heavily on Claude for the workflow, Functions and tests, and I made the decisions and ran the deploys. Publishing is now a `git push` for the calculators and a merged pull request for the blog, and a failed build leaves the old site up. No home server, tunnel or Oracle VPS is in the path anymore.

Thanks for reading.
