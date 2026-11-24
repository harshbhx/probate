import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

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
