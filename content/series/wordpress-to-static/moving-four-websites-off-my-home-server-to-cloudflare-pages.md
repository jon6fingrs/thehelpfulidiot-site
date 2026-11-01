+++
title = "Moving Four Websites Off My Home Server and Onto Cloudflare Pages"
date = 2026-11-01
path = "moving-four-websites-off-my-home-server-to-cloudflare-pages"
description = "How I moved four self-hosted websites from a home server behind an Oracle VPS to Cloudflare Pages, using GitHub Actions for the two Zola sites and Cloudflare's own Git integration for the two plain HTML sites, plus what bit me along the way."

[taxonomies]
category = ["Self Hosting"]
tag = ["home lab", "cloudflare", "zola", "github actions", "claude"]
+++

A few weeks ago I [moved this blog from WordPress to Zola](/goodbye-wordpress-hello-zola). That made the site a pile of static files, which raised an uncomfortable question: why was I still serving a pile of static files from a server in my house? A WordPress site needs a real server with PHP and a database, so it's hard to find a free home for one. A static site can live almost anywhere.

This is the story of how I moved four websites off my home server and onto Cloudflare Pages. This blog, my personal site, and two small calculators. I ended up using two different deployment strategies, I broke a few things in instructive ways, and I'm now running all four without a single container of my own.

## Where things were

The setup was the one I wrote about in [Create a FREE public endpoint for self-hosted services using Oracle Cloud and OPNsense](/create-a-free-public-endpoint-for-self-hosted-services-using-oracle-cloud-and-opnsense). A free Oracle Cloud VPS has the public IP address. Traffic comes in there, goes through a WireGuard tunnel to my router, and ends up at Traefik and nginx on a server in my house. That's a lot of hops. Each one is a thing that can break, and every one of them has to be working for a stranger to read a blog post.

The four sites were:

| Site | What it is | How it was built |
|---|---|---|
| This blog | Zola + the tabi theme | A container rebuilt the site after I pulled changes |
| My personal site | Zola, with a contact form and a few interactive tools | Same, plus a small container for the form |
| Two ophtho calculators | A single `index.html` each | Copied into an nginx container |

