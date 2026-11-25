import type { Config, Env } from "./env";
import { allow } from "./limiter";
import { callOrigin, isJson, originHeaders, validKey, type OriginResult } from "./origin";
import { finish, jsonError } from "./respond";
import { IMMUTABLE_TTL_S, type Route } from "./routes";
import {
  awakeUntil,
  dropSnapshot,
  getSnapshot,
  markAwake,
  noteOrigin,
  putSnapshot,
  type Snapshot,
} from "./store";

const JSON_HEADERS = { "Content-Type": "application/json; charset=utf-8" };
const FINISHED = new Set(["tried", "died_early"]);

type Fresh =
  | { t: "ok"; snap: Snapshot }
  | { t: "pass"; status: number; body: string; retryAfter: string | null }
  | { t: "fail"; reason: string };

/** Requests in flight in this isolate, so a burst of identical misses makes one origin call. */
const inflight = new Map<string, Promise<Fresh>>();
export function resetInflight(): void {
  inflight.clear();
}

function ttlFor(route: Route, snap: Snapshot, awake: boolean, cfg: Config): number {
  if (snap.status !== 200) return 10; // negative answers (404) are remembered briefly, in memory
  if (snap.immutable) return IMMUTABLE_TTL_S;
  const base = route.ttl ?? 0;
  return awake ? base : Math.max(base, cfg.idleTtlS);
}

async function isAwake(env: Env, cfg: Config): Promise<boolean> {
  return cfg.alwaysOn || (await awakeUntil(env)) > Date.now();
}

function observe(env: Env, ctx: ExecutionContext, cfg: Config, route: Route, body: string): boolean {
  let parsed: unknown;
  try {
    parsed = JSON.parse(body);
  } catch {
    return false;
  }
  if (route.id === "live" && parsed && typeof parsed === "object") {
    const state = (parsed as { state?: unknown }).state;
    if (state !== "idle") markAwake(env, ctx, cfg.awakeWindowS);
  }
  return true;
}

function refresh(env: Env, ctx: ExecutionContext, cfg: Config, route: Route, key: string, ip: string | null): Promise<Fresh> {
  const existing = inflight.get(key);
  if (existing) return existing;
  const p = (async (): Promise<Fresh> => {
    const r = await callOrigin(cfg, key, { method: "GET", headers: originHeaders(cfg, { ip }) }, cfg.readTimeoutMs);
    return interpret(env, ctx, cfg, route, key, r);
  })().finally(() => inflight.delete(key));
  inflight.set(key, p);
  return p;
}

function interpret(env: Env, ctx: ExecutionContext, cfg: Config, route: Route, key: string, r: OriginResult): Fresh {
  if (!r.ok) {
    noteOrigin(env, ctx, false, r.reason);
    console.warn(JSON.stringify({ evt: "origin_fail", route: route.id, reason: r.reason }));
    return { t: "fail", reason: r.reason };
  }
  if (r.status >= 500) {
    noteOrigin(env, ctx, false, `http_${r.status}`);
    return { t: "fail", reason: `http_${r.status}` };
  }
  if (r.status !== 200) {
    // 404 for a generation that does not exist yet, 429 from the origin, ...: pass through.
    noteOrigin(env, ctx, true);
    if (r.status === 404 && isJson(r.contentType)) {
      putSnapshot(env, ctx, `${key}#404`, { status: 404, body: r.body, fetchedAt: Date.now(), immutable: false }, cfg.staleMaxAgeS);
    }
    return { t: "pass", status: r.status, body: r.body, retryAfter: r.retryAfter };
  }
  // The origin has a catch-all that serves HTML for unknown paths. Only real JSON is ever stored.
  if (!isJson(r.contentType) || !observe(env, ctx, cfg, route, r.body)) {
    noteOrigin(env, ctx, false, "not_json");
    return { t: "fail", reason: "not_json" };
  }
  noteOrigin(env, ctx, true);
  let immutable = false;
  if (route.id === "generation") {
    try {
      immutable = FINISHED.has((JSON.parse(r.body) as { state?: string }).state ?? "");
    } catch {
      /* not immutable */
    }
  }
  const snap: Snapshot = { status: 200, body: r.body, fetchedAt: Date.now(), immutable };
  putSnapshot(env, ctx, key, snap, cfg.staleMaxAgeS);
  return { t: "ok", snap };
}

