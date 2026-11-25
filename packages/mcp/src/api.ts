// A tiny read-only client for the Courthouse's public API. It only ever sends GET requests to /api/* paths, and
// it never reads or sends an admin token: the public API is all this package can reach.

export const baseUrl = (process.env.PROBATE_API_URL ?? 'http://localhost:8080').replace(/\/+$/, '');

export class CourthouseError extends Error {}

/** GET one public JSON route. Throws CourthouseError with a message that says what to do next. */
export async function getJson(path: string): Promise<unknown> {
  if (!path.startsWith('/api/')) throw new CourthouseError(`Refusing to call ${path}: only the public /api routes are allowed.`);
  let res: Response;
  try {
    res = await fetch(baseUrl + path, { method: 'GET', headers: { accept: 'application/json' }, signal: AbortSignal.timeout(10_000) });
  } catch (e) {
    const why = e instanceof Error ? e.message : String(e);
    throw new CourthouseError(
      `Cannot reach the Probate Courthouse at ${baseUrl} (${why}). Start it (make api) or set PROBATE_API_URL to its address.`,
    );
  }
  if (res.status === 404) throw new CourthouseError(`Not found: ${path}. That generation or trial does not exist yet.`);
  if (!res.ok) throw new CourthouseError(`The Courthouse answered ${res.status} for ${path}.`);
  try {
    return await res.json();
  } catch {
    throw new CourthouseError(`The Courthouse at ${baseUrl} did not return JSON for ${path}. Is PROBATE_API_URL the API, not the website?`);
  }
}
