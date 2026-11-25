// The Probate seal: a court seal around a three-generation family tree.
// The red tick is an inheritance the court refused.
export function Seal({ size = 32, className }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" role="img" aria-label="Probate seal" className={className}>
      <circle cx="32" cy="32" r="29" fill="none" stroke="var(--color-gilt)" strokeWidth="2.5" />
      <circle cx="32" cy="32" r="24.5" fill="none" stroke="var(--color-gilt)" strokeWidth="1" opacity="0.7" />
      <g fill="none" stroke="var(--color-moon)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
        <path d="M32 18.5 V24 H22.5 V30" />
        <path d="M32 24 H41.5 V30" />
        <path d="M22.5 36 V43" />
        <path d="M41.5 36 V38.5" />
      </g>
      <g fill="var(--color-moon)">
        <circle cx="32" cy="16" r="3.2" />
        <circle cx="22.5" cy="33" r="3.2" />
        <circle cx="41.5" cy="33" r="3.2" />
        <circle cx="22.5" cy="46" r="3.2" />
      </g>
      <path d="M37.5 44.5 L45.5 40.5" stroke="var(--color-verdict)" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  );
}
