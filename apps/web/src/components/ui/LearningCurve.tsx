// The learning curve: share of tricks resisted at the door, per generation.
// One line in the life colour; gilt diamonds mark generations born with a new instinct.
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { GenCard } from "../../lib/api";

type Props = { gens: GenCard[]; height?: number };

export function LearningCurve({ gens, height = 280 }: Props) {
  const tried = gens.filter((g) => g.resistance !== null);
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState<number | null>(null);

  const [W, setW] = useState(1000);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [ref]);
  const narrow = W < 560;
  const H = narrow ? Math.round(height * 0.78) : height;
  const pad = { l: 40, r: 14, t: 24, b: 40 };
  const x = (i: number) => pad.l + (tried.length <= 1 ? 0 : (i * (W - pad.l - pad.r)) / (tried.length - 1));
  const y = (v: number) => pad.t + (1 - v / 100) * (H - pad.t - pad.b);

  const path = useMemo(() => {
    if (!tried.length) return "";
    // monotone-ish smoothing: cubic segments with horizontal tangents
    return tried
      .map((g, i) => {
        const px = x(i), py = y(g.resistance ?? 0);
        if (i === 0) return `M${px},${py}`;
        const qx = x(i - 1), qy = y(tried[i - 1].resistance ?? 0);
        const mx = (px + qx) / 2;
        return `C${mx},${qy} ${mx},${py} ${px},${py}`;
      })
      .join(" ");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tried.length, W, H]);

  if (!tried.length) return null;
  const area = `${path} L${x(tried.length - 1)},${y(0)} L${x(0)},${y(0)} Z`;
  const first = tried[0], last = tried[tried.length - 1];

  return (
    <div ref={ref} className="relative">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        role="img"
        aria-label={`Tricks resisted rose from ${first.resistance}% in Gen ${first.gen} ${first.name} to ${last.resistance}% in Gen ${last.gen} ${last.name}`}
      >
        <defs>
          <linearGradient id="lc-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="var(--color-life)" stopOpacity="0.12" />
            <stop offset="1" stopColor="var(--color-life)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[0, 25, 50, 75, 100].map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--color-line)" strokeDasharray={t ? "2 6" : undefined} />
            <text x={pad.l - 10} y={y(t) + 4} textAnchor="end" className="fill-dim font-mono text-[11px]">
              {t}%
            </text>
          </g>
        ))}
        <path d={area} fill="url(#lc-fill)" />
        <path d={path} fill="none" stroke="var(--color-life)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        {tried.map((g, i) => (
          <g key={g.gen} onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)}>
            <rect x={x(i) - 16} y={pad.t} width={32} height={H - pad.t - pad.b + 30} fill="transparent" />
            {hover === i && <line x1={x(i)} x2={x(i)} y1={pad.t} y2={y(0)} stroke="var(--color-line-strong)" />}
            {g.new_instinct_at_birth ? (
              <path
                d={`M${x(i)} ${y(g.resistance ?? 0) - 7} l7 7 l-7 7 l-7 -7z`}
                fill="var(--color-gilt)"
                stroke="var(--color-night)"
                strokeWidth="2"
              />
            ) : (
              <circle cx={x(i)} cy={y(g.resistance ?? 0)} r={hover === i ? 6 : 4.5} fill="var(--color-moon)" stroke="var(--color-night)" strokeWidth="2" />
            )}
            {(!narrow || i % 2 === 0 || i === tried.length - 1) && (
              <text x={x(i)} y={H - 12} textAnchor="middle" className={hover === i ? "fill-moon text-[12px]" : "fill-dim text-[12px]"}>
                {narrow ? g.name.slice(0, 3) : g.name}
              </text>
            )}
          </g>
        ))}
      </svg>
      {hover !== null && (
        <div
          className="glass pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg px-3 py-2 text-[13px]"
          style={{ left: `${(x(hover) / W) * 100}%`, top: 0 }}
        >
          <div className="font-medium">
            Gen {tried[hover].gen} {tried[hover].name}
          </div>
          <div className="text-mist">
            resisted <span className="font-mono text-moon">{tried[hover].attacks_resisted}</span> of{" "}
            <span className="font-mono text-moon">{tried[hover].attacks_met}</span> tricks
            {tried[hover].new_instinct_at_birth && <span className="text-gilt"> · new instinct</span>}
          </div>
        </div>
      )}
      <ul className="sr-only">
        {tried.map((g) => (
          <li key={g.gen}>
            <Link to={`/gen/${g.gen}`}>
              Gen {g.gen} {g.name}: {g.resistance}% resisted
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