function fresh(request: Request, cfg: Config, snap: Snapshot, how: "HIT" | "MISS" | "SWR", ttl: number): Response {
  const age = Math.max(0, Math.floor((Date.now() - snap.fetchedAt) / 1000));
  const maxAge = snap.immutable ? 3_600 : Math.min(5, Math.max(0, ttl - age));
  return finish(request, cfg, {
    status: snap.status,
    body: snap.body,
    headers: {
      ...JSON_HEADERS,
      "Cache-Control": snap.status === 200 ? `public, max-age=${maxAge}${snap.immutable ? ", immutable" : ""}` : "no-store",
      "X-Edge-Cache": how,
      Age: String(age),
    },
  });
}

/** Last known good copy. The body is byte for byte what the origin sent; staleness is only ever
 *  signalled in headers. */
function stale(request: Request, cfg: Config, snap: Snapshot, reason: string): Response {
  return finish(request, cfg, {
    status: 200,
    body: snap.body,
    headers: {
      ...JSON_HEADERS,
      "Cache-Control": "public, max-age=5",
      "X-Edge-Cache": "STALE",
      "X-Probate-Stale": "1",
      "X-Probate-Stale-Since": new Date(snap.fetchedAt).toISOString(),
      "X-Probate-Stale-Reason": reason,
      Age: String(Math.max(0, Math.floor((Date.now() - snap.fetchedAt) / 1000))),
    },
  });
}

function failure(request: Request, cfg: Config, reason: string): Response {
  if (reason === "timeout") {
    return jsonError(request, cfg, 504, "origin_timeout", "The Courthouse is waking up or slow. Try again in a few seconds.", { "Retry-After": "5" });
  }
  return jsonError(request, cfg, 502, "origin_unavailable", "The Courthouse is not reachable right now.", { "Retry-After": "10" });
}

