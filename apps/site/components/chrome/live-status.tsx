'use client';
// Who is alive right now, read from the Courthouse's public summary. Renders nothing until it
// knows, and nothing at all when there is no live family (local builds, or the Courthouse is down).
import { useEffect, useState } from 'react';
import { liveUrl } from '@/lib/shared';

type Living = { gen: number; name: string };

export function LiveStatus({ className = '' }: { className?: string }) {
  const [living, setLiving] = useState<Living | null>(null);
  useEffect(() => {
    if (!liveUrl) return;
    const ctl = new AbortController();
    fetch(new URL('/api/summary', liveUrl), { signal: ctl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => s?.living && setLiving({ gen: s.living.gen, name: s.living.name }))
      .catch(() => {});
    return () => ctl.abort();
  }, []);
  if (!living) return null;
  return (
    <a
      href={new URL(`/gen/${living.gen}`, liveUrl).toString()}
      className={`inline-flex h-8 items-center gap-2 rounded-full border border-life/25 bg-life/[0.07] px-3 text-[13px] text-moon transition-colors hover:border-life/45 ${className}`}
    >
      <span className="relative flex size-2" aria-hidden>
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-life opacity-60" />
        <span className="relative inline-flex size-2 rounded-full bg-life" />
      </span>
      Gen {living.gen} {living.name} is alive
    </a>
  );
}
