import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { ApiError, ProbateClient } from "../src/index.js";

type Call = { url: string; init: RequestInit };

function fake(status: number, body: unknown, calls: Call[] = []): typeof fetch {
  return (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response(typeof body === "string" ? body : JSON.stringify(body), { status });
  }) as unknown as typeof fetch;
}

describe("ProbateClient", () => {
  it("defaults to localhost:8080 and strips trailing slashes", () => {
    assert.equal(new ProbateClient().baseUrl, "http://localhost:8080");
    assert.equal(new ProbateClient({ baseUrl: "https://x.test//" }).baseUrl, "https://x.test");
  });

  it("sends X-Probate-Key only when apiKey is set", async () => {
    const calls: Call[] = [];
    await new ProbateClient({ fetch: fake(200, { ok: true }, calls) }).health();
    await new ProbateClient({ apiKey: "k", fetch: fake(200, { ok: true }, calls) }).health();
    assert.equal((calls[0]!.init.headers as Record<string, string>)["X-Probate-Key"], undefined);
    assert.equal((calls[1]!.init.headers as Record<string, string>)["X-Probate-Key"], "k");
  });

  it("POSTs the question as JSON", async () => {
    const calls: Call[] = [];
    const c = new ProbateClient({ fetch: fake(200, { answer: "a", audio_url: null, name: "n" }, calls) });
    await c.ask(4, "why?");
    assert.equal(calls[0]!.url, "http://localhost:8080/api/generations/4/ask");
    assert.equal(calls[0]!.init.method, "POST");
    assert.equal(calls[0]!.init.body, JSON.stringify({ question: "why?" }));
  });

  it("maps error bodies to ApiError (error, then detail, then statusText)", async () => {
    const e1 = await new ProbateClient({ fetch: fake(429, { error: "rate_limited" }) })
      .ask(1, "x").catch((e) => e);
    assert.ok(e1 instanceof ApiError);
    assert.equal(e1.status, 429);
    assert.equal(e1.message, "rate_limited");
    const e2 = await new ProbateClient({ fetch: fake(404, { detail: "Not in the register" }) })
      .generation(9).catch((e) => e);
    assert.equal(e2.message, "Not in the register");
    assert.equal(e2.status, 404);
    const e3 = await new ProbateClient({ fetch: fake(502, "<html>") }).summary().catch((e) => e);
    assert.equal(e3.status, 502);
  });

  it("rejects non-integer generation numbers before any request", () => {
    const c = new ProbateClient({ fetch: fake(200, {}) });
    assert.throws(() => c.generation(1.5), TypeError);
  });

  it("aborts on timeout and on a caller signal", async () => {
    // AbortSignal.timeout timers are unref'd, so hold the event loop open until abort.
    const hang = ((_u: string, init: RequestInit) =>
      new Promise((_, reject) => {
        const keep = setInterval(() => {}, 1000);
        init.signal!.addEventListener("abort", () => {
          clearInterval(keep);
          reject(init.signal!.reason);
        });
      })) as unknown as typeof fetch;
    await assert.rejects(new ProbateClient({ fetch: hang, timeout: 20 }).summary());
    const ctl = new AbortController();
    const p = new ProbateClient({ fetch: hang, timeout: 0 }).summary({ signal: ctl.signal });
    ctl.abort();
    await assert.rejects(p);
  });

  it("does not retry", async () => {
    const calls: Call[] = [];
    await new ProbateClient({ fetch: fake(500, { error: "x" }, calls) }).summary().catch(() => {});
    assert.equal(calls.length, 1);
  });

  it("events() uses ?since and de-duplicates across polls", async () => {
    const urls: string[] = [];
    const pages = [
      [{ id: 2, ts: "t", gen: 1, kind: "k", text: "b" }, { id: 1, ts: "t", gen: 1, kind: "k", text: "a" }],
      [],
      [{ id: 3, ts: "t", gen: null, kind: "k", text: "c" }],
    ];
    const f = (async (url: string) => {
      urls.push(url);
      return new Response(JSON.stringify(pages.shift() ?? []));
    }) as unknown as typeof fetch;
    const c = new ProbateClient({ fetch: f });
    const ids: number[] = [];
    for await (const ev of c.events({ intervalMs: 1 })) {
      ids.push(ev.id);
      if (ev.id === 3) break;
    }
    assert.deepEqual(ids, [1, 2, 3]);
    assert.ok(urls[0]!.endsWith("/api/events?since=0"));
    assert.ok(urls[1]!.endsWith("/api/events?since=2"));
  });
});