export async function handleRead(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
  cfg: Config,
  route: Route,
  key: string,
  ip: string | null,
): Promise<Response> {
  const awake = await isAwake(env, cfg);

  // A judge's own view of /api/live depends on the key, so it is never cached or shared. Only
  // when the Sprite is already awake; otherwise the shared snapshot answers and nothing wakes.
  const judgeKey = route.judge ? request.headers.get("x-probate-key") : null;
  if (judgeKey && awake && validKey(judgeKey)) {
    const r = await callOrigin(cfg, key, { method: "GET", headers: originHeaders(cfg, { ip, key: judgeKey }) }, cfg.readTimeoutMs);
    if (r.ok && r.status < 500 && isJson(r.contentType)) {
      noteOrigin(env, ctx, true);
      return finish(request, cfg, {
        status: r.status,
        body: r.body,
        headers: { ...JSON_HEADERS, "Cache-Control": "no-store", "X-Edge-Cache": "BYPASS", Vary: "Origin, X-Probate-Key" },
      });
    }
    // fall through to the shared snapshot
  }

  let snap = await getSnapshot(env, key);
  if (snap && Date.now() - snap.fetchedAt > cfg.staleMaxAgeS * 1000) snap = null;
  const neg = await getSnapshot(env, `${key}#404`);
  if (neg && Date.now() - neg.fetchedAt < 10_000) return fresh(request, cfg, neg, "HIT", 10);

  if (snap) {
    const ttl = ttlFor(route, snap, awake, cfg);
    const age = (Date.now() - snap.fetchedAt) / 1000;
    if (age < ttl) return fresh(request, cfg, snap, "HIT", ttl);
    if (awake && route.swr && age < ttl + route.swr) {
      // The Sprite is awake anyway: answer now, refresh behind the scenes.
      if (await allow(env, "origin_read_global", "all")) ctx.waitUntil(refresh(env, ctx, cfg, route, key, ip).then(() => undefined));
      return fresh(request, cfg, snap, "SWR", ttl);
    }
  }

  // Going to the origin from here on. A global budget keeps a spray of distinct URLs from waking it.
  if (!(await allow(env, "origin_read_global", "all"))) {
    if (snap) return stale(request, cfg, snap, "rate_limited");
    return jsonError(request, cfg, 429, "rate_limited", "Too many requests. Please slow down.", { "Retry-After": "30", "X-Edge-Limit-Scope": "global" });
  }

  const p = refresh(env, ctx, cfg, route, key, ip);
  let outcome: Fresh | "slow";
  if (snap) {
    // We have something to show: do not make a visitor wait on a cold start.
    let timer: ReturnType<typeof setTimeout> | undefined;
    const slow = new Promise<"slow">((res) => {
      timer = setTimeout(() => res("slow"), cfg.slowMs);
    });
    outcome = await Promise.race([p, slow]);
    clearTimeout(timer);
    if (outcome === "slow") {
      ctx.waitUntil(p.then(() => undefined)); // let the wake-up finish and update the snapshot
      return stale(request, cfg, snap, "slow");
    }
  } else {
    outcome = await p;
  }

  if (outcome.t === "ok") return fresh(request, cfg, outcome.snap, "MISS", ttlFor(route, outcome.snap, true, cfg));
  if (outcome.t === "pass") {
    return finish(request, cfg, {
      status: outcome.status,
      body: outcome.body,
      headers: { ...JSON_HEADERS, "Cache-Control": "no-store", "X-Edge-Cache": "MISS", ...(outcome.retryAfter ? { "Retry-After": outcome.retryAfter } : {}) },
    });
  }
  if (snap) return stale(request, cfg, snap, outcome.reason === "timeout" ? "timeout" : "error");
  return failure(request, cfg, outcome.reason);
}

// ---------------------------------------------------------------------------------------------
// Writes: the only requests that are meant to wake the origin.
// ---------------------------------------------------------------------------------------------

type Body = { bytes: Uint8Array<ArrayBuffer> } | "too_large";

