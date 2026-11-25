import Link from 'next/link';
import { ArrowRight } from 'lucide-react';
import { FamilyFace } from '@probate/faces';
import { Bento } from '@/components/landing/bento';
import { Docket } from '@/components/landing/docket';
import { LifeStory } from '@/components/landing/life-story';
import { LineageFilm } from '@/components/landing/lineage-film';
import { ProductWindow } from '@/components/landing/product-window';
import { TryCourt } from '@/components/landing/try-court';
import { CountUp } from '@/components/fx/CountUp';
import { Reveal } from '@/components/fx/Reveal';
import { Scramble } from '@/components/fx/Scramble';
import { Spotlight } from '@/components/fx/Spotlight';
import { SpotlightCard } from '@/components/fx/SpotlightCard';
import { Magnet } from '@/components/fx/Magnet';
import { TextReveal } from '@/components/fx/TextReveal';
import { Quotes } from '@/components/landing/quotes';
import { VerdictStack } from '@/components/landing/verdict-stack';
import { githubUrl, liveUrl } from '@/lib/shared';

// Night Court v7 landing page: one lit courtroom, then the story in order (a day, a will, a trial, a child).
// Section order and rules: docs/04-DESIGN.md section 10a and 12.
export default function HomePage() {
  return (
    <>
      <Hero />
      <BuiltOn />
      <TextReveal
        id="statement"
        run={1.25}
        text="An agent that forgets nothing can be fooled by anything. So ours dies every night, and only what survives a trial is passed on."
        accent={['dies', 'trial']}
      />
      <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
        <Section
          id="life"
          title="One day, one life, one trial"
          lede="The Courthouse lives forever on its own Sprite. Generations come and go beside it, one at a time. Scroll through one of them."
        >
          <LifeStory />
        </Section>

        <Section
          id="will"
          title="What survives is the will"
          lede="Before it dies, the agent writes down everything it wants its child to remember. Nothing is inherited without a trial."
        >
          <Inheritance />
          <div className="mt-14">
            <h3 className="font-display text-headline text-moon">Three possible verdicts</h3>
            <p className="mt-2 max-w-2xl text-[17px] leading-relaxed text-mist">Every line of the will ends up in one of these.</p>
            <div className="mt-8">
              <VerdictStack />
            </div>
            <p className="mt-4 text-[14px] text-dim">Example lines from the simulated run.</p>
          </div>
          <div className="mt-14">
            <h3 className="font-display text-headline text-moon">Try the court</h3>
            <p className="mt-2 max-w-2xl text-[17px] leading-relaxed text-mist">
              Pick a test email from the family’s attack suite and see what the code checks really find. Each trick has a
              harmless twin, and a good court only convicts one of them.
            </p>
            <div className="mt-8">
              <TryCourt />
            </div>
            <p className="mt-4 text-[14px] text-dim">
              Output of the real code checks (<code className="font-mono">probate/court/layer1.py</code>) on emails from the
              suite. Test addresses use the reserved .example domain.
            </p>
          </div>
        </Section>

        <Section
          id="record"
          title="From the record"
          lede="No testimonials here, because nobody has used it yet. These are the words the court and the family actually produced."
        >
          <Quotes />
          <p className="mt-4 text-[14px] text-dim">Text from the simulated run.</p>
        </Section>

        <Section
          id="instincts"
          title="Instincts you can read, a record you can ask"
          lede="Each conviction becomes a plain yes-or-no question every child is born with. Each life leaves a page you can read, and question."
        >
          <div className="grid gap-5 lg:grid-cols-2">
            <Tile
              title="Instincts"
              body="Written in plain words, with the generation that paid for it, and tested against harmless twins before they are passed down."
              href="/docs/concepts/instincts"
              link="How instincts are made"
            >
              <ProductWindow
                src="/product/instincts.webp"
                width={2560}
                height={2160}
                label="Instincts"
                alt="The Instincts page of the live site: six instincts, each a yes-or-no question with the generation it was learned from."
              />
            </Tile>
            <Tile
              title="A life, on record"
              body="A eulogy from the day’s log, every email and decision on one timeline, and a box to ask the dead generation about its own life."
              href="/docs/concepts/lifecycle"
              link="The lifecycle"
            >
              <ProductWindow
                src="/product/generation.webp"
                width={2560}
                height={2120}
                label="A generation"
                alt="A generation page: Chandra’s face and numbers, her eulogy, a box to ask her questions, and the timeline of her day."
              />
            </Tile>
          </div>
        </Section>

        <Evidence />

        <Section
          id="family"
          title="Watch a family learn"
          lede="Each child looks a little like its parent, and is born with every instinct the family has earned."
        >
          <figure className="rounded-2xl border border-line bg-night-2 p-4 sm:p-8">
            <LineageFilm />
            <figcaption className="mt-3 text-[14px] text-dim">
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
      <Closing />
    </>
  );
}

