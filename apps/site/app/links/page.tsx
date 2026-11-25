// /links: every Probate link on one phone-sized page, for a bio, a QR code or the submission form.
// A link whose address isn't set yet (live site, video, write-up, post) is left out rather than shown broken.
import type { Metadata } from 'next';
import type { LucideIcon } from 'lucide-react';
import {
  Accessibility,
  ArrowUpRight,
  BookOpen,
  Bot,
  Braces,
  ClipboardCheck,
  Code2,
  Database,
  FileText,
  Gavel,
  Mail,
  MessageCircle,
  Package,
  Play,
  Radio,
  Table2,
  Trophy,
  User,
} from 'lucide-react';
import { FamilyFace } from 'kinfaces/react';
import Link from '@/components/intent-link';
import { appName, articleUrl, githubUrl, liveUrl, postUrl, videoUrl } from '@/lib/shared';

export const metadata: Metadata = {
  title: 'Links',
  description: 'Every Probate link in one place: the live family, the docs, the code, the packages and the open datasets.',
};

type Item = { icon: LucideIcon; label: string; note: string; href: string };
type Group = { title: string; items: Item[] };

const HF = 'https://huggingface.co/datasets/harshbhx';
const repo = githubUrl || 'https://github.com/harshbhx/probate';

const GROUPS: Group[] = [
  {
    title: 'See it work',
    items: [
      { icon: Radio, label: 'The live family', note: 'Running on Fly.io Sprites right now', href: liveUrl },
      { icon: Trophy, label: 'Start here, judges', note: 'What to open and try in five minutes', href: '/docs/for-judges' },
      { icon: Gavel, label: 'Try the court', note: 'Real code checks on real test emails', href: '/#court' },
      { icon: Play, label: 'The 90-second video', note: 'One generation fooled, the next one not', href: videoUrl },
    ],
  },
  {
    title: 'Read',
    items: [
      { icon: FileText, label: 'The write-up', note: 'Why an agent should die every night', href: articleUrl },
      { icon: BookOpen, label: 'The docs', note: 'Concepts, architecture, deploying and costs', href: '/docs' },
      { icon: ClipboardCheck, label: 'Proof for every claim', note: 'A command or a page next to each one', href: '/docs/proof' },
      { icon: Braces, label: 'API reference', note: 'Every Courthouse route, with real example replies', href: '/docs/reference/api' },
      { icon: Accessibility, label: 'Accessibility', note: 'PageSpeed scores and what axe found', href: '/docs/accessibility' },
      { icon: MessageCircle, label: 'The post', note: 'Share it, or reply with a question', href: postUrl },
    ],
  },
  {
    title: 'Code and data',
    items: [
      { icon: Code2, label: 'Source code', note: 'Open source, with the attack suite and 341 tests', href: repo },
      { icon: Package, label: 'Packages', note: 'kinfaces, the API clients and the court checks', href: `${repo}#packages` },
      { icon: Database, label: 'Dataset: the attack suite', note: '16 tricks and their 16 harmless twins, in four languages', href: `${HF}/probate-attack-suite` },
      { icon: Table2, label: 'Dataset: simulated runs', note: '12 generations and 96 outcomes, from stand-in models (simulated)', href: `${HF}/probate-simulated-runs` },
      { icon: Bot, label: 'llms.txt', note: 'The whole docs as plain text, for AI agents', href: '/llms-full.txt' },
    ],
  },
  {
    title: 'Made by',
    items: [
      { icon: User, label: 'Harsh Bhanushali', note: 'B.Tech student who builds AI agents', href: 'https://github.com/harshbhx' },
      { icon: Mail, label: 'Email', note: 'harshbhx@gmail.com', href: 'mailto:harshbhx@gmail.com' },
    ],
  },
];

function Row({ icon: Icon, label, note, href }: Item) {
  const external = !href.startsWith('/');
  const cls =
    'group flex min-h-16 items-center gap-3.5 rounded-xl border border-line bg-night-2 px-4 py-3 transition-colors hover:border-gilt/60 hover:bg-night-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gilt';
  const inner = (
    <>
      <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-night text-gilt">
        <Icon size={17} aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[16px] leading-snug text-moon">{label}</span>
        <span className="block text-[13.5px] leading-snug text-mist">{note}</span>
      </span>
      <ArrowUpRight size={16} aria-hidden className="shrink-0 text-dim transition-colors group-hover:text-gilt" />
    </>
  );
  return external ? (
    <a href={href} className={cls} {...(href.startsWith('mailto:') ? {} : { target: '_blank', rel: 'noreferrer' })}>
      {inner}
      {!href.startsWith('mailto:') && <span className="sr-only"> (opens in a new tab)</span>}
    </a>
  ) : (
    <Link href={href} className={cls}>
      {inner}
    </Link>
  );
}

export default function LinksPage() {
  return (
    <main id="content" className="mx-auto w-full max-w-[34rem] flex-1 px-5 pb-16 pt-12 sm:pt-16">
      <header className="flex flex-col items-center text-center">
        <FamilyFace gen={7} life="alive" mood="happy" instincts={3} size={76} title="Grace, generation 7 of the family" />
        <h1 className="mt-4 font-display text-[40px] font-[420] leading-none tracking-[-0.02em]">{appName}</h1>
        <p className="mt-3 max-w-sm text-[16px] leading-relaxed text-silver">
          My agent dies every night. A court decides what its child inherits.
        </p>
        <p className="mt-2 text-[13.5px] text-dim">An entry in Fly.io Hacksgiving 2026</p>
      </header>

      {GROUPS.map((g) => {
        const items = g.items.filter((i) => i.href);
        if (!items.length) return null;
        const id = `links-${g.title.toLowerCase().replace(/\s+/g, '-')}`;
        return (
          <section key={g.title} aria-labelledby={id} className="mt-9">
            <h2 id={id} className="mb-3 px-1 text-[13.5px] font-medium text-mist">
              {g.title}
            </h2>
            <ul className="flex flex-col gap-2.5">
              {items.map((i) => (
                <li key={i.label}>
                  <Row {...i} />
                </li>
              ))}
            </ul>
          </section>
        );
      })}

      <p className="mt-10 text-center text-[13px] leading-relaxed text-dim">
        <Link href="/" className="text-mist underline decoration-gilt/50 underline-offset-[3px] hover:text-moon">
          probate home
        </Link>
        {' · '}PageSpeed: Accessibility, Best Practices and SEO 100
      </p>
    </main>
  );
}