async function readCapped(req: Request, max: number): Promise<Body> {
  const cl = req.headers.get("content-length");
  if (cl !== null && Number(cl) > max) return "too_large";
  if (!req.body) return { bytes: new Uint8Array(0) };
  const reader = req.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > max) {
      await reader.cancel().catch(() => {});
      return "too_large";
    }
    chunks.push(value);
  }
  const bytes = new Uint8Array(total);
  let o = 0;
  for (const c of chunks) {
    bytes.set(c, o);
    o += c.byteLength;
  }
  return { bytes };
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function handleWrite(
  request: Request,
  env: Env,
  ctx: ExecutionContext,
  cfg: Config,
  route: Route,
  ip: string | null,
): Promise<Response> {
  const url = new URL(request.url);
  const isGet = route.method === "GET";

  let key: string | null = null;
  if (route.judge) {
    key = request.headers.get("x-probate-key");
    if (key !== null && !validKey(key)) return jsonError(request, cfg, 400, "bad_key_header", "The X-Probate-Key header is malformed.");
  }
  if (isGet && !key) {
    // Nothing to check without a key: answer at the edge so it never wakes the Sprite.
    return jsonError(request, cfg, 401, "key_required", "A judge key is required.");
  }

  let bytes: Uint8Array<ArrayBuffer> = new Uint8Array(0);
  let contentType: string | null = null;
  if (!isGet) {
    const read = await readCapped(request, route.maxBody ?? 4_096);
    if (read === "too_large") return jsonError(request, cfg, 413, "payload_too_large", `The request body may be at most ${route.maxBody} bytes.`);
    bytes = read.bytes;
    const ct = request.headers.get("content-type") ?? "";
    const need = route.body !== "none-or-json" || bytes.length > 0;
    if (need) {
      if (!isJson(ct)) return jsonError(request, cfg, 415, "unsupported_media_type", "Send application/json.");
      let parsed: unknown;
      try {
        parsed = JSON.parse(new TextDecoder("utf-8", { fatal: true, ignoreBOM: false }).decode(bytes));
      } catch {
        return jsonError(request, cfg, 400, "invalid_json", "The request body is not valid JSON.");
      }
      const isObj = typeof parsed === "object" && parsed !== null && !Array.isArray(parsed);
      if (route.body !== "none-or-json" && !isObj) return jsonError(request, cfg, 400, "invalid_body", "Expected a JSON object.");
      if (route.body === "question") {
        const q = (parsed as { question?: unknown }).question;
        if (typeof q !== "string" || q.trim().length === 0 || q.length > 2_000) {
          return jsonError(request, cfg, 400, "invalid_body", "`question` must be a string of 1 to 2000 characters.");
        }
      }
      contentType = "application/json";
    }
  }

  // Short retry policy for a cold start: retry when the connection fails or a proxy answers
  // 502/503/504 with a non-JSON page. Never retry a timeout (the write may have landed).
  const deadline = Date.now() + cfg.writeTimeoutMs;
  let result: OriginResult = { ok: false, reason: "network" };
  const headers = originHeaders(cfg, { ip, key: route.judge ? key : null, contentType });
  for (let attempt = 0; attempt <= cfg.writeRetries; attempt++) {
    const left = deadline - Date.now();
    if (left <= 0) {
      result = { ok: false, reason: "timeout" };
      break;
    }
    result = await callOrigin(cfg, url.pathname, { method: route.method, headers, body: bytes }, left);
    const transient =
      (!result.ok && result.reason === "network") ||
      (result.ok && [502, 503, 504].includes(result.status) && !isJson(result.contentType));
    if (!transient) break;
    if (attempt < cfg.writeRetries) await sleep(Math.min(400 * 2 ** attempt, Math.max(0, deadline - Date.now())));
  }

  if (!result.ok) {
    noteOrigin(env, ctx, false, result.reason);
    console.warn(JSON.stringify({ evt: "origin_fail", route: route.id, reason: result.reason }));
    if (result.reason === "timeout") {
      return jsonError(request, cfg, 504, "origin_timeout", "The Courthouse is waking up. Try again in a few seconds.", { "Retry-After": "5" });
    }
    return jsonError(request, cfg, 502, "origin_unavailable", "The Courthouse is not reachable right now.", { "Retry-After": "10" });
  }
  if (result.status >= 502 && !isJson(result.contentType)) {
    noteOrigin(env, ctx, false, `http_${result.status}`);
    return jsonError(request, cfg, 502, "origin_unavailable", "The Courthouse is not reachable right now.", { "Retry-After": "10" });
  }

  // The origin app answered, so the Sprite is awake: reads may refresh at base TTLs for a while.
  noteOrigin(env, ctx, true);
  markAwake(env, ctx, cfg.awakeWindowS);
  if (result.status < 400 && route.method === "POST") {
    if (route.id === "ask") dropSnapshot(env, ctx, url.pathname.replace(/\/ask$/, ""));
    if (route.id === "lives") dropSnapshot(env, ctx, "/api/live");
  }
  return finish(request, cfg, {
    status: result.status,
    body: isJson(result.contentType) ? result.body : JSON.stringify({ error: "bad_origin_response", message: "Unexpected response from the Courthouse." }),
    headers: {
      ...JSON_HEADERS,
      "Cache-Control": "no-store",
      "X-Edge-Cache": "BYPASS",
      Vary: "Origin, X-Probate-Key",
      ...(result.retryAfter ? { "Retry-After": result.retryAfter } : {}),
    },
  });
}
