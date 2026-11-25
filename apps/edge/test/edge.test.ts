import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { allow } from "../src/limiter";
import { hang, json, setup } from "./helpers";

const SUMMARY = { living: { gen: 3, name: "Cora" }, latest_trial: 2 };
const post = (body: unknown, extra: Record<string, string> = {}) => ({
  method: "POST",
  headers: { "content-type": "application/json", ...extra },
  body: typeof body === "string" ? body : JSON.stringify(body),
});

let now = 1_700_000_000_000;
beforeEach(() => {
  now = 1_700_000_000_000;
  vi.spyOn(Date, "now").mockImplementation(() => now);
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("routing allowlist", () => {
  it("proxies the public read routes and nothing else", async () => {
    const t = setup();
    t.origin.fn = () => json({ ok: true });
    for (const p of ["/healthz", "/api/summary", "/api/genome", "/api/evidence", "/api/events", "/api/trials/latest", "/api/trials/4", "/api/generations/4", "/api/live"]) {
      const r = await t.call(p);
      expect(r.status, p).toBe(200);
    }
    for (const p of ["/", "/audio/x.mp3", "/api", "/api/", "/api/summary/", "/api/unknown", "/API/summary", "/api/generations/abc", "/api/generations/1/ask/x", "/api/%73ummary", "/api/generations/1%2f..", "/api//summary", "/api/../admin/pause", "/edge/other", "/index.html"]) {
      const r = await t.call(p);
      expect(r.status, p).toBe(404);
    }
    expect(t.origin.calls.every((c) => new URL(c.url).host === "courthouse.example.test")).toBe(true);
  });

  it("rejects methods that are not allowed on a known path", async () => {
    const t = setup();
    expect((await t.call("/api/summary", { method: "POST" })).status).toBe(405);
    expect((await t.call("/api/lives", { method: "GET" })).status).toBe(405);
    expect((await t.call("/api/summary", { method: "DELETE" })).status).toBe(405);
    expect((await t.call("/api/summary", { method: "PUT", body: "{}" })).status).toBe(405);
    expect(t.origin.calls).toHaveLength(0);
  });

  it("rejects an unexpected query string on events and ignores others", async () => {
    const t = setup();
    expect((await t.call("/api/events?since=abc")).status).toBe(400);
    await t.call("/api/summary?x=1&token=secret");
    expect(t.origin.calls[0]!.url).toBe("https://courthouse.example.test/api/summary");
  });

  it("is not an open proxy: the host is fixed", async () => {
    const t = setup();
    await t.call("/api/summary", { headers: { Host: "evil.example", "X-Forwarded-Host": "evil.example" } });
    expect(new URL(t.origin.calls[0]!.url).host).toBe("courthouse.example.test");
    expect((await t.call("/https://evil.example/")).status).toBe(404);
  });

  it("does not follow origin redirects", async () => {
    const t = setup();
    t.origin.fn = () => new Response(null, { status: 302, headers: { location: "https://evil.example/" } });
    const r = await t.call("/api/summary");
    expect(r.status).toBe(502);
    expect(r.headers.get("location")).toBeNull();
  });

  it("fails closed when ORIGIN_URL is unset or unsafe", async () => {
    for (const bad of [undefined, "", "not a url", "http://courthouse.example.test", "https://user:pw@x.test", "https://x.test/base?x=1"]) {
      const t = setup({ ORIGIN_URL: bad });
      expect((await t.call("/api/summary")).status, String(bad)).toBe(503);
      expect((await t.call("/api/lives", post({}))).status).toBe(503);
      expect((await t.call("/edge/status")).status).toBe(503);
      expect(t.origin.calls).toHaveLength(0);
    }
    const ok = setup({ ORIGIN_URL: "http://127.0.0.1:8080" });
    expect((await ok.call("/api/summary")).status).toBe(200);
  });
});

describe("admin and header hygiene", () => {
  it("blocks /admin/* at the edge with 404, any method", async () => {
    const t = setup();
    for (const [m, p] of [["POST", "/admin/pause"], ["POST", "/admin/force-death"], ["GET", "/admin/tick"], ["POST", "/ADMIN/pause"], ["GET", "/admin"], ["POST", "/admin/judge/disable"], ["OPTIONS", "/admin/pause"]] as const) {
      const r = await t.call(p, { method: m, headers: { "X-Probate-Admin": "hunter2" } });
      expect(r.status, `${m} ${p}`).toBe(404);
    }
    expect(t.origin.calls).toHaveLength(0);
  });

  it("never forwards cookies, admin or internal headers; forwards the key on judge routes only", async () => {
    const t = setup();
    t.origin.fn = () => json({ ok: true, accepted: true });
    const evil = { Cookie: "session=abc", Authorization: "Bearer visitor", "X-Probate-Admin": "tok", "X-Forwarded-For": "1.2.3.4, 5.6.7.8", Connection: "keep-alive, x-foo", "X-Foo": "bar", "Proxy-Authorization": "x", "CF-Access-Jwt-Assertion": "j", "X-Probate-Key": "judge-key-123456789012345" };

    await t.call("/api/genome", { headers: evil });
    const read = t.origin.at("/api/genome")[0]!;
    for (const h of ["cookie", "authorization", "x-probate-admin", "connection", "x-foo", "proxy-authorization", "cf-access-jwt-assertion", "x-probate-key"]) {
      expect(read.headers.has(h), h).toBe(false);
    }
    expect(read.headers.get("x-forwarded-for")).toBe("203.0.113.7");

    await t.call("/api/attacks", { ...post({ text: "hi" }), headers: { ...evil, "content-type": "application/json" } });
    const atk = t.origin.at("/api/attacks")[0]!;
    expect(atk.headers.get("x-probate-key")).toBe("judge-key-123456789012345");
    expect(atk.headers.has("cookie")).toBe(false);
    expect(atk.headers.has("x-probate-admin")).toBe(false);
    expect(atk.headers.get("x-forwarded-for")).toBe("203.0.113.7");

    await t.call("/api/generations/1/ask", { ...post({ question: "why?" }), headers: { ...evil, "content-type": "application/json" } });
    expect(t.origin.at("/api/generations/1/ask")[0]!.headers.has("x-probate-key")).toBe(false);
  });

  it("adds the origin bearer token when configured, and never sends the visitor's Authorization", async () => {
    const t = setup({ ORIGIN_AUTH_TOKEN: "sprite-token" });
    await t.call("/api/genome", { headers: { Authorization: "Bearer visitor" } });
    expect(t.origin.calls[0]!.headers.get("authorization")).toBe("Bearer sprite-token");
  });

  it("sends the edge token and the real client IP, and never what the visitor sent in those headers", async () => {
    const t = setup({ EDGE_TOKEN: "edge-secret-0123456789", EDGE_TOKEN_MODE: "required" });
    t.origin.fn = () => json({ ok: true, accepted: true });
    const spoof = { "X-Probate-Edge": "guess", "X-Probate-Client-IP": "6.6.6.6", "x-probate-edge": "guess2", "X-Forwarded-For": "6.6.6.6" };
    await t.call("/api/genome", { headers: spoof, ip: "198.51.100.4" });
    await t.call("/api/attacks", { ...post({ text: "hi" }), headers: { ...spoof, "content-type": "application/json", "X-Probate-Key": "judge-key-123456789012345" }, ip: "198.51.100.5" });
    await t.call("/api/generations/1/ask", { ...post({ question: "why?" }), headers: { ...spoof, "content-type": "application/json" }, ip: "198.51.100.6" });
    for (const [path, ip] of [["/api/genome", "198.51.100.4"], ["/api/attacks", "198.51.100.5"], ["/api/generations/1/ask", "198.51.100.6"]] as const) {
      const c = t.origin.at(path)[0]!;
      expect(c.headers.get("x-probate-edge"), path).toBe("edge-secret-0123456789");
      expect(c.headers.get("x-probate-client-ip"), path).toBe(ip);
      expect(c.headers.get("x-forwarded-for"), path).toBe(ip);
    }
  });

  it("sends no edge headers when no token is configured, and drops spoofed ones", async () => {
    const t = setup();
    await t.call("/api/genome", { headers: { "X-Probate-Edge": "guess", "X-Probate-Client-IP": "6.6.6.6" } });
    const c = t.origin.calls[0]!;
    expect(c.headers.has("x-probate-edge")).toBe(false);
    expect(c.headers.has("x-probate-client-ip")).toBe(false);
  });

  it("fails closed in edge-token mode without the secret: 503, nothing reaches the origin", async () => {
    for (const secret of [undefined, "", "   "]) {
      const t = setup({ EDGE_TOKEN_MODE: "required", EDGE_TOKEN: secret });
      for (const [p, init] of [["/api/summary", {}], ["/api/lives", post({})], ["/api/attacks", post({ text: "x" }, { "X-Probate-Key": "judge-key-123456789012345" })]] as const) {
        const r = await t.call(p, init);
        expect(r.status, p).toBe(503);
        expect(((await r.json()) as any).error).toBe("edge_misconfigured");
      }
      expect(t.origin.calls).toHaveLength(0);
      const st = await t.call("/edge/status");
      expect(st.status).toBe(503);
      expect(((await st.json()) as any).edge_token).toBe("missing");
    }
  });

  it("never logs or returns the edge token", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    const t = setup({ EDGE_TOKEN: "edge-secret-0123456789", EDGE_TOKEN_MODE: "required", WRITE_RETRIES: "0" });
    t.origin.fn = () => {
      throw new TypeError("fetch failed");
    };
    const seen: string[] = [];
    for (const [p, init] of [["/api/summary", {}], ["/api/lives", post({})], ["/edge/status", {}]] as const) {
      const r = await t.call(p, init);
      seen.push(await r.text(), JSON.stringify([...r.headers]));
    }
    const missing = setup({ EDGE_TOKEN_MODE: "required" });
    seen.push(await (await missing.call("/api/summary")).text());
    expect(seen.join("") + JSON.stringify([...warn.mock.calls, ...err.mock.calls])).not.toContain("edge-secret");
    expect(JSON.stringify(seen)).toContain("sent");
  });

  it("drops Set-Cookie and server headers from the origin response and adds security headers", async () => {
    const t = setup();
    t.origin.fn = () => json({ a: 1 }, 200, { "set-cookie": "sid=1", server: "uvicorn", "access-control-allow-origin": "*", "x-admin": "1" });
    const r = await t.call("/api/summary");
    expect(r.headers.get("set-cookie")).toBeNull();
    expect(r.headers.get("server")).toBeNull();
    expect(r.headers.get("x-admin")).toBeNull();
    expect(r.headers.get("access-control-allow-origin")).toBeNull();
    expect(r.headers.get("x-content-type-options")).toBe("nosniff");
    expect(r.headers.get("content-security-policy")).toContain("default-src 'none'");
    expect(r.headers.get("referrer-policy")).toBe("no-referrer");
  });

  it("rejects a malformed key header and answers keyless judge-status at the edge", async () => {
    const t = setup();
    expect((await t.call("/api/attacks", post({ a: 1 }, { "X-Probate-Key": "bad key with spaces" }))).status).toBe(400);
    const r = await t.call("/api/judge/status");
    expect(r.status).toBe(401);
    expect(t.origin.calls).toHaveLength(0);
  });
});

describe("cache: hit, miss, ttl, immutability", () => {
  it("misses once, then hits; the Courthouse is called once", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = () => json(SUMMARY);
    const a = await t.call("/api/summary");
    expect(a.headers.get("x-edge-cache")).toBe("MISS");
    expect(await a.json()).toEqual(SUMMARY);
    const b = await t.call("/api/summary");
    expect(b.headers.get("x-edge-cache")).toBe("HIT");
    expect(await b.json()).toEqual(SUMMARY);
    expect(t.origin.calls).toHaveLength(1);
    expect(b.headers.get("x-probate-stale")).toBeNull();
  });

  it("expires after the TTL while awake (summary 15 s) and serves SWR inside the window", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    let n = 0;
    t.origin.fn = () => json({ n: ++n });
    await t.call("/api/summary");
    now += 14_000;
    expect((await t.call("/api/summary")).headers.get("x-edge-cache")).toBe("HIT");
    now += 2_000; // 16 s: past ttl, inside swr
    const swr = await t.call("/api/summary");
    expect(swr.headers.get("x-edge-cache")).toBe("SWR");
    expect(await swr.json()).toEqual({ n: 1 }); // old body now, refresh in background
    expect(t.origin.calls).toHaveLength(2);
    expect(await (await t.call("/api/summary")).json()).toEqual({ n: 2 });
    now += 60_000; // far past ttl + swr: foreground refresh
    const miss = await t.call("/api/summary");
    expect(miss.headers.get("x-edge-cache")).toBe("MISS");
    expect(await miss.json()).toEqual({ n: 3 });
  });

  it("uses the documented TTLs: genome and evidence 60 s", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    await t.call("/api/genome");
    await t.call("/api/evidence");
    now += 59_000;
    expect((await t.call("/api/genome")).headers.get("x-edge-cache")).toBe("HIT");
    expect((await t.call("/api/evidence")).headers.get("x-edge-cache")).toBe("HIT");
    expect(t.origin.calls).toHaveLength(2);
  });

  it("keeps a finished generation for a day, a living one for 15 s", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = (c) => json({ state: c.url.endsWith("/3") ? "tried" : "living" });
    await t.call("/api/generations/3");
    await t.call("/api/generations/4");
    now += 3_600_000;
    expect((await t.call("/api/generations/3")).headers.get("x-edge-cache")).toBe("HIT");
    expect((await t.call("/api/generations/4")).headers.get("x-edge-cache")).toBe("MISS");
    now += 86_400_000 + 1;
    expect((await t.call("/api/generations/3")).headers.get("x-edge-cache")).toBe("MISS");
  });

  it("does not store or serve non-JSON 200s (the origin's SPA catch-all)", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = () => new Response("<html></html>", { status: 200, headers: { "content-type": "text/html" } });
    const r = await t.call("/api/summary");
    expect(r.status).toBe(502);
    expect(t.kv.data.has("snap:/api/summary")).toBe(false);
  });

  it("passes 404s through, remembers them for 10 s, and never snapshots them", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = () => json({ detail: "Not in the register" }, 404);
    expect((await t.call("/api/generations/99")).status).toBe(404);
    expect((await t.call("/api/generations/99")).status).toBe(404);
    expect(t.origin.calls).toHaveLength(1);
    now += 11_000;
    await t.call("/api/generations/99");
    expect(t.origin.calls).toHaveLength(2);
    expect([...t.kv.data.keys()].some((k) => k.startsWith("snap:"))).toBe(false);
  });

  it("coalesces concurrent misses into one origin call", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = async () => {
      await new Promise((r) => setTimeout(r, 30));
      return json(SUMMARY);
    };
    const rs = await Promise.all(Array.from({ length: 8 }, () => t.call("/api/summary")));
    expect(rs.every((r) => r.status === 200)).toBe(true);
    expect(t.origin.calls).toHaveLength(1);
  });

  it("writes snapshots to KV and throttles repeat writes", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    await t.call("/api/summary");
    const first = t.kv.puts;
    expect(t.kv.data.has("snap:/api/summary")).toBe(true);
    now += 16_000 * 1; // refresh with an identical body: no new KV write inside 10 minutes
    await t.call("/api/summary");
    await t.call("/api/summary");
    expect(t.kv.puts).toBe(first);
  });
});

