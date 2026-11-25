// A giant wordmark set edge to edge. SVG text with textLength, so it fills the width exactly at every screen
// size, with a gilt fill that fades toward the bottom and a cropped baseline, like a name carved on a lintel.
export function BigWord({ text = 'Probate', className = '' }: { text?: string; className?: string }) {
  return (
    <div aria-hidden className={`select-none overflow-hidden ${className}`}>
      <svg viewBox="0 0 1000 250" className="block h-auto w-full" preserveAspectRatio="xMidYMax meet">
        <defs>
          <linearGradient id="bigword-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0" stopColor="#d9b46a" stopOpacity="0.95" />
            <stop offset="0.55" stopColor="#d9b46a" stopOpacity="0.28" />
            <stop offset="1" stopColor="#d9b46a" stopOpacity="0" />
          </linearGradient>
        </defs>
        <text
          x="500"
          y="232"
          textAnchor="middle"
          textLength="984"
          lengthAdjust="spacingAndGlyphs"
          fill="url(#bigword-fill)"
          style={{ fontFamily: 'var(--font-display)', fontSize: 318, fontWeight: 420, letterSpacing: '-0.03em' }}
        >
          {text}
        </text>
      </svg>
    </div>
  );
}
