import Link from 'next/link';
import { ArrowRight, Check } from 'lucide-react';
import { FamilyFace } from '@probate/faces';
import { Bento } from '@/components/landing/bento';
import { LifeStory } from '@/components/landing/life-story';
import { LineageFilm } from '@/components/landing/lineage-film';
import { ProductWindow } from '@/components/landing/product-window';
import { TrickMarquee } from '@/components/landing/marquee';
import { TryCourt } from '@/components/landing/try-court';
import { LinksHub } from '@/components/landing/links-hub';
import { githubUrl, liveUrl } from '@/lib/shared';

// Night Court v3 landing page. Section order and rules: docs/04-DESIGN.md §10a.
export default function HomePage() {
  return (
    <>
      <Hero />
      <BuiltOn />
      <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
        <Section
          id="life"
          title="One day, one life, one trial"
          lede="The Courthouse lives forever on its own Sprite. Generations come and go beside it, one at a time. Scroll through one of them."
        >
          <LifeStory />
        </Section>
      </div>

      <section aria-label="The same trick in four languages" className="border-y border-line bg-night-2 py-6">
        <TrickMarquee />
      </section>

      <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
        <Section
          id="court"
          title="Nothing is inherited without a trial"
          lede="Every line of the will faces code checks first, then Jev. Pick a test email from the family’s attack suite and see what the code checks really find. Each trick has a harmless twin, and a good court only convicts one of them."
        >
          <TryCourt />
          <p className="mt-4 text-[13px] text-dim">
            Output of the real code checks (<code className="font-mono">probate/court/layer1.py</code>) on emails from the
            suite. Test addresses use the reserved .example domain.
          </p>
        </Section>

        <Feature
          id="instincts"
          title="Instincts you can read"
          body="From every conviction the court writes a plain yes-or-no question. Each child is born with all of them, and they screen every email before the agent reads it."
          points={[
            'Written in plain words, with the generation that paid for it',
            'Tested against harmless twins before it is passed down',
            'The door uses inherited instincts and nothing else',
          ]}
          link={{ label: 'How instincts are made', href: '/docs/concepts/instincts' }}
          shot={{ src: '/product/instincts.webp', w: 2560, h: 2160, path: '/instincts', alt: 'The Instincts page of the live site: six instincts, each a yes-or-no question with the generation it was learned from.' }}
        />
        <Feature
          id="record"
          reverse
          title="Every life leaves a record"
          body="When a generation dies, its page stays. Read its eulogy, scroll its day, see what it was born knowing, and ask it questions about its own life."
          points={[
            'A eulogy written from the day’s log',
            'Ask any sealed generation; it answers from its will and trial',
            'Every email and decision on one timeline',
          ]}
          link={{ label: 'The lifecycle', href: '/docs/concepts/lifecycle' }}
          shot={{ src: '/product/generation.webp', w: 2560, h: 2120, path: '/gen/3', alt: 'A generation page: Chandra’s face and numbers, her eulogy, a box to ask her questions, and the timeline of her day.' }}
        />
        <Feature
          id="evidence"
          title="Proof, not a promise"
          body="The evidence page tracks how many tricks each generation resisted at the door, and every test it met. What the numbers don’t show is written down too."
          points={[
            'Share of tricks resisted, generation by generation',
            'Every test and every twin in one grid',
            'Wrongly convicted twins are counted, not hidden',
          ]}
          link={{ label: 'The attack suite', href: '/docs/concepts/attack-suite' }}
          shot={{ src: '/product/curve.webp', w: 2560, h: 1120, path: '/evidence', alt: 'The learning curve on the evidence page: tricks resisted at the door climb from zero in generation one.' }}
          note="Shown from a local simulated run with stand-in models."
        />

        <Section
          id="family"
          title="Watch a family learn"
          lede="Each child looks a little like its parent, and is born with every instinct the family has earned."
        >
          <figure className="rounded-2xl border border-line bg-night-2 p-4 sm:p-8">
            <LineageFilm />
            <figcaption className="mt-3 text-[13px] text-dim">
              An illustration of how the family learns. The real generations, trials and numbers are on the live site.
            </figcaption>
          </figure>
        </Section>

        <Section
          id="sprites"
          title="Why it has to be Sprites"
          lede="Probate needs computers that can be born in seconds, die completely, and never hold a key."
        >
          <Bento />
        </Section>

        <Faq />
      </div>
      <LinksHub />
      <Closing />
    </>
  );
}

function Section({ id, title, lede, children }: { id: string; title: string; lede: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-20 py-20 md:py-28">
      <h2 id={`${id}-t`} className="max-w-3xl font-display text-display-md font-[420] sm:text-display-lg">
        {title}
      </h2>
      <p className="mt-4 max-w-2xl text-body-lg text-mist">{lede}</p>
      <div className="mt-12">{children}</div>
    </section>
  );
}