describe("sleep-friendliness (on_demand mode)", () => {
  it("serves reads from the snapshot while the Sprite is idle, far beyond the base TTL", async () => {
    const t = setup(); // on_demand by default
    t.origin.fn = () => json(SUMMARY);
    await t.call("/api/summary"); // cold read: the only unavoidable wake
    now += 14 * 60_000;
    const r = await t.call("/api/summary");
    expect(r.headers.get("x-edge-cache")).toBe("HIT");
    expect(t.origin.calls).toHaveLength(1);
  });

  it("a write marks the origin awake, so reads use the short TTLs again", async () => {
    const t = setup();
    t.origin.fn = (c) => (c.method === "POST" ? json({ state: "waking" }, 202) : json(SUMMARY));
    await t.call("/api/summary");
    await t.call("/api/lives", { method: "POST" });
    now += 50_000; // past the 15 s TTL plus the 30 s SWR window; idle mode would still say HIT
    expect((await t.call("/api/summary")).headers.get("x-edge-cache")).toBe("MISS");
  });

  it("a non-idle /api/live keeps the origin marked awake; idle does not", async () => {
    const t = setup();
    t.origin.fn = () => json({ state: "living" });
    await t.call("/api/live");
    now += 20_000;
    expect((await t.call("/api/live")).headers.get("x-edge-cache")).toBe("MISS");
    const idle = setup();
    idle.origin.fn = () => json({ state: "idle" });
    await idle.call("/api/live");
    now += 20_000;
    expect((await idle.call("/api/live")).headers.get("x-edge-cache")).toBe("HIT");
  });

  it("a keyed /api/live bypasses the cache only when awake, never when idle", async () => {
    const t = setup();
    t.origin.fn = () => json({ state: "idle", judge: false });
    await t.call("/api/live"); // idle
    const k = "judge-key-123456789012345";
    const r = await t.call("/api/live", { headers: { "X-Probate-Key": k } });
    expect(r.headers.get("x-edge-cache")).toBe("HIT");
    expect(t.origin.calls).toHaveLength(1);
    await t.call("/api/lives", { method: "POST" }); // wakes
    const r2 = await t.call("/api/live", { headers: { "X-Probate-Key": k } });
    expect(r2.headers.get("x-edge-cache")).toBe("BYPASS");
    expect(r2.headers.get("cache-control")).toBe("no-store");
    expect(t.origin.at("/api/live").at(-1)!.headers.get("x-probate-key")).toBe(k);
  });
});

