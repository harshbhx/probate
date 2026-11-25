import type { Config, Env } from "./env";
import { finish } from "./respond";
import { awakeUntil, getOriginMeta, getSnapshot } from "./store";

const KEYS: Array<[string, string, number]> = [
  ["healthz", "/healthz", 30],
  ["summary", "/api/summary", 15],
  ["live", "/api/live", 5],
  ["genome", "/api/genome", 60],
  ["evidence", "/api/evidence", 60],
  ["events", "/api/events", 10],
  ["trial_latest", "/api/trials/latest", 15],
];

const iso = (ms?: number) => (ms ? new Date(ms).toISOString() : null);

/** Reports what the edge already knows. It never calls the origin, so polling it cannot wake the
 *  Sprite. "Reachable" means: what the last real request saw, not a live probe. */
export async function handleStatus(request: Request, env: Env, cfg: Config): Promise<Response> {
  const now = Date.now();
  const meta = await getOriginMeta(env);
  const until = cfg.alwaysOn ? 0 : await awakeUntil(env);
  const snapshots: Record<string, unknown> = {};
  for (const [name, key, ttl] of KEYS) {
    const s = await getSnapshot(env, key);
    snapshots[name] = s
      ? { present: true, fetched_at: iso(s.fetchedAt), age_s: Math.floor((now - s.fetchedAt) / 1000), base_ttl_s: ttl, fresh_while_awake: (now - s.fetchedAt) / 1000 < ttl }
      : { present: false };
  }
  const lastOk = meta.okAt ?? 0;
  const lastErr = meta.errAt ?? 0;
  const reachable = lastOk === 0 && lastErr === 0 ? "unknown" : lastOk >= lastErr ? "yes" : "no";
  const body = {
    ok: cfg.origin !== null,
    service: "probate-edge",
    now: iso(now),
    note: "Reported from edge state only. This endpoint never calls the origin.",
    origin: {
      configured: cfg.origin !== null,
      mode: cfg.alwaysOn ? "always_on" : "on_demand",
      believed_awake: cfg.alwaysOn || until > now,
      awake_until: until > 0 ? iso(until) : null,
      last_seen_reachable: reachable,
      last_ok_at: iso(meta.okAt),
      last_error_at: iso(meta.errAt),
      last_error_kind: meta.errKind ?? null,
    },
    kv_bound: env.SNAPSHOTS !== undefined,
    snapshots,
  };
  return finish(request, cfg, {
    status: cfg.origin ? 200 : 503,
    body: JSON.stringify(body),
    headers: { "Cache-Control": "no-store" },
  });
}
