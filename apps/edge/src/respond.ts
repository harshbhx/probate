import { corsHeaders } from "./cors";
import type { Config } from "./env";

const SECURITY: Record<string, string> = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
  "Cross-Origin-Resource-Policy": "cross-origin",
  "Strict-Transport-Security": "max-age=31536000",
  "Permissions-Policy": "interest-cohort=()",
};

export interface Out {
  status: number;
  body?: string | null;
  headers?: Record<string, string>;
}

/** Every response leaves through here: security headers, explicit CORS, HEAD without a body.
 *  Nothing from the origin's own headers is copied, so Set-Cookie and friends cannot leak out. */
export function finish(request: Request, cfg: Config, out: Out): Response {
  const h = corsHeaders(request, cfg.allowedOrigins);
  for (const [k, v] of Object.entries(SECURITY)) h.set(k, v);
  for (const [k, v] of Object.entries(out.headers ?? {})) h.set(k, v);
  if (out.body !== undefined && out.body !== null && !h.has("Content-Type")) {
    h.set("Content-Type", "application/json; charset=utf-8");
  }
  const body = request.method === "HEAD" ? null : (out.body ?? null);
  return new Response(body, { status: out.status, headers: h });
}

export function jsonError(
  request: Request,
  cfg: Config,
  status: number,
  error: string,
  message: string,
  extra: Record<string, string> = {},
): Response {
  return finish(request, cfg, {
    status,
    body: JSON.stringify({ error, message }),
    headers: { "Cache-Control": "no-store", ...extra },
  });
}
