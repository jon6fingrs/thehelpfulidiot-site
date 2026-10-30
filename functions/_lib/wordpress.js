// What nginx did for leftover WordPress URLs, as one function. Only the
// paths listed in static/_routes.json reach it; everything else is served
// straight from the build. Plain path-to-path 301s (feeds, /author/,
// /category/uncategorized) are in static/_redirects instead.
//
// Order follows nginx: exact matches, then prefixes, then the regexes in
// file order. A path that matches nothing (e.g. a future post whose slug
// starts with "20") falls through to the static site.

const EXACT_GONE = new Set([
  '/comments/feed', '/comments/feed/',
  '/sample-page', '/sample-page/',
  '/wp-login.php', '/xmlrpc.php', '/wp-cron.php',
  '/wp-config.php', '/wp-config-sample.php',
  '/readme.html', '/license.txt', '/wp-content/debug.log',
]);

const PREFIX_GONE = ['/wp-admin', '/wp-includes', '/wp-json'];

const RULES = [
  // Per-post and per-taxonomy comment feeds: /<slug>/feed/.
  [/^\/.+\/feed\/?$/, 410],
  // WordPress's sitemap and its sub-sitemaps.
  [/^\/wp-sitemap.*\.xml$/, 301, '/sitemap.xml'],
  // Monthly and daily date archives.
  [/^\/[0-9]{4}(\/[0-9]{2})?(\/[0-9]{2})?\/?$/, 301, '/archive/'],
  // Uploads stay; only plugin and theme files are gone.
  [/^\/wp-content\/(plugins|themes)\//i, 410],
];

// _headers does not apply to Function responses, so the security headers
// Traefik added on the old server are repeated here (keep in step with
// static/_headers).
const SECURITY = {
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'SAMEORIGIN',
  'Referrer-Policy': 'strict-origin-when-cross-origin',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
};

// Same body nginx's default 410 page had.
const GONE_HTML = '<html>\r\n<head><title>410 Gone</title></head>\r\n<body>\r\n<center><h1>410 Gone</h1></center>\r\n</body>\r\n</html>\r\n';

function gone() {
  return new Response(GONE_HTML, { status: 410, headers: { ...SECURITY, 'Content-Type': 'text/html; charset=utf-8' } });
}

// Relative Location, like nginx's `absolute_redirect off`.
function moved(to) {
  return new Response(null, { status: 301, headers: { ...SECURITY, 'Content-Type': 'text/html', Location: to } });
}

// Returns a Response, or null when no rule matches.
export function match(pathname) {
  if (EXACT_GONE.has(pathname)) return gone();
  if (PREFIX_GONE.some((p) => pathname.startsWith(p))) return gone();
  for (const [re, status, to] of RULES) {
    if (re.test(pathname)) return status === 410 ? gone() : moved(to);
  }
  return null;
}

export function wordpress({ request, next }) {
  return match(new URL(request.url).pathname) || next();
}