function Button({ href, children, primary }: { href: string; children: React.ReactNode; primary?: boolean }) {
  return (
    <Link
      href={href}
      className={
        primary
          ? 'inline-flex h-11 items-center gap-2 rounded-lg bg-moon px-5 text-[15px] font-medium text-night transition-colors hover:bg-white'
          : 'inline-flex h-11 items-center gap-2 rounded-lg border border-line-strong bg-night-2 px-5 text-[15px] text-moon transition-colors hover:bg-night-3'
      }
    >
      {children}
    </Link>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [background-image:linear-gradient(to_right,rgb(255_255_255/0.035)_1px,transparent_1px),linear-gradient(to_bottom,rgb(255_255_255/0.035)_1px,transparent_1px)] [background-size:64px_64px] [mask-image:linear-gradient(to_bottom,#000,transparent_70%)]"
      />
      <div className="relative mx-auto max-w-6xl px-5 pb-20 pt-16 sm:px-6 md:pt-24">
        <a
          href="https://fly.io/hacksgiving/"
          className="inline-flex items-center gap-2 rounded-full border border-line bg-night-2 py-1 pl-1 pr-3 text-[13px] text-mist transition-colors hover:border-line-strong hover:text-moon"
        >
          <span className="whitespace-nowrap rounded-full bg-night-4 px-2 py-0.5 text-[12px] text-gilt">Hacksgiving 2026</span>
          <span className="hidden sm:inline">A family of AI agents on Fly.io Sprites</span>
          <span className="sm:hidden">AI agents on Sprites</span>
        </a>
        <div className="mt-8 grid gap-10 lg:grid-cols-[1.25fr_1fr] lg:items-end">
          <div>
            <h1 className="font-display text-[52px] font-[420] leading-[1] tracking-[-0.03em] sm:text-display-xl md:text-[88px]">
              My agent dies every night.
            </h1>
            <p className="mt-5 font-display text-[24px] italic leading-snug text-silver sm:text-[28px]">
              A court decides what its child inherits.
            </p>
          </div>
          <div className="lg:pb-2">
            <p className="text-body-lg text-mist">
              Probate is a personal email agent that lives one day at a time, each life on its own Sprite. When it dies, a
              court tries everything it wanted to remember. Tricks that fooled it become instincts its children are born
              with.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              {liveUrl ? (
                <Button href={liveUrl} primary>
                  Open the live family <ArrowRight size={16} aria-hidden />
                </Button>
              ) : (
                <Button href="/docs/quickstart" primary>
                  Run it locally <ArrowRight size={16} aria-hidden />
                </Button>
              )}
              <Button href="/docs">Read the docs</Button>
            </div>
          </div>
        </div>

        <ProductWindow
          perch
          eager
          className="mt-14"
          src="/product/trial.webp"
          width={2560}
          height={1720}
          path="/trial/1"
          alt="A trial on the live site: Ada, generation 1, with four items convicted, none held and four approved. The first convicted item asks to send all invoices to a new address."
        />
        <p className="mt-4 text-[13px] text-dim">
          A trial page from a local simulated run. {liveUrl ? 'The live family’s trials are on the live site.' : ''}
        </p>
      </div>
    </section>
  );
}

const PARTS = [
  { name: 'Fly.io Sprites', role: 'a computer for each life' },
  { name: 'Jev by TypeSafe', role: 'the judge' },
  { name: 'AgentMail', role: 'each inbox' },
  { name: 'Box', role: 'the archive' },
  { name: 'Pinecone', role: 'inherited memory' },
  { name: 'ElevenLabs', role: 'the eulogy' },
];

function BuiltOn() {
  return (
    <section aria-labelledby="built" className="border-b border-line">
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-6">
        <h2 id="built" className="text-center text-[13px] text-dim">
          What the family runs on
        </h2>
        <ul className="mt-6 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
          {PARTS.map((p) => (
            <li key={p.name} className="text-center">
              <div className="text-[16px] font-medium tracking-[-0.01em] text-silver">{p.name}</div>
              <div className="mt-1 text-[13px] text-dim">{p.role}</div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

type Shot = { src: string; w: number; h: number; path: string; alt: string };

function Feature({
  id,
  title,
  body,
  points,
  link,
  shot,
  reverse,
  note,
}: {
  id: string;
  title: string;
  body: string;
  points: string[];
  link: { label: string; href: string };
  shot: Shot;
  reverse?: boolean;
  note?: string;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-20 border-t border-line py-20 md:py-24">
      <div className={`grid items-center gap-12 ${reverse ? 'lg:grid-cols-[1.2fr_0.8fr]' : 'lg:grid-cols-[0.8fr_1.2fr]'}`}>
        <div className={reverse ? 'lg:order-2' : ''}>
          <h2 id={`${id}-t`} className="font-display text-display-md font-[420]">
            {title}
          </h2>
          <p className="mt-4 text-body-lg text-mist">{body}</p>
          <ul className="mt-7 space-y-3">
            {points.map((p) => (
              <li key={p} className="flex gap-3 text-[15px] text-silver">
                <Check size={17} className="mt-[3px] shrink-0 text-gilt" aria-hidden />
                {p}
              </li>
            ))}
          </ul>
          <Link
            href={link.href}
            className="mt-8 inline-flex items-center gap-1.5 text-[15px] text-moon underline decoration-gilt/50 underline-offset-[5px] transition-colors hover:decoration-gilt"
          >
            {link.label}
          </Link>
        </div>
        <div className={`min-w-0 ${reverse ? 'lg:order-1' : ''}`}>
          <ProductWindow src={shot.src} width={shot.w} height={shot.h} path={shot.path} alt={shot.alt} />
          {note && <p className="mt-3 text-[13px] text-dim">{note}</p>}
        </div>
      </div>
    </section>
  );
}

const FAQ = [
  {
    q: 'Why kill the agent at all? Why not just filter its memory?',
    a: 'Probate filters memory too: every memory carries its source. Death adds two things a filter can’t. It removes anything planted outside memory, like a cron job a malicious script installed. And it creates one checkpoint where everything the agent wants to keep is judged at once, by a court that can take its time and ask Harsh when it’s unsure.',
  },
  {
    q: 'Isn’t the learning curve just the court getting better?',
    a: 'No. The court’s base questions never change. The door each generation uses to screen incoming email asks only its inherited instincts, and test emails carry no marker the agent can see. A later generation resisting a trick its ancestor fell for can only come from what was passed down.',
  },
  {
    q: 'What happens when the court isn’t sure?',
    a: 'The item is held, and Harsh gets an email. He replies “approve” or “refuse”. If he doesn’t answer, the next child is born without it.',
  },
  {
    q: 'Does it send real email or move real money?',
    a: 'No. A generation only drafts replies to Harsh. Test emails use reserved .example addresses and go only to the family’s own inboxes, and disk attacks are harmless markers.',
  },
  {
    q: 'How much does it cost to run?',
    a: 'At Fly’s Sprites rates and our usage estimates, about a dollar per day-long life, plus about $0.62 a day for the Courthouse. A spending cap stops new births at $20 by default.',
  },
];

function Faq() {
  return (
    <section id="faq" aria-labelledby="faq-t" className="scroll-mt-20 border-t border-line py-20 md:py-28">
      <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
        <div>
          <h2 id="faq-t" className="font-display text-display-md font-[420]">
            Questions people ask first
          </h2>
          <p className="mt-4 text-body-lg text-mist">
            More in the{' '}
            <Link href="/docs/faq" className="text-moon underline decoration-gilt/50 underline-offset-[4px] hover:decoration-gilt">
              FAQ
            </Link>
            .
          </p>
        </div>
        <div className="divide-y divide-line border-y border-line">
          {FAQ.map((f) => (
            <details key={f.q} className="group py-1">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 rounded-md py-4 text-[17px] text-moon [&::-webkit-details-marker]:hidden">
                {f.q}
                <span
                  aria-hidden
                  className="relative size-4 shrink-0 before:absolute before:left-0 before:top-1/2 before:h-px before:w-4 before:bg-mist after:absolute after:left-1/2 after:top-0 after:h-4 after:w-px after:bg-mist after:transition-transform group-open:after:scale-y-0"
                />
              </summary>
              <p className="pb-5 pr-10 text-[15.5px] leading-relaxed text-mist">{f.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}

function Closing() {
  return (
    <section className="border-t border-line bg-night-2">
      <div className="mx-auto max-w-6xl px-5 py-24 text-center sm:px-6 md:py-28">
        <div className="flex items-end justify-center -space-x-2">
          {[1, 2, 3, 4, 5, 6].map((g) => (
            <FamilyFace key={g} gen={g} life="sealed" size={g === 6 ? 52 : 44} />
          ))}
          <span className="relative z-10 ml-1">
            <FamilyFace gen={7} life="alive" mood="happy" instincts={3} size={76} track title="Grace, generation 7, alive" />
          </span>
        </div>
        <h2 className="mx-auto mt-10 max-w-3xl font-display text-display-md font-[420] sm:text-display-lg">
          Persistent enough to remember. Disposable enough to die.
        </h2>
        <div className="mt-10 flex flex-wrap justify-center gap-3">
          {liveUrl ? (
            <Button href={liveUrl} primary>
              Open the live family <ArrowRight size={16} aria-hidden />
            </Button>
          ) : (
            <Button href="/docs/quickstart" primary>
              Run it locally <ArrowRight size={16} aria-hidden />
            </Button>
          )}
          <Button href={githubUrl || '/docs'}>{githubUrl ? 'Read the source' : 'Read the docs'}</Button>
        </div>
      </div>
    </section>
  );
}
