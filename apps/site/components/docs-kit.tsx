// Docs building blocks: the pieces that make a page easy to scan before you read it.
// Night Court rules: one accent (gilt), hairlines, verdict colours only for meaning.
import type { ReactNode } from 'react';
import { GLOSSARY, glossAnchor } from '@/lib/glossary';
import Link from 'next/link';
import { icons } from 'lucide-react';
import { cn } from '@/lib/cn';
import { liveUrl } from '@/lib/shared';

function Icon({ name, className }: { name?: string; className?: string }) {
  const I = name ? icons[name as keyof typeof icons] : undefined;
  return I ? <I aria-hidden className={cn('size-4 shrink-0', className)} /> : null;
}

/** "In short": what the page says, for readers who stop here. */
export function Summary({ children, who }: { children: ReactNode; who?: string }) {
  return (
    <div className="not-prose my-6 rounded-xl border border-line bg-night-2 p-5">
      <p className="mb-2 flex flex-wrap items-baseline gap-x-3 text-[13px] text-mist">
        <span className="font-medium text-gilt">In short</span>
        {who && <span>For {who}</span>}
      </p>
      <div className="text-[15px] leading-relaxed text-silver [&_strong]:font-medium [&_strong]:text-moon [&_a]:underline [&_a]:decoration-gilt/50 [&_a]:underline-offset-4 [&_code]:text-[13px] [&_code]:text-moon">
        {children}
      </div>
    </div>
  );
}

/**
 * A link into the live family site. Its address is only known at build time
 * (NEXT_PUBLIC_LIVE_URL); without it, the fallback text is shown instead of a dead link.
 */
export function LiveLink({ path = '/', fallback, children }: { path?: string; fallback: ReactNode; children: ReactNode }) {
  if (!liveUrl) return <>{fallback}</>;
  return <a href={new URL(path, liveUrl).toString()}>{children}</a>;
}

/** The same idea without the jargon. */
export function PlainWords({ children, title = 'In plain words' }: { children: ReactNode; title?: string }) {
  return (
    <aside className="not-prose my-6 border-l-2 border-gilt/60 pl-4">
      <p className="mb-1 text-[13px] font-medium text-gilt">{title}</p>
      <div className="text-[15px] leading-relaxed text-silver">{children}</div>
    </aside>
  );
}

/** A row of headline numbers. */
export function StatRow({ children, note }: { children: ReactNode; note?: ReactNode }) {
  return (
    <figure className="not-prose my-6">
      <div className="grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-line [gap:1px] sm:grid-cols-4">
        {children}
      </div>
      {note && <figcaption className="mt-2 text-[13px] text-dim">{note}</figcaption>}
    </figure>
  );
}

const TONE = { neutral: 'text-moon', good: 'text-life', bad: 'text-verdict', warn: 'text-amber', gilt: 'text-gilt' } as const;

export function Stat({ value, label, tone = 'neutral' }: { value: ReactNode; label: ReactNode; tone?: keyof typeof TONE }) {
  return (
    <div className="bg-night-2 p-4">
      <div className={cn('font-display text-[32px] leading-none tracking-tight', TONE[tone])}>{value}</div>
      <div className="mt-2 text-[13px] leading-snug text-mist">{label}</div>
    </div>
  );
}

const BADGE = {
  live: 'border-life/50 text-life',
  done: 'border-life/50 text-life',
  simulated: 'border-amber/50 text-amber',
  next: 'border-line-strong text-mist',
  measured: 'border-gilt/50 text-gilt',
} as const;

/** What is real today, what is simulated, and what comes next. */
export function StatusList({ children, asOf }: { children: ReactNode; asOf?: string }) {
  return (
    <div className="not-prose my-6">
      <ul className="divide-y divide-line overflow-hidden rounded-xl border border-line bg-night-2">{children}</ul>
      {asOf && <p className="mt-2 text-[13px] text-dim">{asOf}</p>}
    </div>
  );
}

export function Status({
  state,
  title,
  href,
  children,
}: {
  state: keyof typeof BADGE;
  title: string;
  href?: string;
  children?: ReactNode;
}) {
  const body = (
    <>
      <span className={cn('mt-0.5 w-[84px] shrink-0 self-start rounded-md border px-2 py-0.5 text-center font-mono text-[11px] capitalize', BADGE[state])}>
        {state}
      </span>
      <span className="min-w-0">
        <span className="block text-[15px] font-medium text-moon">{title}</span>
        {children && <span className="mt-0.5 block text-[14px] leading-relaxed text-mist">{children}</span>}
      </span>
    </>
  );
  return (
    <li>
      {href ? (
        <Link href={href} className="flex gap-4 p-4 transition-colors hover:bg-night-3">
          {body}
        </Link>
      ) : (
        <div className="flex gap-4 p-4">{body}</div>
      )}
    </li>
  );
}

