import type { Config } from "./env";

/** The only code that talks to the origin. The target is always `cfg.origin` plus a path that has
 *  already passed the route allowlist, so the Worker cannot be steered at another host. */

const MAX_RESPONSE_BYTES = 2 * 1024 * 1024;
const KEY_RE = /^[\x21-\x7e]{1,256}$/;

export const validKey = (k: string): boolean => KEY_RE.test(k);

export interface OriginResponse {
  ok: true;
  status: number;
  body: string;
  contentType: string;
  retryAfter: string | null;
}
export interface OriginFailure {
  ok: false;
  reason: "timeout" | "network" | "bad_gateway";
}
export type OriginResult = OriginResponse | OriginFailure;

/** Headers are built from scratch, never copied from the visitor: cookies, Authorization,
 *  X-Probate-Admin and anything else the visitor sent cannot reach the Courthouse. */
export function originHeaders(
  cfg: Config,
  o: { ip: string | null; key?: string | null; contentType?: string | null },
): Headers {
  const h = new Headers({
    Accept: "application/json",
    "User-Agent": "probate-edge/1",
    "X-Forwarded-Proto": "https",
  });
  if (o.ip) h.set("X-Forwarded-For", o.ip);
  // Visitor-supplied X-Probate-Edge / X-Probate-Client-IP never get here (nothing is copied), so
  // these two are the only ones the origin can ever see. Without a CF-Connecting-IP the edge sends
  // no client-IP header (the origin then falls back to X-Forwarded-For).
  if (cfg.edgeToken) {
    h.set("X-Probate-Edge", cfg.edgeToken);
    if (o.ip) h.set("X-Probate-Client-IP", o.ip);
  }
  if (o.key) h.set("X-Probate-Key", o.key);
  if (o.contentType) h.set("Content-Type", o.contentType);
  if (cfg.originToken) h.set("Authorization", `Bearer ${cfg.originToken}`);
  return h;
}

export async function callOrigin(
  cfg: Config,
  path: string,
  init: { method: "GET" | "POST"; headers: Headers; body?: Uint8Array<ArrayBuffer> },
  timeoutMs: number,
): Promise<OriginResult> {
  if (!cfg.origin) return { ok: false, reason: "bad_gateway" };
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const res = await fetch(new URL(path, cfg.origin).toString(), {
      method: init.method,
      headers: init.headers,
      body: init.body && init.body.length > 0 ? init.body : undefined,
      redirect: "manual", // never follow: an origin redirect must not turn the edge into a proxy
      signal: ctl.signal,
    });
    if (res.status >= 300 && res.status < 400) return { ok: false, reason: "bad_gateway" };
    const len = Number(res.headers.get("content-length") ?? 0);
    if (len > MAX_RESPONSE_BYTES) return { ok: false, reason: "bad_gateway" };
    const body = await res.text();
    if (body.length > MAX_RESPONSE_BYTES) return { ok: false, reason: "bad_gateway" };
    return {
      ok: true,
      status: res.status,
      body,
      contentType: res.headers.get("content-type") ?? "",
      retryAfter: res.headers.get("retry-after"),
    };
  } catch (e) {
    return { ok: false, reason: ctl.signal.aborted || (e as Error)?.name === "AbortError" ? "timeout" : "network" };
  } finally {
    clearTimeout(timer);
  }
}

export const isJson = (ct: string): boolean => /^application\/(?:[\w.+-]+\+)?json\b/i.test(ct);