describe("stale fallback", () => {
  it("serves the last known good body with X-Probate-Stale when the origin errors", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = () => json(SUMMARY);
    await t.call("/api/summary");
    now += 120_000;
    t.origin.fn = () => json({ detail: "boom" }, 500);
    const r = await t.call("/api/summary");
    expect(r.status).toBe(200);
    expect(r.headers.get("x-probate-stale")).toBe("1");
    expect(r.headers.get("x-probate-stale-since")).toBe(new Date(1_700_000_000_000).toISOString());
    expect(r.headers.get("x-probate-stale-reason")).toBe("error");
    expect(await r.json()).toEqual(SUMMARY); // body untouched
  });

  it("serves stale on a network error", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    await t.call("/api/genome");
    now += 300_000;
    t.origin.fn = () => {
      throw new TypeError("fetch failed");
    };
    const r = await t.call("/api/genome");
    expect(r.headers.get("x-probate-stale")).toBe("1");
  });

  it("answers stale after SLOW_MS when the origin is waking, then refreshes in the background", async () => {
    const t = setup({ ORIGIN_MODE: "always_on", SLOW_MS: "50", READ_TIMEOUT_MS: "400" });
    await t.call("/api/summary");
    now += 120_000;
    t.origin.fn = async () => {
      await new Promise((r) => setTimeout(r, 150));
      return json({ fresh: true });
    };
    const t0 = performance.now();
    const pending: Promise<unknown>[] = [];
    t.ctx.waitUntil = (p: Promise<unknown>) => void pending.push(p);
    const r = await (await import("../src/index")).handle(new Request("https://edge.example.test/api/summary", { headers: { "CF-Connecting-IP": "9.9.9.9" } }), t.env, t.ctx);
    expect(performance.now() - t0).toBeLessThan(140);
    expect(r.headers.get("x-probate-stale")).toBe("1");
    expect(r.headers.get("x-probate-stale-reason")).toBe("slow");
    await Promise.allSettled(pending);
    const next = await t.call("/api/summary");
    expect(next.headers.get("x-edge-cache")).toBe("HIT");
    expect(await next.json()).toEqual({ fresh: true });
    expect(next.headers.get("x-probate-stale")).toBeNull();
  });

  it("serves stale on timeout", async () => {
    const t = setup({ ORIGIN_MODE: "always_on", SLOW_MS: "10000", READ_TIMEOUT_MS: "60" });
    await t.call("/api/summary");
    now += 120_000;
    t.origin.fn = () => hang();
    const r = await t.call("/api/summary");
    expect(r.headers.get("x-probate-stale")).toBe("1");
    expect(r.headers.get("x-probate-stale-reason")).toBe("timeout");
  });

  it("returns a clean 504 JSON error on timeout with nothing to show, 502 on a network error", async () => {
    const t = setup({ READ_TIMEOUT_MS: "50" });
    t.origin.fn = () => hang();
    const r = await t.call("/api/genome");
    expect(r.status).toBe(504);
    expect(r.headers.get("content-type")).toContain("application/json");
    expect(await r.json()).toMatchObject({ error: "origin_timeout" });
    t.origin.fn = () => {
      throw new TypeError("fetch failed");
    };
    expect((await t.call("/api/evidence")).status).toBe(502);
  });

  it("recovers from KV after a cold isolate", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    await t.call("/api/summary");
    const { resetStore } = await import("../src/store");
    resetStore(); // new isolate: memory gone, KV remains
    t.origin.fn = () => json({ x: 1 }, 503);
    now += 120_000;
    const r = await t.call("/api/summary");
    expect(r.headers.get("x-probate-stale")).toBe("1");
  });
});

