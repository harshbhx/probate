import type { ReactNode } from 'react';
import { findEntry } from '@/lib/glossary';

/**
 * A hard word with a dotted underline. It is plain server-rendered HTML: one GlossLayer per page
 * (components/gloss-layer.tsx) shows the meaning on hover, focus or tap, so a page with thirty
 * marked words loads no extra JavaScript for them.
 */
export function Gloss({ term, children }: { term: string; children: ReactNode }) {
  if (!findEntry(term)) return <>{children}</>;
  return (
    <button type="button" className="gloss-word" data-gloss={term} aria-expanded="false">
      {children}
    </button>
  );
}
