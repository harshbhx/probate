import { preflight } from "./cors";
import { loadConfig, type Config, type Env } from "./env";
import { allow } from "./limiter";
import { handleRead, handleWrite } from "./proxy";
import { jsonError } from "./respond";
import { cacheKey, match } from "./routes";
import { handleStatus } from "./status";

export type { Env } from "./env";

/** Public front door for the Courthouse API. See docs/EDGE.md. */
export async function handle(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
  const cfg: Config = loadConfig(env);
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method.toUpperCase();
  const ip = request.headers.get("CF-Connecting-IP");
  const who = ip ?? "unknown";

  // Admin routes never exist at the edge, whatever the method or spelling.
  if (/^\/admin(\/|$)/i.test(path)) {
    return jsonError(request, cfg, 404, "not_found", "No such route.");
  }

  const isStatus = path === "/edge/status";
  const m = isStatus ? {} : match(method === "OPTIONS" ? "GET" : method, path);
  const known = isStatus || m.route !== undefined || m.allow !== undefined;
  if (!known) return jsonError(request, cfg, 404, "not_found", "No such route.");

  // Fail closed: without a valid fixed ORIGIN_URL nothing is proxied.
  if (!cfg.origin && !isStatus) {
    return jsonError(request, cfg, 503, "edge_misconfigured", "The edge has no valid origin configured.");
  }

  // Fail closed: edge-token mode without the secret would send visitors' requests to the origin
  // as anonymous (and the origin would then count them all as one address).
  if (cfg.edgeTokenRequired && !cfg.edgeToken && !isStatus) {
    console.error(JSON.stringify({ evt: "edge_misconfigured", reason: "EDGE_TOKEN_MODE=required but the EDGE_TOKEN secret is not set" }));
    return jsonError(request, cfg, 503, "edge_misconfigured", "The edge is missing its origin credentials.");
  }

  if (method === "OPTIONS") return preflight(request, cfg.allowedOrigins);

  if (isStatus) {
    if (method !== "GET" && method !== "HEAD") {
      return jsonError(request, cfg, 405, "method_not_allowed", "Use GET.", { Allow: "GET, HEAD, OPTIONS" });
    }
    if (!(await allow(env, "read_ip", who))) return tooMany(request, cfg, "ip");
    return handleStatus(request, env, cfg);
  }

  if (!m.route) {
    const allowed = [...(m.allow ?? []), "OPTIONS"].join(", ");
    return jsonError(request, cfg, 405, "method_not_allowed", "That method is not allowed here.", { Allow: allowed });
  }
  if (method !== "GET" && method !== "HEAD" && method !== "POST") {
    return jsonError(request, cfg, 405, "method_not_allowed", "That method is not allowed here.");
  }

  const route = m.route;
  if (route.kind === "write" || route.kind === "judge-read") {
    // Per-IP first, then global: a single noisy visitor cannot burn the global budget.
    if (!(await allow(env, "write_ip", who))) return tooMany(request, cfg, "ip");
    if (route.kind === "write" && !(await allow(env, "write_global", "all"))) return tooMany(request, cfg, "global");
    return handleWrite(request, env, ctx, cfg, route, ip);
  }

  if (!(await allow(env, "read_ip", who))) return tooMany(request, cfg, "ip");
  const key = cacheKey(route, path, url.searchParams);
  if (key === null) return jsonError(request, cfg, 400, "bad_query", "Unsupported query string.");
  return handleRead(request, env, ctx, cfg, route, key, ip);
}

function tooMany(request: Request, cfg: Config, scope: "ip" | "global"): Response {
  return jsonError(request, cfg, 429, "rate_limited", "Too many requests. Please slow down.", {
    "Retry-After": "30",
    "X-Edge-Limit-Scope": scope,
  });
}

export default {
  fetch: handle,
} satisfies ExportedHandler<Env>;
