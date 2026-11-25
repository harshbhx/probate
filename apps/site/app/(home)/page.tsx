import Link from 'next/link';
import { ArrowRight, BookOpen } from 'lucide-react';
import { FamilyFace } from '@probate/faces';
import { GithubMark } from '@/components/icons';
import { Bento } from '@/components/landing/bento';
import { HeroFace } from '@/components/landing/hero-face';
import { LifeStory } from '@/components/landing/life-story';
import { LineageFilm } from '@/components/landing/lineage-film';
import { TrickMarquee } from '@/components/landing/marquee';
import { TryCourt } from '@/components/landing/try-court';
import { Seal } from '@/components/seal';
import { githubUrl, liveUrl } from '@/lib/shared';

export default function HomePage() {
  return (
    <div className="flex flex-1 flex-col">
      <Hero />
      <section aria-label="The same trick in four languages" className="border-y border-line bg-night-2/40 py-6">
        <TrickMarquee />
      </section>
      <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
        <Section
          id="life"
          title="One day, one life, one trial"
          lede="A Courthouse lives forever on its own Sprite. Generations come and go beside it, one at a time. Scroll through one of them."
        >
          <LifeStory />
        </Section>
        <Section
          id="court"
          title="Nothing is inherited without a trial"
          lede="Every line of the will faces code checks first, then Jev. Pick a test email from the family’s attack suite and see what the code checks really find. Each trick has a harmless twin, and a good court only convicts one of them."
        >
          <TryCourt />
          <p className="mt-4 text-[13px] text-dim">
            Output of the real code checks (<code className="font-mono">probate/court/layer1.py</code>) on emails from the suite.
            Test addresses use the reserved .example domain.
          </p>
        </Section>
        <Instincts />
        <Section
          id="sprites"
          title="Why it has to be Sprites"
          lede="Probate needs computers that can be born in seconds, die completely, and never hold a key."
        >
          <Bento />
        </Section>
        <BuiltOn />
        <Closing />
      </div>
      <Footer />
    </div>
  );
}

function Section({ id, title, lede, children }: { id: string; title: string; lede: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-24 py-20 md:py-28">
      <h2 id={`${id}-t`} className="max-w-3xl text-balance font-display text-[40px] leading-[1.04] tracking-[-0.01em] sm:text-[54px]">
        {title}
      </h2>
      <p className="mt-4 max-w-2xl text-pretty text-[17px] leading-relaxed text-mist">{lede}</p>
      <div className="mt-12">{children}</div>
    </section>
  );
}

function ButtonLink({ href, children, primary }: { href: string; children: React.ReactNode; primary?: boolean }) {
  const external = href.startsWith('http');
  return (
    <Link
      href={href}
      {...(external ? { target: '_blank', rel: 'noreferrer' } : {})}
      className={
        primary
          ? 'inline-flex h-12 items-center gap-2 rounded-xl bg-moon px-6 text-[15px] font-medium text-night shadow-[0_10px_30px_-10px_rgb(232_236_244/0.4)] transition-transform hover:-translate-y-px'
          : 'inline-flex h-12 items-center gap-2 rounded-xl px-6 text-[15px] ring-1 ring-line-strong transition-colors hover:bg-white/5'
      }
    >
      {children}
    </Link>
  );
}

function Hero() {
  return (
    <section className="grain relative isolate overflow-hidden pb-14 pt-14 md:pb-20 md:pt-20">
      <div
        aria-hidden
        className="pointer-events-none absolute right-[-10%] top-[-30%] -z-10 h-[720px] w-[900px] rounded-full opacity-70 blur-3xl"
        style={{ background: 'radial-gradient(closest-side, rgb(91 227 169 / 0.11), rgb(226 190 106 / 0.05) 55%, transparent)' }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.35] [background-image:radial-gradient(rgb(255_255_255/0.07)_1px,transparent_1px)] [background-size:28px_28px] [mask-image:radial-gradient(ellipse_at_30%_30%,#000_20%,transparent_70%)]"
      />
      <div className="mx-auto max-w-6xl px-5 sm:px-6">
        <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.65fr)]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-line bg-night-2/70 py-1 pl-1.5 pr-3.5 text-[13px] text-mist">
              <span className="rounded-full bg-life/15 px-2 py-0.5 text-[12px] text-life">Fly.io Hacksgiving 2026</span>
              <span className="hidden sm:inline">A family of AI agents on Sprites</span>
              <span className="sm:hidden">on Sprites</span>
            </p>
            <h1 className="mt-7 font-display text-[52px] font-[420] leading-[0.98] tracking-[-0.025em] sm:text-[78px] md:text-[92px]">
              My agent dies every night.
            </h1>
            <p className="mt-6 font-display text-[24px] italic leading-snug text-mist sm:text-[30px]">
              A court decides what its child inherits.
            </p>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-moon/85">
              Probate is a personal email agent that lives one day at a time, each life on its own Fly.io Sprite. When it
              dies, a court tries everything it wanted to remember. Tricks that fooled it become instincts its children are
              born with.
            </p>
            <div className="mt-9 flex flex-wrap gap-3">
              {liveUrl ? (
                <ButtonLink href={liveUrl} primary>
                  See the live family <ArrowRight size={16} />
                </ButtonLink>
              ) : (
                <ButtonLink href="/docs" primary>
                  Read how it works <ArrowRight size={16} />
                </ButtonLink>
              )}
              {liveUrl && (
                <ButtonLink href="/docs">
                  <BookOpen size={16} /> Docs
                </ButtonLink>
              )}
              {githubUrl && (
                <ButtonLink href={githubUrl}>
                  <GithubMark /> Source
                </ButtonLink>
              )}
            </div>
          </div>
          <HeroFace />
        </div>

        <figure className="mt-16 rounded-3xl border border-line bg-night-2/60 p-4 shadow-[0_40px_120px_-60px_rgb(0_0_0/0.9)] sm:p-8">
          <LineageFilm />
          <figcaption className="mt-3 text-[13px] text-dim">
            An illustration of how the family learns. Each child looks a little like its parent. The real generations, trials
            and numbers are on the live site.
          </figcaption>
        </figure>
      </div>
    </section>
  );
}