describe("writes", () => {
  it("pass through uncached and with no-store", async () => {
    const t = setup();
    t.origin.fn = (c) => (c.method === "POST" ? json({ state: "waking" }, 202, { "retry-after": "7" }) : json({}));
    const r = await t.call("/api/lives", { method: "POST" });
    expect(r.status).toBe(202);
    expect(r.headers.get("cache-control")).toBe("no-store");
    expect(r.headers.get("retry-after")).toBe("7");
    await t.call("/api/lives", { method: "POST" });
    expect(t.origin.at("/api/lives")).toHaveLength(2);
    expect([...t.kv.data.keys()].some((k) => k.startsWith("snap:/api/lives"))).toBe(false);
  });

  it("an ask drops the cached generation so the new answer shows", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    t.origin.fn = (c) => (c.method === "POST" ? json({ answer: "x" }) : json({ state: "tried", n: now }));
    await t.call("/api/generations/2");
    expect((await t.call("/api/generations/2")).headers.get("x-edge-cache")).toBe("HIT");
    await t.call("/api/generations/2/ask", post({ question: "why?" }));
    expect((await t.call("/api/generations/2")).headers.get("x-edge-cache")).toBe("MISS");
  });

  it("retries a cold-start 502 page and connection errors, but not a timeout", async () => {
    const t = setup({ WRITE_RETRIES: "2", WRITE_TIMEOUT_MS: "3000" });
    let n = 0;
    t.origin.fn = () => (++n < 3 ? new Response("bad gateway", { status: 502, headers: { "content-type": "text/html" } }) : json({ ok: true }, 202));
    const r = await t.call("/api/lives", { method: "POST" });
    expect(r.status).toBe(202);
    expect(t.origin.at("/api/lives")).toHaveLength(3);

    const u = setup({ WRITE_TIMEOUT_MS: "80" });
    u.origin.fn = () => hang();
    const r2 = await u.call("/api/lives", { method: "POST" });
    expect(r2.status).toBe(504);
    expect(u.origin.at("/api/lives")).toHaveLength(1);
  });

  it("does not retry an application-level 503 JSON answer", async () => {
    const t = setup();
    t.origin.fn = () => json({ error: "unavailable" }, 503);
    const r = await t.call("/api/lives", { method: "POST" });
    expect(r.status).toBe(503);
    expect(t.origin.at("/api/lives")).toHaveLength(1);
  });

  it("gives a 502 JSON error when the origin is down", async () => {
    const t = setup({ WRITE_RETRIES: "1" });
    t.origin.fn = () => {
      throw new TypeError("fetch failed");
    };
    const r = await t.call("/api/attacks", post({ text: "x" }, { "X-Probate-Key": "judge-key-123456789012345" }));
    expect(r.status).toBe(502);
    expect(await r.json()).toMatchObject({ error: "origin_unavailable" });
  });
});

