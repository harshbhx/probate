'use client';
// The header is a floating pill: seal and wordmark on the left, the sections in the middle, search, source and one
// primary action on the right. It lifts off the page (blur and a hairline) once you scroll. On phones the pill
// keeps the lockup, search and a menu button, and the menu opens as a card beneath it with big tap targets.
import Link from '@/components/intent-link';
import { useEffect, useState } from 'react';
import { ArrowRight, Menu, Search, X } from 'lucide-react';
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
    const on = () => setScrolled(window.scrollY > 8);
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
    ? { label: 'Open the live family', short: 'Open the live family', href: liveUrl }
    : { label: 'Get started', short: 'Get started', href: '/docs/quickstart' };

  return (
    <header className="sticky top-0 z-40 px-3 pt-3 sm:px-5">
      <a
        href="#content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:z-50 focus:rounded-md focus:bg-night-3 focus:px-3 focus:py-2 focus:text-[14px]"
      >
        Skip to content
      </a>
      <div
        className={`mx-auto flex h-14 max-w-5xl items-center gap-1 rounded-full border pl-4 pr-2 backdrop-blur-xl transition-[background-color,border-color,box-shadow] duration-300 ${
          scrolled || open
            ? 'border-line-strong bg-night/80 shadow-[0_18px_50px_-24px_rgb(0_0_0/0.9)]'
            : 'border-line bg-night/40'
        }`}
      >
        <Link href="/" className="mr-2 flex items-center gap-2.5 rounded-full py-1 pr-2" aria-label="Probate home">
          <Seal size={28} />
          <span className="font-display text-[22px] leading-none tracking-[-0.01em]">Probate</span>
        </Link>

        <nav aria-label="Main" className="hidden md:block">
          <ul className="flex items-center">
            {NAV.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="rounded-full px-3.5 py-2 text-[14.5px] text-mist transition-colors hover:bg-night-3 hover:text-moon"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <button
            type="button"
            onClick={() => setOpenSearch(true)}
            aria-label="Search the docs"
            className="inline-flex size-11 items-center justify-center rounded-full text-mist transition-colors hover:bg-night-3 hover:text-moon md:size-10"
          >
            <Search size={17} />
          </button>
          {githubUrl && (
            <a
              href={githubUrl}
              aria-label="Source on GitHub"
              className="hidden size-10 items-center justify-center rounded-full text-mist transition-colors hover:bg-night-3 hover:text-moon sm:inline-flex"
            >
              <GithubMark />
            </a>
          )}
          <Link
            href={cta.href}
            className="ml-1 hidden h-10 items-center gap-1.5 rounded-full bg-moon px-4 text-[14.5px] font-medium text-night transition-colors hover:bg-white sm:inline-flex"
          >
            {cta.label}
            <ArrowRight size={15} aria-hidden />
          </Link>
          <button
            type="button"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? 'Close menu' : 'Open menu'}
            onClick={() => setOpen((o) => !o)}
            className="inline-flex size-11 items-center justify-center rounded-full bg-night-3 text-moon transition-colors hover:bg-night-4 md:hidden"
          >
            {open ? <X size={19} /> : <Menu size={19} />}
          </button>
        </div>
      </div>

      {open && (
        <div
          id="mobile-menu"
          className="mx-auto mt-2 max-w-5xl overflow-hidden rounded-3xl border border-line-strong bg-night/95 p-2 shadow-[0_30px_80px_-30px_rgb(0_0_0/0.95)] backdrop-blur-xl md:hidden"
        >
          <nav aria-label="Main">
            <ul>
              {NAV.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="flex min-h-14 items-center justify-between rounded-2xl px-4 font-display text-[26px] text-moon transition-colors active:bg-night-3"
                  >
                    {l.label}
                    <ArrowRight size={18} className="text-dim" aria-hidden />
                  </Link>
                </li>
              ))}
            </ul>
            <div className="mt-2 flex gap-2 p-2">
              <Link
                href={cta.href}
                onClick={() => setOpen(false)}
                className="flex h-12 flex-1 items-center justify-center rounded-full bg-moon text-[16px] font-medium text-night"
              >
                {cta.short}
              </Link>
              {githubUrl && (
                <a
                  href={githubUrl}
                  aria-label="Source on GitHub"
                  className="flex size-12 items-center justify-center rounded-full border border-line-strong text-moon"
                >
                  <GithubMark />
                </a>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
