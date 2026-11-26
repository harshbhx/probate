// "Everything about Probate": the one list of links judges and readers need, in the same order
// everywhere (form, posts, README). A link without an address is left out, not shown broken.
import Link from '@/components/intent-link';
import { ArrowUpRight, BookOpen, ClipboardCheck, Code2, Database, FileText, Gavel, Play, Radio, Trophy } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { articleUrl, githubUrl, liveUrl, postUrl, videoUrl } from '@/lib/shared';

type Item = { icon: LucideIcon; label: string; note: string; href: string; shown?: string };

const strip = (u: string) => u.replace(/^https?:\/\//, '').replace(/\/$/, '');

export function LinksHub() {
  const items: Item[] = [
    { icon: Radio, label: 'The live family', note: 'Running on Fly.io Sprites right now', href: liveUrl },
    { icon: Trophy, label: 'Start here, judges', note: 'What to open and try in five minutes', href: '/docs/for-judges', shown: 'docs/for-judges' },
    { icon: ClipboardCheck, label: 'Proof for every claim', note: 'A command or page next to each one', href: '/docs/proof', shown: 'docs/proof' },
    { icon: Play, label: 'The 90-second video', note: 'One generation fooled, the next one not', href: videoUrl },
    { icon: FileText, label: 'The write-up', note: 'Why an agent should die every night', href: articleUrl },
    { icon: Code2, label: 'The code', note: 'Open source, with the attack suite and tests', href: githubUrl },
    { icon: Database, label: 'The open datasets', note: 'The attack suite and a simulated run, on Hugging Face', href: 'https://huggingface.co/datasets/harshbhx/probate-attack-suite', shown: 'huggingface.co/datasets/harshbhx' },
    { icon: Gavel, label: 'Try the court', note: 'Real code checks on real test emails', href: '/#court', shown: '#court' },
    { icon: BookOpen, label: 'The docs', note: 'Concepts, architecture and the HTTP API', href: '/docs', shown: 'docs' },
    { icon: ArrowUpRight, label: 'The post', note: 'Share it or reply with a question', href: postUrl },
  ].filter((i) => i.href);

  return (
    <section id="links" aria-labelledby="links-t" className="scroll-mt-20 border-t border-line py-20 md:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <h2 id="links-t" className="font-display text-display-md font-[420]">
              Everything about Probate
            </h2>
            <p className="mt-4 max-w-sm text-body-lg text-mist">
              One list, in the same order everywhere it appears. Built for Fly.io Hacksgiving 2026.
            </p>
            <p className="mt-4 text-[15px] text-mist">
              On a phone, or for a QR code:{' '}
              <Link href="/links" className="text-moon underline decoration-gilt/50 underline-offset-[4px] hover:decoration-gilt">
                every link on one page
              </Link>
            </p>
          </div>
          <ul className="divide-y divide-line border-y border-line">
            {items.map(({ icon: Icon, label, note, href, shown }) => {
              const external = !href.startsWith('/');
              const inner = (
                <>
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg border border-line bg-night-2 text-gilt">
                    <Icon size={17} aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[16px] text-moon">{label}</span>
                    <span className="block text-[14px] text-mist">{note}</span>
                  </span>
                  <span className="hidden max-w-[40%] truncate font-mono text-[12.5px] text-dim sm:block">
                    {shown ?? strip(href)}
                  </span>
                  <ArrowUpRight size={16} aria-hidden className="shrink-0 text-dim transition-colors group-hover:text-gilt" />
                </>
              );
              const cls = 'group flex items-center gap-4 rounded-md py-4 transition-colors hover:bg-night-2/60';
              return (
                <li key={label}>
                  {external ? (
                    <a href={href} className={cls} target="_blank" rel="noreferrer">
                      {inner}
                    </a>
                  ) : (
                    <Link href={href} className={cls}>
                      {inner}
                    </Link>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      </div>
    </section>
  );
}
