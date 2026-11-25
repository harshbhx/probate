const METHODS = "GET, HEAD, POST, OPTIONS";
const ALLOW_HEADERS = "Content-Type, Accept, X-Probate-Key";
const EXPOSE = "X-Probate-Stale, X-Probate-Stale-Since, X-Edge-Cache, Retry-After, Age";

export function originAllowed(origin: string, allowed: string[]): boolean {
  for (const a of allowed) {
    if (a === origin) return true;
    const w = /^(https?:\/\/)\*\.(.+)$/.exec(a);
    if (w && origin.startsWith(w[1]!)) {
      const host = origin.slice(w[1]!.length);
      if (host.endsWith("." + w[2]!) && /^[A-Za-z0-9.-]+(:\d+)?$/.test(host)) return true;
    }
  }
  return false;
}

/** Explicit allowlist, never `*`, never credentials. */
export function corsHeaders(request: Request, allowed: string[]): Headers {
  const h = new Headers({ Vary: "Origin" });
  const origin = request.headers.get("Origin");
  if (origin && originAllowed(origin, allowed)) {
    h.set("Access-Control-Allow-Origin", origin);
    h.set("Access-Control-Expose-Headers", EXPOSE);
  }
  return h;
}

export function preflight(request: Request, allowed: string[]): Response {
  const origin = request.headers.get("Origin");
  const vary = "Origin, Access-Control-Request-Method, Access-Control-Request-Headers";
  if (!origin) return new Response(null, { status: 204, headers: { Vary: vary, Allow: METHODS } });
  if (!originAllowed(origin, allowed)) {
    return new Response(JSON.stringify({ error: "origin_not_allowed" }), {
      status: 403,
      headers: { Vary: vary, "Content-Type": "application/json; charset=utf-8" },
    });
  }
  return new Response(null, {
    status: 204,
    headers: {
      Vary: vary,
      "Access-Control-Allow-Origin": origin,
      "Access-Control-Allow-Methods": METHODS,
      "Access-Control-Allow-Headers": ALLOW_HEADERS,
      "Access-Control-Max-Age": "600",
    },
  });
}
