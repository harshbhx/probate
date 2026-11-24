// Floating glass navigation (pattern after Aceternity "Floating Navbar"), footer and page frame.
import { type ReactNode, useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { motion } from "motion/react";
import { cx } from "../../lib/format";
import type { Summary } from "../../lib/api";
import { Seal } from "./Seal";
import { LivePill } from "./LivePill";

const LINKS = [
  { to: "/", label: "Family", end: true },
  { to: "/trial", label: "Trials" },
  { to: "/instincts", label: "Instincts" },
  { to: "/evidence", label: "Evidence" },
];

export function Nav({ summary }: { summary: Summary | null }) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 12);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);
  return (
    <header className="fixed inset-x-0 top-3 z-50 px-3 sm:top-4">
      <nav
        aria-label="Main"
        className={cx(
          "glass mx-auto flex h-14 max-w-5xl items-center gap-2 rounded-2xl px-2.5 pl-3.5 transition-shadow duration-300",
          scrolled && "shadow-[0_12px_40px_-12px_rgb(0_0_0/0.7)]",
        )}
      >
        <Link to="/" className="mr-auto flex items-center gap-2.5 rounded-lg pr-2">
          <Seal size={28} />
          <span className="font-display text-[22px] leading-none tracking-tight">Probate</span>
        </Link>
        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <li key={l.to}>
              <NavLink
                to={l.to}
                end={l.end}
                className={({ isActive }) =>
                  cx(
                    "relative rounded-lg px-3 py-2 text-[14px] transition-colors",
                    isActive ? "text-moon" : "text-mist hover:text-moon",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.span
                        layoutId="nav-pill"
                        className="absolute inset-0 rounded-lg bg-white/[0.06] ring-1 ring-white/[0.08]"
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
        {summary?.living && <LivePill gen={summary.living} compact />}
      </nav>
      <MobileTabs />
    </header>
  );
}

function MobileTabs() {
  const loc = useLocation();
  return (
    <ul className="glass mx-auto mt-2 flex max-w-5xl justify-between rounded-xl p-1 md:hidden">
      {LINKS.map((l) => {
        const active = l.end ? loc.pathname === l.to : loc.pathname.startsWith(l.to);
        return (
          <li key={l.to} className="flex-1">
            <Link
              to={l.to}
              className={cx(
                "block rounded-lg py-2 text-center text-[13px]",
                active ? "bg-white/[0.07] text-moon" : "text-mist",
              )}
            >
              {l.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function SimBanner({ mode }: { mode?: string }) {
  if (mode !== "simulation") return null;
  return (
    <div className="mx-auto mb-8 flex max-w-6xl items-start gap-3 rounded-xl border border-amber/25 bg-amber/[0.06] px-4 py-3 text-[14px] text-amber/90">
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
      transition={{ duration: 0.4 }}
      className={cx("mx-auto max-w-6xl px-4 pb-24 sm:px-6", flush ? "pt-0" : "pt-32 md:pt-36", className)}
    >
      {children}
    </motion.main>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10 text-[14px] text-mist sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Seal size={22} />
          <span>Probate, the family of Harsh's agents. Every generation lives on its own Fly.io Sprite.</span>
        </div>
        <p className="text-dim">Built for Fly.io Hacksgiving 2026 by Harsh Bhanushali</p>
      </div>
    </footer>
  );
}