![The old setup: a visitor's request goes from Cloudflare DNS to the Oracle VPS, through a WireGuard tunnel to my house, then through OPNsense and Traefik to nginx containers](/img/2026/11/home-server-before.png)
*The old path, one hop after another*

It worked, mostly. But "mostly" is the problem. The connection was often unstable, and a page would sometimes need several reloads before it showed up. It got worse when more than one person was visiting at the same time. When something went wrong it was never obvious which of the hops was at fault, and I was always the one on call.

## Why Cloudflare

This part was easy. All of my DNS already lives in Cloudflare. The domains were there, the records were there, and the only thing that decided whether anyone could see my sites was where those records pointed. Cloudflare Pages is a free static host, and since it's the same company that already answers for my DNS, moving a site over is mostly a matter of pointing the name somewhere else.

The tradeoff is that I'm trading "I run it all" for "someone else runs it". For static sites that's a trade I'll happily make. If my house loses power, the websites don't care anymore.

## The new setup

Here's the whole thing after the move. Everything on the bottom row is Cloudflare's problem now.

![The new setup: I push to GitHub; GitHub Actions builds and deploys the Zola sites, while Cloudflare watches the repo for the two plain HTML sites; all four are served by Cloudflare Pages](/img/2026/11/cloudflare-after.png)
*The new path*

## Two ways to get a site onto Pages

Cloudflare Pages has two different ways of getting files into a project, and I ended up using both.

### Path one: the Zola sites, built by GitHub Actions

Zola sites need a build step, and I wanted that build to be the same one that runs my checks. So for this blog and my personal site, GitHub Actions does the work:

1. I push to the main branch.
2. A GitHub Actions workflow installs Zola and builds the site.
3. It runs the link checker and the site's own tests.
4. **Only if all of that passes**, a second job uploads the finished `public/` folder to Cloudflare with `wrangler pages deploy`.

That last point is the part I like most. A red check never deploys, so a broken build can't take the site down. The deploy job looks like this (trimmed down):

{% raw %}
```yaml
deploy:
  needs: build
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  runs-on: ubuntu-latest
  env:
    CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
    CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
  steps:
    - uses: actions/checkout@v4
    - uses: actions/download-artifact@v4
      with:
        name: public
        path: public
    - uses: actions/setup-node@v4
      with:
        node-version: 22
    - run: npx --yes wrangler@4.156.0 pages deploy --branch main --commit-hash "$GITHUB_SHA"
```
{% endraw %}

Two details in there are on purpose. The deploy downloads the exact folder that the tests ran against, instead of building a second time, so what I tested is what ships. And I pinned the wrangler version, so a surprise update to the tool can't change how my deploys behave.

Setting it up took two secrets:

1. A Cloudflare API token with one permission, **Cloudflare Pages: Edit**, on my account.
2. My Cloudflare account ID.

Both go in the repo's GitHub secrets as `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. I also made the workflow check that both secrets exist and quietly skip the deploy (still green) if they don't. That way the first push, before I had set anything up, didn't fail.

The nginx rules didn't come along for free, though. Cloudflare Pages has its own way of doing everything nginx did, which is the next section.

### Path two: the plain HTML sites, watched by Cloudflare

The two ophtho calculators are the opposite situation. Each one is a single `index.html`. There is nothing to build, so there is nothing for GitHub Actions to do. I'd just be writing a workflow whose only job was to copy a file.

For these, Cloudflare Pages can connect to the GitHub repo directly. You give it the repo, tell it which folder holds a given site and that there's no build command, and from then on Cloudflare watches the repo itself. Push a change, and Cloudflare notices and publishes.

Both calculators live in one repo, each in its own folder. So I made two Pages projects pointed at the same repo, each one watching a different folder:

```text
ophtho-sites/
├── munnerlyn/
│   ├── index.html
│   ├── 404.html
│   └── _headers
└── randleman/
    ├── index.html
    ├── 404.html
    └── _headers
```

There's no CI to maintain, no secrets to store in GitHub, and no token to rotate. The cost is that there's also no gate. There are no tests to fail first, because for a page like this there aren't any tests. Whatever lands on the branch gets published.

I'd call this the better choice for anything that is already finished HTML, and the worse choice for anything that needs a build. Which brings up a small catch: as far as I can tell, a Pages project has to be created one way or the other, either by connecting Git or by direct upload, and you can't swap it afterwards. Decide before you create the project.

## What nginx used to do for me (and what does it now)

On the old setup nginx and Traefik did a surprising number of jobs without me thinking about them. Moving to Pages meant finding a new home for each one.

| Old job | New home |
|---|---|
| Redirects (`/feed` to `/rss.xml`, and so on) | `static/_redirects` |
| Cache and security headers | `static/_headers` |
| Returning `410 Gone` for WordPress leftovers like `/wp-login.php` | Cloudflare Functions |
| My self-hosted Plausible analytics proxy | Cloudflare Functions |
| The contact form on my personal site | A Cloudflare Function that sends mail through Fastmail |
| A real 404 page | `404.html` |

The Functions are small JavaScript files in a `functions/` folder, and Cloudflare runs them on the same infrastructure as Workers. The important thing to know is that they only run on the paths you list in a file called `_routes.json`. Everything else is served straight from the build without waking up any code. If you write a Function and forget to list its path, it just never runs, and nothing tells you.

The contact form was the biggest piece of work. It used to be its own container that sent mail. Now it's a Function that sends through Fastmail's SMTP with an app password. The password and the other personal details are stored as Cloudflare secrets, not in the repo. One thing I needed to learn: secrets only take effect on the *next* deploy, so after adding them I had to re-run the workflow before the form started working.

## Cutover, which was anticlimactic

Because the DNS was already in Cloudflare, switching a site over was:

1. Open the Pages project and add the real domain under *Custom domains*.
2. Wait for it to go green.

That's it. Cloudflare creates the DNS record and the certificate on its own. I left the mail records (MX, SPF, DKIM, DMARC) on my personal domain completely alone, since mail has nothing to do with the website.

Before that I let each site run for a while on its free `*.pages.dev` address and compared it against the live one. For the blog I wrote a small script that walks every URL in the sitemap, every asset, and all the old WordPress addresses, and compares the answers from the old and new origin. Comparing every URL is a lot more reliable than clicking around and hoping.

The last step was shutting down the old containers and removing the Traefik routes. That's the moment this stopped being a project and became how things are.

## Lessons learned

Most of these only showed up by actually deploying, and several of them fail silently.

**Pages treats `/x` and `/x/` as different paths.** nginx lets you write one rule that covers both. In `_redirects` you list each one separately. Skip the second one and half your visitors get the old behaviour.

**No path may match two `Cache-Control` rules in `_headers`.** If two rules match, Pages doesn't pick one. It joins the values together, and you end up with a header that says two contradictory things. The fix is to write the rules so every path matches exactly one.

**Without a `404.html`, Pages serves `index.html` for every unknown address, with a 200 status.** That's convenient for a single-page app and wrong for anything else. Bots would see a "working" page at every random path. Adding a plain `404.html` to each calculator brought back real 404s, like the old nginx setup had.

**Keep the `*.pages.dev` copies out of Google.** Every project also gets a public address on `pages.dev`, and search engines will happily index it as a duplicate of the real site. A `_headers` rule that adds `X-Robots-Tag: noindex` for those hostnames, and only those, fixes it without touching the real domain.

**Remember to remove your temporary workarounds.** Before cutover I had a repository variable that made the build use a relative base URL, so links on the `pages.dev` copy would stay on the `pages.dev` copy. That's helpful during testing and a disaster afterward, because the live site would link to the wrong place. I deleted it at cutover, and wrote a note to myself in the repo not to put it back.

**The security headers need to match the page.** The Zola sites have a strict Content Security Policy with no inline scripts. The calculators are single files with their scripts and styles written inline, so their policy has to allow that. Copying the strict policy over would have broken them on the first load. If you're moving headers from one site to another, test the page afterward.

**Keep your redirect rules in step with the thing that lists them.** The routes file, the redirects and the Functions all have to agree. I added a small test that fails if they drift apart, so I find out in CI instead of by seeing a 404 later.

**Write a gate into your deploy job.** The "skip if the secrets are missing" check seems like a small thing. It meant I could merge the workflow before I had finished the Cloudflare setup, and it made the whole transition much less stressful.

## Using Claude for the boring parts

As with the [WordPress migration](/goodbye-wordpress-hello-zola), I leaned heavily on Claude for this. It wrote the workflow, the Functions, the redirect rules and the tests, and I made the decisions, ran the deploys, and found the surprises. I'm not going to pretend I had `_routes.json` memorized. Honestly, having something that will port my nginx rules one at a time and write the test that proves each port is correct is what made this manageable.

## Was it worth it?

Yes. All four sites are now served from Cloudflare's network, with no home server, no tunnel, and no Oracle VPS in the path. Publishing is a `git push` for the calculators and a merged pull request for the blog. If a build fails, the old site stays up. The thing I notice most is the quiet: nothing in my house is a dependency for any of these sites anymore.

The websites no longer need the Oracle VPS or my home server in the path, and that's a lot less to babysit.

Thanks for reading.
