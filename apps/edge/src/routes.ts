/** The allowlist. A request is proxied only if it matches a row here; everything else is a 404
 *  generated at the edge. Paths are matched against the raw pathname with a strict character set,
 *  so encoded slashes, dot segments and double slashes never match. */

export type Kind = "read" | "write" | "judge-read";

export interface Route {
  id: string;
  method: "GET" | "POST";
  kind: Kind;
  re: RegExp;
  /** Seconds a snapshot counts as fresh while the origin is awake. */
  ttl?: number;
  /** Extra seconds a just-expired snapshot may be served while a refresh runs (awake only). */
  swr?: number;
  /** X-Probate-Key is forwarded on this route. */
  judge?: boolean;
  /** Maximum request body in bytes (writes). */
  maxBody?: number;
  /** Required shape of the request body (writes). */
  body?: "none-or-json" | "json-object" | "question";
}

export const IMMUTABLE_TTL_S = 86_400;

export const ROUTES: Route[] = [
  { id: "healthz", method: "GET", kind: "read", re: /^\/healthz$/, ttl: 30, swr: 30 },
  { id: "summary", method: "GET", kind: "read", re: /^\/api\/summary$/, ttl: 15, swr: 30 },
  { id: "live", method: "GET", kind: "read", re: /^\/api\/live$/, ttl: 5, swr: 10, judge: true },
  { id: "genome", method: "GET", kind: "read", re: /^\/api\/genome$/, ttl: 60, swr: 120 },
  { id: "evidence", method: "GET", kind: "read", re: /^\/api\/evidence$/, ttl: 60, swr: 120 },
  { id: "events", method: "GET", kind: "read", re: /^\/api\/events$/, ttl: 10, swr: 20 },
  { id: "trial-latest", method: "GET", kind: "read", re: /^\/api\/trials\/latest$/, ttl: 15, swr: 30 },
  { id: "trial", method: "GET", kind: "read", re: /^\/api\/trials\/\d{1,6}$/, ttl: 3_600, swr: 600 },
  { id: "generation", method: "GET", kind: "read", re: /^\/api\/generations\/\d{1,6}$/, ttl: 15, swr: 30 },
  { id: "judge-status", method: "GET", kind: "judge-read", re: /^\/api\/judge\/status$/, judge: true },
  { id: "lives", method: "POST", kind: "write", re: /^\/api\/lives$/, judge: true, maxBody: 4_096, body: "none-or-json" },
  { id: "attacks", method: "POST", kind: "write", re: /^\/api\/attacks$/, judge: true, maxBody: 8_192, body: "json-object" },
  { id: "ask", method: "POST", kind: "write", re: /^\/api\/generations\/\d{1,6}\/ask$/, maxBody: 4_096, body: "question" },
];

export const PATH_OK = /^\/[A-Za-z0-9/_.-]{0,198}$/;

export interface Match {
  route?: Route;
  /** Path is known but not with this method. */
  allow?: string[];
}

export function match(method: string, pathname: string): Match {
  if (!PATH_OK.test(pathname) || pathname.includes("..") || pathname.includes("//")) return {};
  const hits = ROUTES.filter((r) => r.re.test(pathname));
  if (hits.length === 0) return {};
  const m = method === "HEAD" ? "GET" : method;
  const route = hits.find((r) => r.method === m);
  return route ? { route } : { allow: [...new Set(hits.map((r) => r.method))] };
}

/** Canonical cache key. Only /api/events takes a query (`since`, digits). Null = bad query. */
export function cacheKey(route: Route, pathname: string, search: URLSearchParams): string | null {
  if (route.id === "events") {
    const since = search.get("since");
    if (since === null) return pathname;
    return /^\d{1,12}$/.test(since) ? `${pathname}?since=${since}` : null;
  }
  return pathname;
}
