import type {
  AskAnswer,
  CourthouseEvent,
  Evidence,
  GenerationDetail,
  Genome,
  Health,
  Summary,
  Trial,
} from "./types.js";

export class ApiError extends Error {
  readonly status: number;
  /** Parsed JSON body when the server sent one, otherwise undefined. */
  readonly body?: unknown;
  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export type ProbateClientOptions = {
  /** Courthouse origin. Default `http://localhost:8080`. */
  baseUrl?: string;
  /** Sent as `X-Probate-Key`. Reserved: the Courthouse does not check it today. */
  apiKey?: string;
  /** Per-request timeout in milliseconds. Default 30000. 0 disables it. */
  timeout?: number;
  /** Default AbortSignal for every call; a per-call `signal` is combined with it. */
  signal?: AbortSignal;
  /** Custom fetch (tests, proxies). Default: the global `fetch`. */
  fetch?: typeof fetch;
};

export type RequestOptions = { signal?: AbortSignal; timeout?: number };

export type EventsOptions = RequestOptions & {
  /** Only yield events with an id greater than this. Default 0. */
  since?: number;
  /** Milliseconds between polls. Default 5000. */
  intervalMs?: number;
};

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason);
    const onAbort = () => {
      clearTimeout(t);
      reject(signal!.reason);
    };
    const t = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

// AbortSignal.any needs Node 20.3+; this works on 18.
function combine(signals: AbortSignal[]): { signal?: AbortSignal; dispose: () => void } {
  if (signals.length === 0) return { dispose: () => {} };
  if (signals.length === 1) return { signal: signals[0], dispose: () => {} };
  const ctl = new AbortController();
  const offs: (() => void)[] = [];
  for (const s of signals) {
    if (s.aborted) {
      ctl.abort(s.reason);
      break;
    }
    const f = () => ctl.abort(s.reason);
    s.addEventListener("abort", f, { once: true });
    offs.push(() => s.removeEventListener("abort", f));
  }
  return { signal: ctl.signal, dispose: () => offs.forEach((o) => o()) };
}

function int(n: number): number {
  if (!Number.isInteger(n)) throw new TypeError(`Expected an integer, got ${n}`);
  return n;
}

export class ProbateClient {
  readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly timeout: number;
  private readonly signal?: AbortSignal;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ProbateClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? "http://localhost:8080").replace(/\/+$/, "");
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 30_000;
    this.signal = options.signal;
    this.fetchImpl = options.fetch ?? ((...a) => fetch(...a));
  }

  /** `GET /api/summary` */
  summary(o?: RequestOptions): Promise<Summary> {
    return this.request("GET", "/api/summary", undefined, o);
  }

  /** `GET /api/generations/{n}` */
  generation(n: number, o?: RequestOptions): Promise<GenerationDetail> {
    return this.request("GET", `/api/generations/${int(n)}`, undefined, o);
  }

  /** `GET /api/trials/{n}` */
  trial(n: number, o?: RequestOptions): Promise<Trial> {
    return this.request("GET", `/api/trials/${int(n)}`, undefined, o);
  }

  /** `GET /api/trials/latest` (404 ApiError until a generation has died). */
  latestTrial(o?: RequestOptions): Promise<Trial> {
    return this.request("GET", "/api/trials/latest", undefined, o);
  }

  /** `GET /api/genome`: the family's instincts. */
  genome(o?: RequestOptions): Promise<Genome> {
    return this.request("GET", "/api/genome", undefined, o);
  }

  /** Same as `genome()` but returns just the instinct list. */
  async instincts(o?: RequestOptions): Promise<Genome["instincts"]> {
    return (await this.genome(o)).instincts;
  }

  /** `GET /api/evidence` */
  evidence(o?: RequestOptions): Promise<Evidence> {
    return this.request("GET", "/api/evidence", undefined, o);
  }

  /** `GET /healthz` */
  health(o?: RequestOptions): Promise<Health> {
    return this.request("GET", "/healthz", undefined, o);
  }

  /**
   * `POST /api/generations/{n}/ask`. Only dead generations can be asked: others give
   * an ApiError with status 400 ("not_dead"). The server allows 10 asks a minute per IP (429).
   */
  ask(gen: number, question: string, o?: RequestOptions): Promise<AskAnswer> {
    return this.request("POST", `/api/generations/${int(gen)}/ask`, { question }, o);
  }

  /**
   * Follow `GET /api/events`. The Courthouse serves this route as a JSON list
   * (newest first, at most 50 rows, filtered by `?since=<id>`), not as a server-sent
   * stream, so this iterator polls it and yields each new event once, oldest first.
   * It runs until you `break`, abort the signal, or a request fails.
   */
  async *events(o: EventsOptions = {}): AsyncGenerator<CourthouseEvent, void, undefined> {
    let since = o.since ?? 0;
    const interval = o.intervalMs ?? 5000;
    for (;;) {
      const rows = await this.request<CourthouseEvent[]>(
        "GET",
        `/api/events?since=${int(since)}`,
        undefined,
        o,
      );
      for (const ev of [...rows].sort((a, b) => a.id - b.id)) {
        since = Math.max(since, ev.id);
        yield ev;
      }
      await sleep(interval, o.signal ?? this.signal);
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body: unknown,
    o: RequestOptions = {},
  ): Promise<T> {
    const signals: AbortSignal[] = [];
    if (this.signal) signals.push(this.signal);
    if (o.signal) signals.push(o.signal);
    const ms = o.timeout ?? this.timeout;
    if (ms > 0) signals.push(AbortSignal.timeout(ms));

    const headers: Record<string, string> = { Accept: "application/json" };
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (this.apiKey) headers["X-Probate-Key"] = this.apiKey;

    const { signal, dispose } = combine(signals);
    let res: Response;
    let text: string;
    try {
      res = await this.fetchImpl(this.baseUrl + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal,
      });
      text = await res.text();
    } finally {
      dispose();
    }
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : undefined;
    } catch {
      data = undefined;
    }
    if (!res.ok) {
      const d = data as { error?: unknown; detail?: unknown } | undefined;
      const msg = d?.error ?? d?.detail;
      throw new ApiError(
        res.status,
        typeof msg === "string" ? msg : res.statusText || `HTTP ${res.status}`,
        data,
      );
    }
    if (data === undefined) throw new ApiError(res.status, "Response was not JSON");
    return data as T;
  }
}
