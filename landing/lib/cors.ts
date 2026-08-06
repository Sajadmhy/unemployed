/**
 * Open to any origin on purpose: the local app reads these boards from
 * localhost:3000, and none of this data is worth protecting behind CORS.
 * No credentials are involved, which is required anyway since a wildcard
 * origin and credentials cannot be combined.
 */
export const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
  "Access-Control-Max-Age": "86400",
};

// Browsers always get fresh data; the edge absorbs bursts.
export const CACHE = {
  "Cache-Control": "no-store, max-age=0",
  "CDN-Cache-Control": "public, s-maxage=30",
};

export function corsOptions() {
  return new Response(null, { status: 204, headers: CORS });
}