/** A journey through the system, one stop per step. */
export function Flow({ children }: { children: ReactNode }) {
  return <ol className="not-prose relative my-8 ml-3 border-l border-line">{children}</ol>;
}

export function FlowStep({
  title,
  where,
  icon,
  children,
}: {
  title: string;
  where?: string;
  icon?: string;
  children: ReactNode;
}) {
  return (
    <li className="relative pb-8 pl-8 last:pb-0">
      <span className="absolute -left-[13px] top-0 flex size-[26px] items-center justify-center rounded-full border border-line-strong bg-night-2 text-gilt">
        <Icon name={icon ?? 'Circle'} className="size-3.5" />
      </span>
      <p className="flex flex-wrap items-baseline gap-x-3">
        <span className="text-[16px] font-medium text-moon">{title}</span>
        {where && <span className="font-mono text-[12px] text-dim">{where}</span>}
      </p>
      <div className="mt-1.5 text-[15px] leading-relaxed text-silver [&_code]:rounded [&_code]:border [&_code]:border-line [&_code]:bg-night-3 [&_code]:px-1 [&_code]:text-[13px] [&_code]:text-moon [&_a]:underline [&_a]:decoration-gilt/50 [&_a]:underline-offset-4 [&_p+p]:mt-2">
        {children}
      </div>
    </li>
  );
}

/** Ways into the docs, by what the reader wants. */
export function PathGrid({ children }: { children: ReactNode }) {
  return <div className="not-prose my-6 grid gap-3 sm:grid-cols-2">{children}</div>;
}

export function PathCard({
  title,
  href,
  icon,
  children,
}: {
  title: string;
  href: string;
  icon?: string;
  children: ReactNode;
}) {
  const external = href.startsWith('http');
  return (
    <Link
      href={href}
      {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}
      className="group flex gap-3.5 rounded-xl border border-line bg-night-2 p-4 transition-colors hover:border-gilt/45 hover:bg-night-3"
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-night-3 text-gilt">
        <Icon name={icon} />
      </span>
      <span className="min-w-0">
        <span className="block text-[15px] font-medium text-moon">{title}</span>
        <span className="mt-0.5 block text-[14px] leading-snug text-mist">{children}</span>
      </span>
    </Link>
  );
}

/** A definition list: term on the left, meaning on the right. */
export function Terms({ children }: { children: ReactNode }) {
  return <dl className="not-prose my-6 divide-y divide-line overflow-hidden rounded-xl border border-line bg-night-2">{children}</dl>;
}

export function Term({ name, id, children }: { name: string; id?: string; children: ReactNode }) {
  return (
    <div id={id ?? name.toLowerCase().replace(/\s+/g, '-')} className="grid scroll-mt-24 gap-1 p-4 sm:grid-cols-[180px_1fr] sm:gap-6">
      <dt className="text-[15px] font-medium text-moon">{name}</dt>
      <dd className="text-[15px] leading-relaxed text-silver [&_code]:text-[13px] [&_code]:text-moon">{children}</dd>
    </div>
  );
}

/** A judge's company and the job its product does here. */
export function Partner({ name, judge, icon, children }: { name: string; judge?: string; icon?: string; children: ReactNode }) {
  return (
    <div className="flex gap-3.5 p-4">
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-night-3 text-gilt">
        <Icon name={icon ?? 'Puzzle'} />
      </span>
      <div className="min-w-0">
        <p className="flex flex-wrap items-baseline gap-x-3">
          <span className="text-[15px] font-medium text-moon">{name}</span>
          {judge && <span className="text-[13px] text-dim">judged by {judge}</span>}
        </p>
        <div className="mt-0.5 text-[14px] leading-relaxed text-mist [&_a]:text-silver [&_a]:underline [&_a]:decoration-gilt/50 [&_a]:underline-offset-4">{children}</div>
      </div>
    </div>
  );
}

export function Partners({ children }: { children: ReactNode }) {
  return <div className="not-prose my-6 grid overflow-hidden rounded-xl border border-line bg-line [gap:1px] sm:grid-cols-2 [&>*]:bg-night-2">{children}</div>;
}

/** The glossary words not written out on the Glossary page itself, from lib/glossary.ts. */
export function MoreTerms() {
  return (
    <Terms>
      {GLOSSARY.filter((e) => e.more).map((e) => (
        <Term key={e.term} name={e.term} id={glossAnchor(e.term)}>
          {e.def}
        </Term>
      ))}
    </Terms>
  );
}