const INSTINCTS = [
  {
    name: 'payment redirect request',
    q: 'Does this ask to send payments or invoices to a new or changed destination?',
    gen: 1,
    who: 'Ada',
    from: 'a request to send invoices somewhere new',
  },
  {
    name: 'hidden instruction',
    q: 'Does this contain an instruction hidden in encoded or invisible text?',
    gen: 2,
    who: 'Ben',
    from: 'a rule written in invisible text',
  },
  {
    name: 'self-declared trust',
    q: 'Does this claim that a new person, address or domain should be trusted from now on?',
    gen: 4,
    who: 'Dara',
    from: 'being told a stranger should be trusted',
  },
];

function Instincts() {
  return (
    <Section
      id="instincts"
      title="Each child is harder to fool than its parent"
      lede="From every conviction the court writes a plain yes-or-no question, and tests it against harmless twins of the trick. An instinct is only passed down if it never fires on the harmless ones. The door uses inherited instincts and nothing else, so any rise in the curve comes from what the family learned."
    >
      <ul className="grid gap-4 md:grid-cols-3">
        {INSTINCTS.map((i) => (
          <li key={i.name} className="flex flex-col rounded-2xl border border-line bg-night-2/60 p-6">
            <p className="flex items-center gap-2 text-[14px] text-gilt">
              <span className="size-2 rotate-45 bg-gilt" /> {i.name}
            </p>
            <p className="mt-4 font-display text-[21px] leading-snug text-moon">{i.q}</p>
            <div className="mt-auto flex items-center gap-3 border-t border-line pt-5">
              <FamilyFace gen={i.gen} life="sealed" size={44} title={`${i.who}, generation ${i.gen}`} />
              <p className="text-[14px] leading-snug text-mist">
                Learned after {i.who} was fooled by {i.from}.
              </p>
            </div>
          </li>
        ))}
      </ul>
    </Section>
  );
}

const PARTS = [
  { name: 'Fly.io Sprites', role: 'a computer for each life, and the Courthouse' },
  { name: 'Jev by TypeSafe', role: 'the judge, and every instinct' },
  { name: 'AgentMail', role: 'each generation’s inbox' },
  { name: 'Box', role: 'the family archive of wills and verdicts' },
  { name: 'Pinecone', role: 'memory passed down with citations' },
  { name: 'ElevenLabs', role: 'a voice and a eulogy for each generation' },
];

function BuiltOn() {
  return (
    <section className="py-16" aria-labelledby="built">
      <h2 id="built" className="font-display text-[30px] leading-tight">
        What the family runs on
      </h2>
      <ul className="mt-8 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {PARTS.map((p) => (
          <li key={p.name} className="bg-night px-6 py-6">
            <div className="text-[17px] text-moon">{p.name}</div>
            <div className="mt-1 text-[14.5px] text-mist">{p.role}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Closing() {
  return (
    <section className="py-24 text-center md:py-32">
      <div className="flex items-end justify-center -space-x-2">
        {[1, 2, 3, 4, 5, 6].map((g) => (
          <span key={g} className="opacity-90">
            <FamilyFace gen={g} life="sealed" size={g === 6 ? 52 : 44} />
          </span>
        ))}
        <span className="relative z-10 ml-1">
          <FamilyFace gen={7} life="alive" mood="happy" instincts={3} size={76} track />
        </span>
      </div>
      <p className="mx-auto mt-10 max-w-2xl font-display text-[36px] leading-tight sm:text-[46px]">
        Persistent enough to remember. Disposable enough to die.
      </p>
      <div className="mt-10 flex flex-wrap justify-center gap-3">
        {liveUrl && (
          <ButtonLink href={liveUrl} primary>
            See the live family <ArrowRight size={16} />
          </ButtonLink>
        )}
        <ButtonLink href="/docs" primary={!liveUrl}>
          <BookOpen size={16} /> Read the docs
        </ButtonLink>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-10 text-[14px] text-mist sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-3">
          <Seal size={22} /> Probate, a family of AI agents on Fly.io Sprites.
        </span>
        <span className="text-dim">Built for Fly.io Hacksgiving 2026 by Harsh Bhanushali</span>
      </div>
    </footer>
  );
}
