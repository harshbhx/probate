import type { Env } from "./env";

/** A stored copy of one origin response. The body is the origin's JSON text, untouched. */
export interface Snapshot {
  status: number;
  body: string;
  /** ms epoch of the origin fetch that produced it. */
  fetchedAt: number;
  /** Finished generations never change, so they get a long TTL. */
  immutable: boolean;
}

export interface OriginMeta {
  okAt?: number;
  errAt?: number;
  errKind?: string;
}

const L1_MAX = 256;
const l1 = new Map<string, Snapshot>();
const kvWrittenAt = new Map<string, number>();
// KV allows about one write per second per key and the free plan 1,000 writes a day in total.
const MIN_CHANGED_WRITE_MS = 20_000;
const MIN_UNCHANGED_WRITE_MS = 600_000;

let metaOrigin: OriginMeta = {};
let awakeUntilL1 = 0;

export function resetStore(): void {
  l1.clear();
  kvWrittenAt.clear();
  metaOrigin = {};
  awakeUntilL1 = 0;
}

const snapKey = (k: string) => `snap:${k}`;
/** Keys with a query string (events?since=N) or a negative marker are unbounded, so they live in memory only. */
const persistent = (k: string) => !k.includes("?") && !k.includes("#");

function remember(key: string, s: Snapshot): void {
  if (l1.size >= L1_MAX && !l1.has(key)) l1.delete(l1.keys().next().value as string);
  l1.set(key, s);
}

export async function getSnapshot(env: Env, key: string): Promise<Snapshot | null> {
  const mem = l1.get(key);
  if (mem) return mem;
  if (!env.SNAPSHOTS || !persistent(key)) return null;
  try {
    const s = await env.SNAPSHOTS.get<Snapshot>(snapKey(key), "json");
    if (s && typeof s.body === "string" && typeof s.fetchedAt === "number") {
      remember(key, s);
      return s;
    }
  } catch {
    /* KV unavailable: behave as if empty. */
  }
  return null;
}

/** Record a fresh origin response. Memory is always updated; KV writes are throttled. */
export function putSnapshot(
  env: Env,
  ctx: ExecutionContext,
  key: string,
  s: Snapshot,
  staleMaxAgeS: number,
  now = Date.now(),
): void {
  const prev = l1.get(key);
  remember(key, s);
  if (!env.SNAPSHOTS || !persistent(key)) return;
  const last = kvWrittenAt.get(key) ?? 0;
  const changed = !prev || prev.body !== s.body;
  if (prev && now - last < (changed ? MIN_CHANGED_WRITE_MS : MIN_UNCHANGED_WRITE_MS)) return;
  kvWrittenAt.set(key, now);
  ctx.waitUntil(
    env.SNAPSHOTS.put(snapKey(key), JSON.stringify(s), { expirationTtl: Math.max(60, staleMaxAgeS) }).catch(() => {}),
  );
}

export function dropSnapshot(env: Env, ctx: ExecutionContext, key: string): void {
  l1.delete(key);
  kvWrittenAt.delete(key);
  if (env.SNAPSHOTS && persistent(key)) ctx.waitUntil(env.SNAPSHOTS.delete(snapKey(key)).catch(() => {}));
}

// ---- awake tracking: did something real reach the origin recently? ----------------------

export async function awakeUntil(env: Env): Promise<number> {
  if (awakeUntilL1 > Date.now() || !env.SNAPSHOTS) return awakeUntilL1;
  try {
    const v = Number(await env.SNAPSHOTS.get("meta:awake_until"));
    if (Number.isFinite(v) && v > awakeUntilL1) awakeUntilL1 = v;
  } catch {
    /* ignore */
  }
  return awakeUntilL1;
}

export function markAwake(env: Env, ctx: ExecutionContext, windowS: number, now = Date.now()): void {
  const until = now + windowS * 1000;
  if (until <= awakeUntilL1 + 30_000) return; // not a KV write per request
  awakeUntilL1 = until;
  if (env.SNAPSHOTS) {
    ctx.waitUntil(
      env.SNAPSHOTS.put("meta:awake_until", String(until), { expirationTtl: Math.max(60, windowS + 60) }).catch(() => {}),
    );
  }
}

// ---- origin reachability, as last observed (never probed) -------------------------------

export async function getOriginMeta(env: Env): Promise<OriginMeta> {
  if (env.SNAPSHOTS && metaOrigin.okAt === undefined && metaOrigin.errAt === undefined) {
    try {
      const m = await env.SNAPSHOTS.get<OriginMeta>("meta:origin", "json");
      if (m) metaOrigin = m;
    } catch {
      /* ignore */
    }
  }
  return metaOrigin;
}

export function noteOrigin(env: Env, ctx: ExecutionContext, ok: boolean, errKind?: string, now = Date.now()): void {
  const prev = metaOrigin;
  const first = prev.okAt === undefined && prev.errAt === undefined;
  const flip = ok ? (prev.errAt ?? 0) > (prev.okAt ?? 0) : (prev.okAt ?? 0) > (prev.errAt ?? 0);
  const old = now - ((ok ? prev.okAt : prev.errAt) ?? 0) > 600_000;
  metaOrigin = ok ? { ...prev, okAt: now } : { ...prev, errAt: now, errKind };
  if (env.SNAPSHOTS && (first || flip || old)) {
    ctx.waitUntil(env.SNAPSHOTS.put("meta:origin", JSON.stringify(metaOrigin), { expirationTtl: 2_592_000 }).catch(() => {}));
  }
}