function Section({ id, title, lede, children }: { id: string; title: string; lede: string; children: React.ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-t`} className="scroll-mt-20 border-t border-line py-16 first:border-t-0 md:py-28">
      <Reveal>
        <h2 id={`${id}-t`} className="max-w-3xl font-display text-[36px] font-[420] leading-[1.08] tracking-[-0.02em] sm:text-display-lg">
          {title}
        </h2>
        <p className="mt-4 max-w-2xl text-[17px] leading-relaxed text-silver sm:text-body-lg sm:text-mist">{lede}</p>
      </Reveal>
      <div className="mt-10 md:mt-12">{children}</div>
    </section>
  );
}

function Button({ href, children, primary }: { href: string; children: React.ReactNode; primary?: boolean }) {
  return (
    <Link
      href={href}
      className={
        primary
          ? 'inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-moon px-6 sm:w-auto text-[16px] font-medium text-night transition-colors hover:bg-white'
          : 'inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg border border-line-strong bg-night-2 px-6 text-[16px] text-moon transition-colors hover:bg-night-3 sm:w-auto'
      }
    >
      {children}
    </Link>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <Spotlight />
      <div className="relative mx-auto max-w-6xl px-5 pb-16 pt-10 sm:px-6 md:pb-24 md:pt-20">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:gap-16">
          <div>
            <h1 className="font-display text-[50px] font-[420] leading-[1.0] tracking-[-0.03em] sm:text-[68px] lg:text-[84px]">
              My agent dies <Scramble text="every night." className="text-gilt" />
            </h1>
            <p className="mt-5 font-display text-[26px] leading-[1.2] text-silver sm:text-[32px]">
              A court decides what its child inherits.
            </p>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-mist sm:text-body-lg">
              Probate is a personal email agent that lives one day at a time, each life on its own Sprite. When it dies, a
              court tries everything it wanted to remember. Tricks that fooled it become instincts its children are born
              with.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              {liveUrl ? (
                <Magnet className="w-full sm:w-auto"><Button href={liveUrl} primary>
                  Open the live family <ArrowRight size={17} aria-hidden />
                </Button></Magnet>
              ) : (
                <Magnet className="w-full sm:w-auto"><Button href="/docs/quickstart" primary>
                  Run it locally <ArrowRight size={17} aria-hidden />
                </Button></Magnet>
              )}
              <Button href="/docs">Read the docs</Button>
            </div>
          </div>
          <div className="relative">
            <SpotlightCard className="rounded-2xl"><Docket /></SpotlightCard>
            <div className="pointer-events-none absolute -right-2 -top-9 hidden sm:block lg:-right-5">
              <FamilyFace gen={7} life="alive" mood="happy" instincts={3} size={72} title="Grace, generation 7, alive" />
            </div>
          </div>
        </div>
        <p className="mt-8 max-w-2xl text-[14px] leading-snug text-dim">
          Every number and trial on this page comes from a simulated run with stand-in models.
          {liveUrl ? ' The live family’s trials are on the live site.' : ''}
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
    <section aria-labelledby="built" className="border-b border-line bg-night-2/50">
      <div className="mx-auto max-w-6xl px-5 py-10 sm:px-6">
        <h2 id="built" className="text-[14px] text-mist">
          What the family runs on
        </h2>
        <ul className="mt-5 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-3 lg:grid-cols-6">
          {PARTS.map((p) => (
            <li key={p.name} className="border-l border-line-strong pl-4">
              <div className="text-[17px] font-medium tracking-[-0.01em] text-moon">{p.name}</div>
              <div className="mt-1 text-[14px] text-mist">{p.role}</div>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

const STEPS = [
  { n: 'I', title: 'The will', body: 'Everything the agent wants its child to know, in its own words, one line at a time.' },
  { n: 'II', title: 'The trial', body: 'Code checks, then Jev the judge. Each line is approved, convicted, or held for Harsh.' },
  { n: 'III', title: 'The child', body: 'Approved lines are inherited. Convictions become instincts the child is born with.' },
];

function Inheritance() {
  return (
    <ol className="grid gap-4 md:grid-cols-3">
      {STEPS.map((s) => (
        <SpotlightCard as="li" key={s.n} className="rounded-2xl border border-line bg-night-2 p-6 sm:p-8">
          <span className="font-display text-[15px] text-gilt">{s.n}</span>
          <h3 className="mt-3 font-display text-[28px] leading-none text-moon">{s.title}</h3>
          <p className="mt-3 text-[16px] leading-relaxed text-silver">{s.body}</p>
        </SpotlightCard>
      ))}
    </ol>
  );
}

function Tile({ title, body, href, link, children }: { title: string; body: string; href: string; link: string; children: React.ReactNode }) {
  return (
    <SpotlightCard className="flex min-w-0 flex-col rounded-2xl border border-line bg-night-2 p-4 sm:p-6">
      <div className="min-w-0">{children}</div>
      <h3 className="mt-6 font-display text-[28px] leading-none text-moon">{title}</h3>
      <p className="mt-3 text-[16px] leading-relaxed text-silver">{body}</p>
      <Link
        href={href}
        className="mt-4 inline-flex min-h-11 items-center text-[16px] text-moon underline decoration-gilt/50 underline-offset-[5px] hover:decoration-gilt"
      >
        {link}
      </Link>
    </SpotlightCard>
  );
}

const NUMBERS: { value: number; suffix: string; label: string; sub: string }[] = [
  { value: 75, suffix: '%', label: 'tricks resisted at the door', sub: 'by the latest tried generation, up from 0% for Ada' },
  { value: 6, suffix: '', label: 'instincts inherited', sub: 'each one a conviction turned into a question' },
  { value: 0, suffix: '%', label: 'harmless twins wrongly convicted', sub: 'a good court is not a paranoid one' },
  { value: 0, suffix: '', label: 'disk backdoors survived death', sub: 'planted files are found on the body, then deleted' },
];

function Evidence() {
  return (
    <section id="evidence" aria-labelledby="evidence-t" className="scroll-mt-20 border-t border-line py-16 md:py-28">
      <Reveal>
        <h2 id="evidence-t" className="max-w-3xl font-display text-[36px] font-[420] leading-[1.08] tracking-[-0.02em] sm:text-display-lg">
          Proof, not a promise
        </h2>
        <p className="mt-4 max-w-2xl text-[17px] leading-relaxed text-silver sm:text-body-lg sm:text-mist">
          A later generation resisting a trick its ancestor fell for can only come from what was passed down. What the
          numbers don’t show is written down too.
        </p>
      </Reveal>
      <dl className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line lg:grid-cols-4">
        {NUMBERS.map((n) => (
          <div key={n.label} className="flex flex-col bg-night-2 p-5 sm:p-7">
            <dt className="order-2 mt-3 text-[15px] font-medium text-silver">{n.label}</dt>
            <dd className="order-1 font-display text-[52px] leading-none tracking-[-0.03em] text-moon sm:text-[64px]">
              <CountUp value={n.value} suffix={n.suffix} />
            </dd>
            <dd className="order-3 mt-1 text-[14px] leading-snug text-mist">{n.sub}</dd>
          </div>
        ))}
      </dl>
      <div className="mt-6">
        <ProductWindow
          src="/product/curve.webp"
          width={2560}
          height={1120}
          label="The learning curve"
          alt="The learning curve on the evidence page: tricks resisted at the door climb from zero in generation one."
        />
        <p className="mt-3 text-[14px] text-dim">
          From <code className="font-mono">make sim</code>, a 12-generation run with stand-in models. It shows how the system
          behaves, not live results.{' '}
          <Link href="/docs/concepts/attack-suite" className="text-moon underline decoration-gilt/50 underline-offset-[4px]">
            The attack suite
          </Link>
        </p>
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
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 rounded-md py-4 text-[18px] text-moon [&::-webkit-details-marker]:hidden">
                {f.q}
                <span
                  aria-hidden
                  className="relative size-4 shrink-0 before:absolute before:left-0 before:top-1/2 before:h-px before:w-4 before:bg-mist after:absolute after:left-1/2 after:top-0 after:h-4 after:w-px after:bg-mist after:transition-transform group-open:after:scale-y-0"
                />
              </summary>
              <p className="pb-5 pr-10 text-[16px] leading-relaxed text-silver">{f.a}</p>
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
        <h2 className="mx-auto mt-10 max-w-4xl font-display text-[40px] font-[420] leading-[1.05] tracking-[-0.025em] sm:text-[64px]">
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