describe("validation and body caps", () => {
  it("caps the body by Content-Length and by actual bytes", async () => {
    const t = setup();
    const big = JSON.stringify({ question: "x".repeat(5_000) });
    expect((await t.call("/api/generations/1/ask", post(big))).status).toBe(413);
    expect((await t.call("/api/attacks", post({ text: "y".repeat(9_000) }))).status).toBe(413);
    const lie = await t.call("/api/lives", { method: "POST", headers: { "content-type": "application/json", "content-length": "99999" }, body: "{}" });
    expect(lie.status).toBe(413);
    expect(t.origin.calls).toHaveLength(0);
  });

  it("validates content type and JSON", async () => {
    const open = { limit: async () => ({ success: true }) } as unknown as RateLimit;
    const t = setup({ RL_WRITE_IP: open, RL_WRITE_GLOBAL: open });
    expect((await t.call("/api/generations/1/ask", { method: "POST", headers: { "content-type": "text/plain" }, body: "hi" })).status).toBe(415);
    expect((await t.call("/api/generations/1/ask", post("{not json"))).status).toBe(400);
    expect((await t.call("/api/generations/1/ask", post([1, 2]))).status).toBe(400);
    expect((await t.call("/api/generations/1/ask", post({ question: 5 }))).status).toBe(400);
    expect((await t.call("/api/generations/1/ask", post({ question: "  " }))).status).toBe(400);
    expect((await t.call("/api/attacks", post("null"))).status).toBe(400);
    expect((await t.call("/api/attacks", { method: "POST" })).status).toBe(415);
    expect((await t.call("/api/lives", post("{oops"))).status).toBe(400);
    expect(t.origin.calls).toHaveLength(0);
    expect((await t.call("/api/lives", { method: "POST" })).status).toBe(200); // empty body is fine
    expect((await t.call("/api/generations/1/ask", post({ question: "ok" }))).status).toBe(200);
  });
});

