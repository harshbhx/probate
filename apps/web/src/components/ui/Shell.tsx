// Product header (sticky, full width, hairline), mobile tab bar, footer and page frame.
// Rules: docs/04-DESIGN.md, Night Court v3.
import { type ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { BookOpen } from "lucide-react";
import { cx } from "../../lib/format";
import type { Summary } from "../../lib/api";
import { Seal } from "./Seal";
import { LivePill } from "./LivePill";

// Set at build time by scripts/ship.sh once the docs site and repo exist. Links hide when empty.
const DOCS_URL: string = import.meta.env.VITE_DOCS_URL ?? "";
const REPO_URL: string = import.meta.env.VITE_REPO_URL ?? "";

const LINKS = [
  { to: "/", label: "Family", end: true },
  { to: "/trial", label: "Trials" },
  { to: "/instincts", label: "Instincts" },
  { to: "/evidence", label: "Evidence" },
];

export function Nav({ summary }: { summary: Summary | null }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 4);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header
      className={cx(
        "sticky top-0 z-50 border-b bg-night/80 backdrop-blur-md transition-colors",
        scrolled ? "border-line" : "border-transparent",
      )}
    >
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-3 focus:rounded-md focus:bg-night-3 focus:px-3 focus:py-2">
        Skip to content
      </a>
      <nav aria-label="Main" className="mx-auto flex h-16 max-w-6xl items-center gap-1 px-4 sm:px-6">
        <Link to="/" className="mr-6 flex items-center gap-2.5 rounded-md">
          <Seal size={26} />
          <span className="font-display text-[21px] leading-none tracking-[-0.01em]">Probate</span>
        </Link>
        <ul className="hidden items-center gap-0.5 md:flex">
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  cx(
                    "relative rounded-md px-3 py-2 text-[14px] transition-colors",
                    isActive ? "text-moon" : "text-mist hover:text-moon",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill"
                        className="absolute inset-0 rounded-md bg-night-3"
                        transition={{ type: "spring", stiffness: 420, damping: 34 }}
                      />
                    )}
                    <span className="relative">{l.label}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="ml-auto flex items-center gap-2">
          {DOCS_URL && (
            <a
              href={DOCS_URL + "/docs"}
              className="hidden h-9 items-center gap-2 rounded-md px-3 text-[14px] text-mist transition-colors hover:text-moon sm:inline-flex"
            >
              <BookOpen size={15} aria-hidden /> Docs
            </a>
          )}
          {summary?.living && <LivePill gen={summary.living} compact />}
        </div>
      </nav>
    </header>
  );
}

export function MobileTabs() {
  const loc = useLocation();
  return (
    <nav aria-label="Sections" className="fixed inset-x-3 bottom-[max(12px,env(safe-area-inset-bottom))] z-50 md:hidden">
      <ul className="glass flex justify-between rounded-2xl p-1.5 shadow-[0_12px_40px_-12px_rgb(0_0_0/0.8)]">
        {LINKS.map((l) => {
          const active = l.end ? loc.pathname === l.to : loc.pathname.startsWith(l.to);
          return (
            <li key={l.to} className="relative flex-1">
              {active && (
                <motion.span
                  layoutId="mobile-tab"
                  className="absolute inset-0 rounded-xl bg-night-4"
                  transition={{ type: "spring", stiffness: 420, damping: 34 }}
                />
              )}
              <Link
                to={l.to}
                aria-current={active ? "page" : undefined}
                className={cx("relative block rounded-xl py-2.5 text-center text-[14px]", active ? "text-moon" : "text-mist")}
              >
                {l.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function SimBanner({ mode }: { mode?: string }) {
  if (mode !== "simulation") return null;
  return (
    <div className="mx-auto mb-8 flex max-w-6xl items-start gap-3 rounded-lg border border-amber/25 bg-amber/[0.06] px-4 py-3 text-[14px] text-amber">
      <span className="mt-1.5 inline-block size-1.5 shrink-0 rounded-full bg-amber" />
      <p>
        Simulated run. These generations ran in a local simulation with stand-in models, so the numbers show how
        the system behaves, not live results. The live family runs on Fly.io Sprites.
      </p>
    </div>
  );
}

export function Page({ children, className, flush = false }: { children: ReactNode; className?: string; flush?: boolean }) {
  return (
    <motion.main
      id="main"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className={cx("mx-auto max-w-6xl px-4 pb-24 sm:px-6", flush ? "pt-0" : "pt-10 md:pt-16", className)}
    >
      {children}
    </motion.main>
  );
}

type FootLink = { label: string; href: string; internal?: boolean };

export function Footer() {
  const cols: { title: string; links: FootLink[] }[] = [
    {
      title: "The family",
      links: LINKS.map((l) => ({ label: l.label, href: l.to, internal: true })),
    },
    {
      title: "Learn",
      links: DOCS_URL
        ? [
            { label: "How it works", href: DOCS_URL + "/docs" },
            { label: "The court", href: DOCS_URL + "/docs/concepts/court" },
            { label: "Instincts", href: DOCS_URL + "/docs/concepts/instincts" },
            { label: "Architecture", href: DOCS_URL + "/docs/architecture/overview" },
          ]
        : [{ label: "Evidence", href: "/evidence", internal: true }],
    },
    {
      title: "Project",
      links: [
        ...(REPO_URL ? [{ label: "Source on GitHub", href: REPO_URL }] : []),
        ...(DOCS_URL ? [{ label: "Security model", href: DOCS_URL + "/docs/security" }] : []),
        { label: "Fly.io Hacksgiving", href: "https://fly.io/hacksgiving/" },
      ],
    },
  ];
  return (
    <footer className="border-t border-line bg-night pb-24 md:pb-0">
      <div className="mx-auto grid max-w-6xl gap-10 px-6 py-14 md:grid-cols-[1.4fr_repeat(3,1fr)]">
        <div className="max-w-xs">
          <Link to="/" className="inline-flex items-center gap-2.5 rounded-md">
            <Seal size={24} />
            <span className="font-display text-[20px] leading-none">Probate</span>
          </Link>
          <p className="mt-4 text-[14px] leading-relaxed text-mist">
            Harsh's email agent. It lives one day on its own Fly.io Sprite, then a court decides what its child inherits.
          </p>
        </div>
        {cols.map((c) => (
          <nav key={c.title} aria-label={c.title}>
            <h2 className="text-[13px] font-medium text-moon">{c.title}</h2>
            <ul className="mt-4 space-y-2.5">
              {c.links.map((l) => (
                <li key={l.label}>
                  {l.internal ? (
                    <Link to={l.href} className="text-[14px] text-mist transition-colors hover:text-moon">{l.label}</Link>
                  ) : (
                    <a href={l.href} className="text-[14px] text-mist transition-colors hover:text-moon">{l.label}</a>
                  )}
                </li>
              ))}
            </ul>
          </nav>
        ))}
      </div>
      <div className="border-t border-line">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 px-6 py-6 text-[13px] text-dim sm:flex-row sm:justify-between">
          <span>Built by Harsh Bhanushali for Fly.io Hacksgiving 2026.</span>
          <span>Every generation lives on its own Sprite. No keys live on a generation.</span>
        </div>
      </div>
    </footer>
  );
}
