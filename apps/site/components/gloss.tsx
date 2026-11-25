'use client';

import { Popover } from '@base-ui/react/popover';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { findEntry, glossAnchor } from '@/lib/glossary';
import { docsRoute } from '@/lib/shared';

/** A hard word with its definition on hover, focus or tap. */
export function Gloss({ term, children }: { term: string; children: ReactNode }) {
  const entry = findEntry(term);
  if (!entry) return <>{children}</>;
  return (
    <Popover.Root>
      <Popover.Trigger
        openOnHover
        delay={120}
        closeDelay={80}
        className="gloss-word"
        aria-label={`${typeof children === 'string' ? children : entry.term}: show what this means`}
      >
        {children}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner sideOffset={8} collisionPadding={12} className="z-50">
          <Popover.Popup className="gloss-card">
            <Popover.Title className="gloss-term">{entry.term}</Popover.Title>
            <Popover.Description className="gloss-def">{entry.def}</Popover.Description>
            <Link href={`${docsRoute}/glossary#${glossAnchor(entry.term)}`} className="gloss-more">
              Read more in the glossary
            </Link>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