describe("rate limiting in front of the origin", () => {
  it("limits writes per IP with a 429 that never reaches the origin", async () => {
    const t = setup();
    const codes: number[] = [];
    for (let i = 0; i < 9; i++) codes.push((await t.call("/api/lives", { method: "POST", ip: "198.51.100.1" })).status);
    expect(codes.slice(0, 6)).toEqual(Array(6).fill(200));
    expect(codes.slice(6)).toEqual([429, 429, 429]);
    expect(t.origin.at("/api/lives")).toHaveLength(6);
    const other = await t.call("/api/lives", { method: "POST", ip: "198.51.100.2" });
    expect(other.status).toBe(200);
    const limited = await t.call("/api/lives", { method: "POST", ip: "198.51.100.1" });
    expect(limited.headers.get("retry-after")).toBe("30");
  });

  it("limits writes globally across IPs", async () => {
    const t = setup();
    let ok = 0;
    let blocked = 0;
    for (let i = 0; i < 40; i++) {
      const r = await t.call("/api/lives", { method: "POST", ip: `192.0.2.${i + 1}` });
      if (r.status === 200) ok++;
      else if (r.status === 429) blocked++;
    }
    expect(ok).toBe(30);
    expect(blocked).toBe(10);
    expect(t.origin.at("/api/lives")).toHaveLength(30);
  });

  it("uses the Workers rate limiting binding when bound", async () => {
    const seen: string[] = [];
    const t = setup({ RL_WRITE_IP: { limit: async ({ key }: { key: string }) => (seen.push(key), { success: false }) } as unknown as RateLimit });
    const r = await t.call("/api/lives", { method: "POST", ip: "203.0.113.50" });
    expect(r.status).toBe(429);
    expect(seen).toEqual(["203.0.113.50"]);
    expect(t.origin.calls).toHaveLength(0);
  });

  it("a flood of distinct cache-missing reads cannot wake the origin more than the global budget; stale is served", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    await t.call("/api/summary"); // snapshot
    now += 120_000;
    const before = t.origin.calls.length;
    const statuses: number[] = [];
    for (let i = 0; i < 80; i++) statuses.push((await t.call(`/api/generations/${i + 1}`, { ip: `10.0.${Math.floor(i / 250)}.${i % 250}` })).status);
    expect(t.origin.calls.length - before).toBeLessThanOrEqual(60);
    expect(statuses.filter((s) => s === 429).length).toBeGreaterThan(0);
  });

  it("limits reads per IP", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    let blocked = 0;
    for (let i = 0; i < 130; i++) if ((await t.call("/api/summary", { ip: "198.51.100.9" })).status === 429) blocked++;
    expect(blocked).toBe(10);
  });

  it("fallback window resets", async () => {
    const t = setup();
    for (let i = 0; i < 6; i++) expect(await allow(t.env, "write_ip", "k", 1000)).toBe(true);
    expect(await allow(t.env, "write_ip", "k", 1500)).toBe(false);
    expect(await allow(t.env, "write_ip", "k", 61_500)).toBe(true);
  });
});

