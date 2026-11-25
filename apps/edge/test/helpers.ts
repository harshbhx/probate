import { vi } from "vitest";
import { handle } from "../src/index";
import type { Env } from "../src/env";
import { resetFallbackLimiter } from "../src/limiter";
import { resetInflight } from "../src/proxy";
import { resetStore } from "../src/store";

export class FakeKV {
  data = new Map<string, string>();
  puts = 0;
  async get(key: string, type?: unknown): Promise<unknown> {
    const v = this.data.get(key);
    if (v === undefined) return null;
    return type === "json" || (type as { type?: string })?.type === "json" ? JSON.parse(v) : v;
  }
  async put(key: string, value: string): Promise<void> {
    this.puts++;
    this.data.set(key, value);
  }
  async delete(key: string): Promise<void> {
    this.data.delete(key);
  }
}

export interface Call {
  url: string;
  method: string;
  headers: Headers;
  body: string;
}

export type OriginFn = (c: Call, signal: AbortSignal | null) => Response | Promise<Response>;

export class Origin {
  calls: Call[] = [];
  fn: OriginFn = () => json({ ok: true });
  constructor() {
    vi.stubGlobal("fetch", async (input: string, init: RequestInit = {}) => {
      const call: Call = {
        url: String(input),
        method: init.method ?? "GET",
        headers: new Headers(init.headers),
        body: init.body ? new TextDecoder().decode(init.body as Uint8Array) : "",
      };
      this.calls.push(call);
      const signal = init.signal ?? null;
      const res = this.fn(call, signal);
      return await Promise.race([
        Promise.resolve(res),
        new Promise<never>((_, rej) => signal?.addEventListener("abort", () => rej(Object.assign(new Error("aborted"), { name: "AbortError" })))),
      ]);
    });
  }
  /** Calls whose path matches. */
  at(path: string): Call[] {
    return this.calls.filter((c) => new URL(c.url).pathname === path);
  }
}

export const json = (o: unknown, status = 200, headers: Record<string, string> = {}): Response =>
  new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", ...headers } });

export const hang = (): Promise<Response> => new Promise(() => {});

export function setup(over: Partial<Env> = {}) {
  resetStore();
  resetFallbackLimiter();
  resetInflight();
  const kv = new FakeKV();
  const origin = new Origin();
  const env: Env = {
    ORIGIN_URL: "https://courthouse.example.test",
    ALLOWED_ORIGINS: "https://site.example.test,https://*.pages.example.test",
    SNAPSHOTS: kv as unknown as KVNamespace,
    READ_TIMEOUT_MS: "300",
    SLOW_MS: "100",
    WRITE_TIMEOUT_MS: "600",
    ...over,
  };
  const pending: Promise<unknown>[] = [];
  const ctx = {
    waitUntil: (p: Promise<unknown>) => void pending.push(p),
    passThroughOnException() {},
  } as unknown as ExecutionContext;
  const call = async (path: string, init: RequestInit & { ip?: string } = {}) => {
    const { ip, ...rest } = init;
    const headers = new Headers(rest.headers);
    headers.set("CF-Connecting-IP", ip ?? "203.0.113.7");
    const res = await handle(new Request("https://edge.example.test" + path, { ...rest, headers }), env, ctx);
    await Promise.allSettled(pending.splice(0));
    return res;
  };
  return { env, kv, origin, ctx, call };
}
