import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Live } from "./api";
import { KEY_HEADER } from "./judge";

export function useApi<T>(path: string | null, refreshMs?: number) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!path) return;
    try {
      setData(await api<T>(path));
      setError(null);
    } catch (e) {
      setError(e as Error);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    setLoading(true);
    load();
    if (!refreshMs) return;
    const id = setInterval(load, refreshMs);
    return () => clearInterval(id);
  }, [load, refreshMs]);

  return { data, error, loading, reload: load };
}

export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

export function useInView<T extends Element>(options?: IntersectionObserverInit) {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setInView(true);
        io.disconnect();
      }
    }, options ?? { rootMargin: "-10% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, [options]);
  return { ref, inView };
}

export function useTitle(title: string | null) {
  useEffect(() => {
    document.title = title ? `${title} · Probate` : "Probate · My agent dies every night";
  }, [title]);
}

export type LiveView = {
  live: Live | null;
  /** The Courthouse can't be asked for a life (static preview, or it is unreachable). */
  unavailable: boolean;
  starting: boolean;
  /** A one-off note about the last click (rate limit, refusal). */
  notice: string | null;
  start: () => Promise<void>;
};

const ACTIVE = ["waking", "living", "on_trial"];

/** Polls GET /api/live (every 2 s while a life runs, else every 10 s) and starts lives.
 *  With the judge key it sends it as a header so the Courthouse applies the judge's own limits. */
export function useLive(judgeKey?: string | null, onKeyRefused?: () => void): LiveView {
  const [live, setLive] = useState<Live | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const active = !!live && ACTIVE.includes(live.state);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/live", { cache: "no-store", headers: judgeKey ? { [KEY_HEADER]: judgeKey } : {} });
      const data = await res.json();
      if (!res.ok || typeof data?.state !== "string") throw new Error("no live endpoint");
      setLive(data as Live);
      setUnavailable(false);
    } catch {
      setUnavailable(true);
    }
  }, [judgeKey]);

  useEffect(() => {
    load();
    const id = setInterval(load, active ? 2000 : 10000);
    return () => clearInterval(id);
  }, [load, active]);

  const start = useCallback(async () => {
    setStarting(true);
    setNotice(null);
    try {
      const res = await fetch("/api/lives", { method: "POST", headers: judgeKey ? { [KEY_HEADER]: judgeKey } : {} });
      const body = await res.json().catch(() => ({}));
      if (body?.error === "key_required" || body?.error === "invalid_key" || body?.error === "key_disabled") {
        setNotice(body.message ?? "The judge key was not accepted.");
        if (body.error !== "key_required") onKeyRefused?.();
        return;
      }
      if (body?.error === "too_many_attempts") {
        setNotice(body.message);
        return;
      }
      if (typeof body?.state !== "string") {
        setUnavailable(true); // a static preview answers 503 (or 404) with no state
        return;
      }
      setLive(body as Live);
      if (body.error === "rate_limited") {
        const mins = Math.max(1, Math.ceil((body.retry_after ?? 60) / 60));
        setNotice(`You've run a few lives already. Try again in about ${mins} ${mins === 1 ? "minute" : "minutes"}.`);
      } else if (body.error === "unavailable") {
        setNotice("The Courthouse isn't taking requests right now.");
      }
    } catch {
      setNotice("Couldn't reach the Courthouse. Try again in a moment.");
    } finally {
      setStarting(false);
    }
  }, [judgeKey, onKeyRefused]);

  return { live, unavailable, starting, notice, start };
}