describe("CORS", () => {
  it("answers preflight at the edge for allowed origins, including X-Probate-Key", async () => {
    const t = setup();
    const r = await t.call("/api/attacks", { method: "OPTIONS", headers: { Origin: "https://site.example.test", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type,x-probate-key" } });
    expect(r.status).toBe(204);
    expect(r.headers.get("access-control-allow-origin")).toBe("https://site.example.test");
    expect(r.headers.get("access-control-allow-headers")!.toLowerCase()).toContain("x-probate-key");
    expect(r.headers.get("access-control-allow-methods")).toContain("POST");
    expect(r.headers.get("access-control-allow-credentials")).toBeNull();
    expect(r.headers.get("vary")).toContain("Origin");
    expect(t.origin.calls).toHaveLength(0);
  });

  it("supports wildcard subdomains but refuses look-alikes and other origins", async () => {
    const t = setup();
    const ask = (o: string) => t.call("/api/summary", { method: "OPTIONS", headers: { Origin: o, "Access-Control-Request-Method": "GET" } });
    expect((await ask("https://abc.pages.example.test")).headers.get("access-control-allow-origin")).toBe("https://abc.pages.example.test");
    for (const bad of ["https://evil.example", "https://pages.example.test", "https://x.pages.example.test.evil.example", "http://site.example.test", "null"]) {
      const r = await ask(bad);
      expect(r.status, bad).toBe(403);
      expect(r.headers.get("access-control-allow-origin")).toBeNull();
    }
    expect((await t.call("/api/summary", { method: "OPTIONS" })).status).toBe(204);
    expect((await t.call("/admin/pause", { method: "OPTIONS", headers: { Origin: "https://site.example.test" } })).status).toBe(404);
  });

  it("adds explicit CORS headers to real responses, never *", async () => {
    const t = setup();
    const ok = await t.call("/api/summary", { headers: { Origin: "https://site.example.test" } });
    expect(ok.headers.get("access-control-allow-origin")).toBe("https://site.example.test");
    expect(ok.headers.get("access-control-expose-headers")).toContain("X-Probate-Stale");
    const no = await t.call("/api/summary", { headers: { Origin: "https://evil.example" } });
    expect(no.headers.get("access-control-allow-origin")).toBeNull();
    expect(no.headers.get("vary")).toContain("Origin");
    const err = await t.call("/api/nope", { headers: { Origin: "https://site.example.test" } });
    expect(err.headers.get("access-control-allow-origin")).toBe("https://site.example.test");
  });
});

describe("/edge/status", () => {
  it("never calls the origin and reports snapshot age and last-seen reachability", async () => {
    const t = setup({ ORIGIN_MODE: "always_on" });
    const empty = await t.call("/edge/status");
    expect(t.origin.calls).toHaveLength(0);
    const e = (await empty.json()) as any;
    expect(e.origin.configured).toBe(true);
    expect(e.origin.last_seen_reachable).toBe("unknown");
    expect(e.snapshots.summary.present).toBe(false);

    await t.call("/api/summary");
    now += 7_000;
    const calls = t.origin.calls.length;
    const s = (await (await t.call("/edge/status")).json()) as any;
    expect(t.origin.calls).toHaveLength(calls);
    expect(s.snapshots.summary).toMatchObject({ present: true, age_s: 7, fresh_while_awake: true });
    expect(s.origin.last_seen_reachable).toBe("yes");
    expect(JSON.stringify(s)).not.toContain("courthouse.example.test"); // origin URL is not disclosed

    t.origin.fn = () => json({}, 500);
    now += 100_000;
    await t.call("/api/summary");
    const down = (await (await t.call("/edge/status")).json()) as any;
    expect(down.origin.last_seen_reachable).toBe("no");
    expect(down.origin.last_error_kind).toBe("http_500");
  });

  it("is no-store, rate limited and read-only", async () => {
    const t = setup();
    const r = await t.call("/edge/status");
    expect(r.headers.get("cache-control")).toBe("no-store");
    expect((await t.call("/edge/status", { method: "POST" })).status).toBe(405);
    expect((await t.call("/edge/status", { method: "OPTIONS", headers: { Origin: "https://site.example.test" } })).status).toBe(204);
  });
});

describe("hygiene", () => {
  it("never logs request bodies or keys", async () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const log = vi.spyOn(console, "log").mockImplementation(() => {});
    const t = setup({ WRITE_RETRIES: "0" });
    t.origin.fn = () => {
      throw new TypeError("fetch failed");
    };
    await t.call("/api/attacks", post({ text: "SECRET-BODY" }, { "X-Probate-Key": "judge-key-SECRET-123456" }));
    const logged = JSON.stringify([...warn.mock.calls, ...log.mock.calls]);
    expect(logged).not.toContain("SECRET");
  });

  it("HEAD returns headers without a body", async () => {
    const t = setup();
    const r = await t.call("/api/summary", { method: "HEAD" });
    expect(r.status).toBe(200);
    expect(await r.text()).toBe("");
  });
});
