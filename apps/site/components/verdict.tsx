// The court's verdict stamp, for use in docs and on the landing page.
const STYLES = {
  convicted: 'text-verdict border-verdict/70 bg-verdict/[0.06]',
  approved: 'text-life border-life/60 bg-life/[0.05]',
  contested: 'text-amber border-amber/60 bg-amber/[0.06]',
} as const;

export function Verdict({ v, className = '' }: { v: keyof typeof STYLES; className?: string }) {
  return (
    <span
      className={`not-prose inline-flex -rotate-3 select-none items-center rounded-md border-2 px-2.5 py-1 font-mono text-[11px] font-semibold tracking-[0.14em] ${STYLES[v]} ${className}`}
    >
      {v.toUpperCase()}
    </span>
  );
}
