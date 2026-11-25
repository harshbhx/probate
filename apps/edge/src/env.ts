/** Everything the Worker reads from its environment. All of it is optional at the type level so a
 *  missing value fails closed at runtime instead of crashing at import. */
export interface Env {
  /** Secret/var. Base URL of the Courthouse Sprite, e.g. https://probate-courthouse-xxxx.sprites.app */
  ORIGIN_URL?: string;
  /** Secret. Sent to the origin as `Authorization: Bearer ...` when the Sprite URL is private. */
  ORIGIN_AUTH_TOKEN?: string;
  /** Comma separated browser origins allowed by CORS. `https://*.example.com` wildcards allowed. */
  ALLOWED_ORIGINS?: string;
  /** Secret. Shared with the Courthouse (`PROBATE_EDGE_TOKEN`, same value). Sent to the origin as
   *  `X-Probate-Edge` next to `X-Probate-Client-IP` so the Courthouse can tell real visitors apart.
   *  Never logged, never returned, never sent anywhere but the origin. */
  EDGE_TOKEN?: string;
  /** "required": every proxied request must carry the edge token, and without the `EDGE_TOKEN`
   *  secret the Worker answers 503 instead of passing requests through unauthenticated.
   *  "off" (default when unset): the token is sent only if `EDGE_TOKEN` happens to be set. */
  EDGE_TOKEN_MODE?: string;
  /** "on_demand" (default): the Sprite sleeps, reads are served from snapshots while it is idle.
   *  "always_on": the Sprite free-runs, so the base TTLs apply all the time. */
  ORIGIN_MODE?: string;

  /** KV namespace holding last-known-good snapshots and small meta keys. Optional: without it the
   *  Worker keeps snapshots in isolate memory only. */
  SNAPSHOTS?: KVNamespace;

  /** Workers rate limiting bindings. Optional: an in-isolate fixed window is the fallback. */
  RL_READ_IP?: RateLimit;
  RL_WRITE_IP?: RateLimit;
  RL_WRITE_GLOBAL?: RateLimit;
  RL_ORIGIN_READ_GLOBAL?: RateLimit;

  READ_TIMEOUT_MS?: string;
  SLOW_MS?: string;
  WRITE_TIMEOUT_MS?: string;
  WRITE_RETRIES?: string;
  IDLE_TTL_S?: string;
  AWAKE_WINDOW_S?: string;
  STALE_MAX_AGE_S?: string;
}

export interface Config {
  origin: URL | null;
  originToken: string | null;
  edgeToken: string | null;
  /** True when EDGE_TOKEN_MODE=required. */
  edgeTokenRequired: boolean;
  allowedOrigins: string[];
  alwaysOn: boolean;
  readTimeoutMs: number;
  slowMs: number;
  writeTimeoutMs: number;
  writeRetries: number;
  idleTtlS: number;
  awakeWindowS: number;
  staleMaxAgeS: number;
}

function num(v: string | undefined, d: number, min = 0, max = Number.MAX_SAFE_INTEGER): number {
  if (v === undefined || v.trim() === "") return d;
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : d;
}

/** Fixed origin only. https, or http for loopback (local dev). No path, no credentials. */
export function parseOrigin(raw: string | undefined): URL | null {
  if (!raw) return null;
  let u: URL;
  try {
    u = new URL(raw.trim());
  } catch {
    return null;
  }
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(u.hostname);
  if (u.protocol !== "https:" && !(u.protocol === "http:" && loopback)) return null;
  if (u.username || u.password || u.search || u.hash) return null;
  if (u.pathname !== "/" && u.pathname !== "") return null;
  return new URL(u.origin);
}

export function loadConfig(env: Env): Config {
  return {
    origin: parseOrigin(env.ORIGIN_URL),
    originToken: env.ORIGIN_AUTH_TOKEN?.trim() || null,
    edgeToken: env.EDGE_TOKEN?.trim() || null,
    edgeTokenRequired: (env.EDGE_TOKEN_MODE ?? "off").trim().toLowerCase() === "required",
    allowedOrigins: (env.ALLOWED_ORIGINS ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    alwaysOn: (env.ORIGIN_MODE ?? "on_demand").trim() === "always_on",
    readTimeoutMs: num(env.READ_TIMEOUT_MS, 10_000, 1, 25_000),
    slowMs: num(env.SLOW_MS, 2_500, 1, 25_000),
    writeTimeoutMs: num(env.WRITE_TIMEOUT_MS, 20_000, 1, 28_000),
    writeRetries: num(env.WRITE_RETRIES, 2, 0, 3),
    idleTtlS: num(env.IDLE_TTL_S, 900, 0, 86_400),
    awakeWindowS: num(env.AWAKE_WINDOW_S, 1_200, 0, 86_400),
    staleMaxAgeS: num(env.STALE_MAX_AGE_S, 604_800, 60, 2_592_000),
  };
}
