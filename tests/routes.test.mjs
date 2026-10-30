// Checks functions/_lib/wordpress.js against what nginx did, and that
// static/_routes.json sends those paths, and only those, to a Function.
// Run: node --test tests/*.test.mjs   (after `zola build`, for the sitemap check)
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { match } from '../functions/_lib/wordpress.js';

const routes = JSON.parse(fs.readFileSync(new URL('../static/_routes.json', import.meta.url)));
const glob = (p) => new RegExp('^' + p.replace(/[.+?^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*') + '$');
const include = routes.include.map(glob);
const exclude = routes.exclude.map(glob);
const routed = (path) => include.some((r) => r.test(path)) && !exclude.some((r) => r.test(path));

// path -> [status, Location] as nginx returned it.
const NGINX = {
  '/comments/feed': [410], '/comments/feed/': [410],
  '/sample-page': [410], '/sample-page/': [410],
  '/hello-world/feed': [410], '/hello-world/feed/': [410],
  '/category/smart-home/feed/': [410], '/tag/zigbee/feed': [410],
  '/wp-sitemap.xml': [301, '/sitemap.xml'],
  '/wp-sitemap-posts-post-1.xml': [301, '/sitemap.xml'],
  '/wp-sitemap-taxonomies-category-1.xml': [301, '/sitemap.xml'],
  '/2021': [301, '/archive/'], '/2021/': [301, '/archive/'],
  '/2021/09': [301, '/archive/'], '/2024/09/': [301, '/archive/'],
  '/2021/09/15': [301, '/archive/'], '/2021/09/15/': [301, '/archive/'],
  '/wp-admin': [410], '/wp-admin/': [410], '/wp-admin/admin-ajax.php': [410],
  '/wp-includes/js/jquery.js': [410], '/wp-json/wp/v2/users': [410], '/wp-json': [410],
  '/wp-login.php': [410], '/xmlrpc.php': [410], '/wp-cron.php': [410],
  '/wp-config.php': [410], '/wp-config-sample.php': [410],
  '/readme.html': [410], '/license.txt': [410], '/wp-content/debug.log': [410],
  '/wp-content/plugins/akismet/readme.txt': [410],
  '/wp-content/themes/twentytwentyone/style.css': [410],
};

test('rules match nginx', () => {
  for (const [path, [status, location]] of Object.entries(NGINX)) {
    const res = match(path);
    assert.ok(res, `${path}: no rule matched`);
    assert.equal(res.status, status, path);
    assert.equal(res.headers.get('Location'), location ?? null, path);
  }
});

test('every rule path reaches the Function', () => {
  for (const path of Object.keys(NGINX)) assert.ok(routed(path), `${path} not in _routes.json`);
  for (const path of ['/js/vx.js', '/vx/event', '/api/event']) assert.ok(routed(path), path);
});

test('uploads, pages and _redirects paths are served without a Function', () => {
  const paths = [
    '/', '/about/', '/archive/', '/page/2/', '/main.css', '/rss.xml',
    '/wp-content/uploads/2021/11/fire-tablet-mount.stl',
    '/feed', '/feed/', '/rss/', '/feed/atom/', '/author/jonkatz/', '/category/uncategorized/',
  ];
  const sitemap = new URL('../public/sitemap.xml', import.meta.url);
  if (fs.existsSync(sitemap)) {
    for (const [, loc] of fs.readFileSync(sitemap, 'utf8').matchAll(/<loc>([^<]+)<\/loc>/g)) {
      paths.push(new URL(loc, 'https://x/').pathname);
    }
  }
  for (const path of paths) {
    // A page under /1* or /2* is routed but must fall through untouched.
    assert.ok(!routed(path) || match(path) === null, `${path} would be caught by the Function`);
    if (!/^\/[12]/.test(path)) assert.ok(!routed(path), `${path} runs a Function needlessly`);
  }
  assert.equal(match('/2026-in-review/'), null);
});
