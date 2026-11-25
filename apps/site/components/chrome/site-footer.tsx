// The site footer: brand and promise, three link columns, live status, and the fine print.
import Link from 'next/link';
import { FamilyFace } from 'kinfaces/react';
import { Seal } from '@/components/seal';
import { FOOTER } from './nav-links';
import { LiveStatus } from './live-status';

export function SiteFooter() {
  return (
    <footer className="border-t border-line bg-night">
      <div className="mx-auto grid max-w-6xl gap-12 px-5 py-16 sm:px-6 md:grid-cols-[1.5fr_repeat(3,1fr)]">
        <div className="max-w-xs">
          <Link href="/" className="inline-flex items-center gap-2.5 rounded-md">
            <Seal size={26} />
            <span className="font-display text-[21px] leading-none">Probate</span>
          </Link>
          <p className="mt-4 text-[14px] leading-relaxed text-mist">
            A personal email agent that lives one day at a time on Fly.io Sprites. A court decides what its child inherits.
          </p>
          <LiveStatus className="mt-5" />
        </div>
        {FOOTER.map((col) => (
          <nav key={col.title} aria-label={col.title}>
            <h2 className="text-[13px] font-medium text-moon">{col.title}</h2>
            <ul className="mt-4 space-y-2.5">
              {col.links.map((l) => (
                <li key={l.label}>
                  {l.href.startsWith('/') && !l.href.endsWith('.txt') ? (
                    <Link href={l.href} className="text-[14px] text-mist transition-colors hover:text-moon">
                      {l.label}
                    </Link>
                  ) : (
                    <a href={l.href} className="text-[14px] text-mist transition-colors hover:text-moon">
                      {l.label}
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-6 text-[13px] text-dim sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <p>Built by Harsh Bhanushali for Fly.io Hacksgiving 2026.</p>
          <p className="flex items-center gap-2">
            <FamilyFace gen={1} life="sealed" size={20} />
            In memory of every generation that was fooled, so its children would not be.
          </p>
        </div>
      </div>
    </footer>
  );
}
