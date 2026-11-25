import type { Env } from "./env";

/** Edge rate limits sit in front of the origin so a flood is refused here and never wakes the
 *  Sprite. Uses the Workers rate limiting binding when bound (limits are set in wrangler.jsonc);
 *  otherwise an in-isolate fixed window with the same numbers. Both are approximations: the
 *  binding is per Cloudflare location and eventually consistent, the fallback is per isolate. */
export type Bucket = "read_ip" | "write_ip" | "write_global" | "origin_read_global";

const FALLBACK: Record<Bucket, { limit: number; windowMs: number }> = {
  read_ip: { limit: 120, windowMs: 60_000 },
  write_ip: { limit: 6, windowMs: 60_000 },
  write_global: { limit: 30, windowMs: 60_000 },
  origin_read_global: { limit: 60, windowMs: 60_000 },
};

const BINDING = {
  read_ip: "RL_READ_IP",
  write_ip: "RL_WRITE_IP",
  write_global: "RL_WRITE_GLOBAL",
  origin_read_global: "RL_ORIGIN_READ_GLOBAL",
} as const;

const windows = new Map<string, { start: number; n: number }>();
const MAX_KEYS = 5_000;

export function resetFallbackLimiter(): void {
  windows.clear();
}

/** True when the request is allowed. */
export async function allow(env: Env, bucket: Bucket, key: string, now = Date.now()): Promise<boolean> {
  const binding = env[BINDING[bucket]];
  if (binding) {
    try {
      return (await binding.limit({ key })).success;
    } catch {
      // A broken binding must not open the gate: fall through to the local window.
    }
  }
  const { limit, windowMs } = FALLBACK[bucket];
  const k = `${bucket}:${key}`;
  const w = windows.get(k);
  if (!w || now - w.start >= windowMs) {
    if (windows.size >= MAX_KEYS) {
      for (const [kk, v] of windows) if (now - v.start >= windowMs) windows.delete(kk);
      if (windows.size >= MAX_KEYS) windows.clear();
    }
    windows.set(k, { start: now, n: 1 });
    return true;
  }
  w.n += 1;
  return w.n <= limit;
}
