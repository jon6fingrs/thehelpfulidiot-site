// Forwards a Plausible event to its /api/event.
//
// The visitor's real IP must go along in X-Forwarded-For; without it
// Plausible counts every visitor as one and its bot filter may drop events
// silently.

export async function forwardEvent({ request, env }) {
  const headers = new Headers({
    'Content-Type': request.headers.get('Content-Type') || 'text/plain',
    'User-Agent': request.headers.get('User-Agent') || '',
    'X-Forwarded-For': request.headers.get('CF-Connecting-IP') || '',
    'X-Forwarded-Proto': 'https',
    'X-Forwarded-Host': new URL(request.url).host,
  });
  const upstream = await fetch(`https://${env.PLAUSIBLE_HOST}/api/event`, {
    method: 'POST',
    headers,
    body: request.body,
  });
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { 'Content-Type': upstream.headers.get('Content-Type') || 'text/plain' },
  });
}
