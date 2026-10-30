// POST /api/event: Plausible's default endpoint, for a script that ignores
// the one set in static/js/vxinit.js.
export { forwardEvent as onRequestPost } from '../_lib/plausible.js';
