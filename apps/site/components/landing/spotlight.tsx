// A plain landing card: surface 1, a hairline, 12px radius. (The pointer light was removed in
// Night Court v3; the name stays so call sites read the same.)
import type { ReactNode } from 'react';

export function Spotlight({ children, className = '' }: { children: ReactNode; className?: string; color?: string }) {
  return <div className={`min-w-0 rounded-xl border border-line bg-night-2 ${className}`}>{children}</div>;
}
