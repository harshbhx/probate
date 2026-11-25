'use client';
// The product header: brand, sections, search, source, one primary action. Sticky, full width,
// a hairline once the page moves. On small screens the sections fold into a menu sheet.
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Menu, Search, X } from 'lucide-react';
import { useSearchContext } from 'fumadocs-ui/contexts/search';
import { GithubMark } from '@/components/icons';
import { Seal } from '@/components/seal';
import { githubUrl, liveUrl } from '@/lib/shared';
import { NAV } from './nav-links';

export function SiteHeader() {
  const { setOpenSearch } = useSearchContext();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 4);
    on();
    window.addEventListener('scroll', on, { passive: true });
    return () => window.removeEventListener('scroll', on);
  }, []);
  useEffect(() => {
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    window.addEventListener('keydown', esc);
    return () => window.removeEventListener('keydown', esc);
  }, [open]);

  const cta = liveUrl
    ? { label: 'Open the live family', href: liveUrl }
    : { label: 'Get started', href: '/docs/quickstart' };

  return (
    <header
      className={`sticky top-0 z-40 border-b backdrop-blur-md transition-colors ${
        scrolled || open ? 'border-line bg-night/85' : 'border-transparent bg-night/60'
      }`}
    >
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-night-3 focus:px-3 focus:py-2 focus:text-[14px]"
      >
        Skip to content
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-2 px-5 sm:px-6">
        <Link href="/" className="mr-5 flex items-center gap-2.5 rounded-md" aria-label="Probate home">
          <Seal size={26} />
          <span className="font-display text-[21px] leading-none tracking-[-0.01em]">Probate</span>
        </Link>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center gap-0.5">
            {NAV.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="rounded-md px-3 py-2 text-[14px] text-mist transition-colors hover:bg-night-3 hover:text-moon"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setOpenSearch(true)}
            className="hidden h-9 w-52 items-center gap-2 rounded-lg border border-line bg-night-2 px-3 text-[13.5px] text-dim transition-colors hover:border-line-strong hover:text-mist lg:flex"
          >
            <Search size={15} aria-hidden />
            Search
            <kbd className="ml-auto rounded border border-line px-1.5 font-mono text-[11px] text-mist">⌘K</kbd>
          </button>
          <button
            type="button"
            onClick={() => setOpenSearch(true)}
            aria-label="Search the docs"
            className="inline-flex size-9 items-center justify-center rounded-lg text-mist transition-colors hover:bg-night-3 hover:text-moon lg:hidden"
          >
            <Search size={17} />
          </button>
          {githubUrl && (
            <a
              href={githubUrl}
              aria-label="Source on GitHub"
              className="hidden size-9 items-center justify-center rounded-lg text-mist transition-colors hover:bg-night-3 hover:text-moon sm:inline-flex"
            >
              <GithubMark />
            </a>
          )}
          <Link
            href={cta.href}
            className="ml-1.5 hidden h-9 items-center rounded-lg bg-moon px-4 text-[14px] font-medium text-night transition-colors hover:bg-white sm:inline-flex"
          >
            {cta.label}
          </Link>
          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen((o) => !o)}
            className="inline-flex size-9 items-center justify-center rounded-lg text-moon transition-colors hover:bg-night-3 md:hidden"
          >
            {open ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </div>

      {open && (
        <div id="mobile-menu" className="border-t border-line bg-night md:hidden">
          <nav aria-label="Main" className="mx-auto max-w-6xl px-5 pb-6 pt-2">
            <ul>
              {NAV.map((l) => (
                <li key={l.href} className="border-b border-line">
                  <Link href={l.href} onClick={() => setOpen(false)} className="block py-3.5 text-[16px] text-moon">
                    {l.label}
                  </Link>
                </li>
              ))}
              {githubUrl && (
                <li className="border-b border-line">
                  <a href={githubUrl} className="flex items-center gap-2 py-3.5 text-[16px] text-moon">
                    <GithubMark /> Source on GitHub
                  </a>
                </li>
              )}
            </ul>
            <Link
              href={cta.href}
              onClick={() => setOpen(false)}
              className="mt-5 flex h-11 items-center justify-center rounded-lg bg-moon text-[15px] font-medium text-night"
            >
              {cta.label}
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
