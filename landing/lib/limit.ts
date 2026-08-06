/**
 * Read a `limit` query parameter, clamped, with a fallback when it is missing.
 *
 * This exists because the obvious version is quietly wrong:
 *
 *     const raw = Number(searchParams.get("limit"));
 *     Number.isFinite(raw) ? clamp(raw) : fallback
 *
 * `searchParams.get` returns null when the parameter is absent, `Number(null)`
 * is 0, and 0 is finite. So a request that asked for no particular limit took
 * the "valid number" branch and got clamped to the minimum of 1, and every
 * caller that omitted the parameter silently received a single row while
 * looking completely healthy.
 */
export function readLimit(
  params: URLSearchParams,
  { fallback, max }: { fallback: number; max: number },
): number {
  const raw = params.get("limit");
  if (raw === null || raw.trim() === "") return fallback;

  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;

  return Math.min(Math.max(Math.trunc(value), 1), max);
}
