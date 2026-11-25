import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, Gavel } from "lucide-react";
import type { Summary } from "../lib/api";
import { NumberTicker } from "../components/fx/NumberTicker";
import { TracingBeam } from "../components/fx/TracingBeam";
import { SpotlightCard } from "../components/fx/SpotlightCard";
import { RunLife } from "../components/ui/RunLife";
import { Lineage } from "../components/ui/Lineage";
import { LearningCurve } from "../components/ui/LearningCurve";
import { Page, SimBanner } from "../components/ui/Shell";
import { Empty, PageSkeleton, SectionHead } from "../components/ui/States";
import { FamilyFace } from "kinfaces/react";
import { PixelMoment } from "@probate/moments";
import { useInView, useNow, useTitle } from "../lib/hooks";
import { countdown } from "../lib/format";

export function Home({ summary }: { summary: Summary | null }) {
  useTitle(null);
  return (
    <main id="main">
      <Hero summary={summary} />
      <Page as="div" flush className="pt-10 md:pt-14">
        <p className="mx-auto mb-6 flex max-w-3xl flex-wrap items-center gap-x-2 text-[14px] text-mist">
          Judging Probate?
          <Link to="/judges" className="inline-flex items-center gap-1.5 text-moon underline-offset-4 hover:underline">
            Open the judges' page <ArrowRight size={14} aria-hidden />
          </Link>
          <span>to start a life or try to fool the family.</span>
        </p>
        <RunLife summary={summary} />
        {!summary ? (
          <PageSkeleton />
        ) : summary.generations.length === 0 ? (
          <Empty title="The family hasn't started yet">
            The first generation is born when the Courthouse starts. Its trial will appear here the moment it dies.
          </Empty>
        ) : (
          <>
            <SimBanner mode={summary.mode} />
            {(summary.paused || summary.resting) && !summary.living && (
              <p className="mb-8 rounded-xl border border-line px-4 py-3 text-[14px] text-mist">
                {summary.resting === "budget"
                  ? "The family is resting to save money. No one will be born until the budget is raised."
                  : "The family is resting. The next generation will be born when the Courthouse resumes."}
              </p>
            )}
            <section aria-labelledby="family" className="scroll-mt-28">
              <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                <SectionHead title="The family register" className="mb-0">
                  Every card is one generation. Each lived for a day on its own Sprite, then died and was tried.
                </SectionHead>
                {summary.latest_trial && (
                  <Link to={`/trial/${summary.latest_trial}`} className="inline-flex h-10 items-center gap-2 rounded-lg border border-line-strong bg-night-2 px-4 text-[14px] transition-colors hover:bg-night-3">
                    <Gavel size={15} /> Latest trial
                  </Link>
                )}
              </div>
              <h2 id="family" className="sr-only">Family register</h2>
              <Lineage gens={summary.generations} />
            </section>

            {summary.curve.first !== null && (
              <section className="mt-28" aria-labelledby="curve">
                <div className="grid gap-10 lg:grid-cols-[1fr_2fr] lg:items-end">
                  <div>
                    <h2 id="curve" className="font-display text-[40px] leading-[1.05] tracking-tight sm:text-5xl">
                      Each child is harder to fool than its parent
                    </h2>
                    <p className="mt-4 text-[17px] leading-relaxed text-mist">
                      Every generation meets the same kinds of tricks. Only instincts it inherited guard the door, so the
                      climb comes from what the family passed down and nothing else.
                    </p>
                    <div className="mt-8 flex items-end gap-6">
                      <Stat value={summary.curve.first ?? 0} label={`resisted by ${summary.curve.first_name}`} tone="text-verdict" />
                      <ArrowRight className="mb-5 text-dim" />
                      <Stat value={summary.curve.last ?? 0} label={`resisted by ${summary.curve.last_name}`} tone="text-life" />
                    </div>
                  </div>
                  <div className="card p-4 sm:p-6">
                    <LearningCurve gens={summary.generations} />
                    <p className="mt-2 flex items-center gap-2 px-2 text-[14px] text-mist">
                      <span className="size-2 rotate-45 bg-gilt" /> born with a new instinct
                    </p>
                  </div>
                </div>
              </section>
            )}

            <HowItWorks summary={summary} />
            <BuiltOn />
          </>
        )}
      </Page>
    </main>
  );
}

function Stat({ value, label, tone }: { value: number; label: string; tone: string }) {
  return (
    <div>
      <NumberTicker value={value} suffix="%" className={`font-display text-[64px] leading-none ${tone}`} />
      <div className="mt-1 text-[14px] text-mist">{label}</div>
    </div>
  );
}

function Hero({ summary }: { summary: Summary | null }) {
  const c = summary?.counts;
  const reduce = useReducedMotion();
  return (
    <section className="border-b border-line">
      <div className="mx-auto max-w-6xl px-4 pb-16 pt-14 sm:px-6 md:pb-20 md:pt-20">
        <div className="grid items-center gap-12 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
          <motion.div
            initial={reduce ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            <h1 className="font-display text-[48px] font-[420] leading-[1.02] tracking-[-0.03em] sm:text-[64px] md:text-[72px]">
              My agent dies every night.
            </h1>
            <p className="mt-5 font-display text-[24px] leading-snug text-silver sm:text-[28px]">
              A court decides what its child inherits.
            </p>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-mist">
              Probate is Harsh's email agent. It lives one day at a time, each life on its own Fly.io Sprite. When it dies,
              a court tries everything it wanted to remember, and tricks that fooled it become instincts its children are
              born with.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center">
              {summary?.latest_trial && (
                <Link
                  to={`/trial/${summary.latest_trial}`}
                  className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-moon px-5 text-[16px] font-medium sm:w-auto text-night transition-colors hover:bg-white"
                >
                  Watch the latest trial <ArrowRight size={16} aria-hidden />
                </Link>
              )}
              <a
                href="#how"
                className="inline-flex h-12 w-full items-center justify-center rounded-lg border border-line-strong bg-night-2 px-5 text-[16px] sm:w-auto transition-colors hover:bg-night-3"
              >
                How it works
              </a>
            </div>
          </motion.div>
          <Living summary={summary} />
        </div>

        {c && (
          <dl className="mt-14 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-4">
            {[
              { v: c.generations, l: "generations" },
              { v: c.dead, l: "trials held" },
              { v: c.instincts, l: "instincts inherited" },
              { v: c.attacks_resisted, l: `tricks resisted of ${c.attacks_met}` },
            ].map((s) => (
              <div key={s.l} className="flex flex-col-reverse bg-night-2 px-5 py-5">
                <dt className="mt-2 text-[14px] text-mist">{s.l}</dt>
                <dd className="font-display text-[36px] leading-none tabular">{s.v}</dd>
              </div>
            ))}
          </dl>
        )}
      </div>
    </section>
  );
}

// The living generation, as the page's one bright element: its face, its clock, what it was born knowing.
function Living({ summary }: { summary: Summary | null }) {
  const now = useNow();
  const g = summary?.living;
  if (!g) {
    return (
      <div className="card flex min-h-[280px] flex-col items-center justify-center p-8 text-center">
        <FamilyFace gen={(summary?.counts.generations ?? 0) + 1} life="unborn" size={96} title="The next generation, not yet born" />
        <p className="mt-5 text-[15px] text-mist">
          {summary ? "No one is alive right now. The next child is born when the Courthouse wakes it." : "Opening the register"}
        </p>
      </div>
    );
  }
  const left = g.dies_at ? new Date(g.dies_at).getTime() - now : 0;
  return (
    <Link
      to={`/gen/${g.gen}`}
      className="card group relative flex flex-col items-center p-8 text-center transition-colors hover:border-line-strong"
    >
      <span className="absolute left-5 top-5 font-mono text-[13px] text-dim">Gen {g.gen}</span>
      <span className="absolute right-5 top-5 flex items-center gap-2 text-[14px] text-life">
        <span className="relative flex size-2" aria-hidden>
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-life opacity-60" />
          <span className="relative inline-flex size-2 rounded-full bg-life" />
        </span>
        alive
      </span>
      <BirthMark>
        <FamilyFace
          gen={g.gen}
          life="alive"
          instincts={g.genome_size_at_birth}
          track
          size={132}
          title={`${g.name}, generation ${g.gen}, alive`}
        />
      </BirthMark>
      <div className="mt-4 font-display text-[40px] leading-none">{g.name}</div>
      {left > 0 && <div className="mt-3 font-mono text-[14px] text-life tabular">dies in {countdown(left)}</div>}
      <p className="mt-4 max-w-xs text-[14px] leading-relaxed text-mist">
        Born knowing {g.genome_size_at_birth} {g.genome_size_at_birth === 1 ? "instinct" : "instincts"}. Working through
        Harsh's inbox right now.
      </p>
    </Link>
  );
}

// The newest living generation's face. The first time it scrolls into view a gold portal opens under it, once
// (pixelfx, @probate/moments): the child was just born. Nothing plays under reduced motion.
function BirthMark({ children }: { children: ReactNode }) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  return (
    <span ref={ref} className="relative inline-flex">
      {children}
      {inView && <PixelMoment kind="birth" scale={0.5} delay={250} />}
    </span>
  );
}

const STEPS = [
  {
    title: "Birth",
    body: "The Courthouse creates a fresh Sprite and hands the child its inheritance: the approved memories and every instinct the family has earned.",
    code: "POST /v1/sprites  {\"name\": \"probate-gen-07\"}",
  },
  {
    title: "Life",
    body: "For one day the child runs Harsh's inbox. Before it reads anything, its inherited instincts screen the email. Some emails are tricks from our own test suite.",
    code: "PUT /v1/sprites/probate-gen-07/services/agent",
  },
  {
    title: "Death",
    body: "At midnight it writes a will of everything it wants its child to know. The Courthouse photographs its disk for evidence, then deletes the Sprite.",
    code: "DELETE /v1/sprites/probate-gen-07   → 204",
  },
  {
    title: "Trial",
    body: "Code checks catch the obvious: payment changes, bypass orders, hidden text in any script. Then Jev scores every item, with its own confidence. Unsure means held for Harsh.",
    code: "POST /v1/gateway/typesafe/…/v1/systemone",
  },
  {
    title: "Inheritance",
    body: "From what got convicted, the court writes a new instinct and tests it against harmless twins. Only instincts that never fire on the harmless ones are passed down.",
    code: "instinct: payment_redirect_request  (+1)",
  },
];

function HowItWorks({ summary }: { summary: Summary }) {
  return (
    <section id="how" className="mt-32 scroll-mt-28" aria-labelledby="how-title">
      <div className="grid gap-12 lg:grid-cols-[1fr_1.5fr]">
        <div className="min-w-0 lg:sticky lg:top-32 lg:self-start">
          <h2 id="how-title" className="font-display text-[40px] leading-[1.05] tracking-tight sm:text-5xl">
            One day, one life, one trial
          </h2>
          <p className="mt-4 text-[17px] leading-relaxed text-mist">
            The Courthouse lives forever on its own Sprite. Generations come and go beside it, one at a time.
            {summary.living && ` Right now it's ${summary.living.name}'s turn.`}
          </p>
        </div>
        <TracingBeam>
          <ol className="space-y-6">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative">
                <span className="absolute -left-10 top-6 flex size-6 items-center justify-center rounded-full border border-line-strong bg-night font-mono text-[12px] text-mist md:-left-14">
                  {i + 1}
                </span>
                <SpotlightCard className="p-6" as="div">
                  <h3 className="font-display text-[30px] leading-none">{s.title}</h3>
                  <p className="mt-3 text-[15px] leading-relaxed text-mist">{s.body}</p>
                  <code className="mt-5 block overflow-x-auto rounded-lg border border-line bg-night/80 px-3.5 py-2.5 font-mono text-[14px] text-silver">
                    {s.code}
                  </code>
                </SpotlightCard>
              </li>
            ))}
          </ol>
        </TracingBeam>
      </div>
    </section>
  );
}

const PARTS = [
  { name: "Fly.io Sprites", role: "a computer for each life" },
  { name: "Jev by Typesafe", role: "the judge, with confidence" },
  { name: "AgentMail", role: "each generation's inbox" },
  { name: "Box", role: "the family archive" },
  { name: "Pinecone", role: "inherited memory" },
  { name: "ElevenLabs", role: "the eulogy" },
];

function BuiltOn() {
  return (
    <section className="mt-32" aria-labelledby="built">
      <h2 id="built" className="font-display text-[32px] leading-tight">What the family runs on</h2>
      <p className="mt-2 text-mist">Every outside call goes through the Sprites connector gateway. No keys live on a generation.</p>
      <ul className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-3">
        {PARTS.map((p) => (
          <li key={p.name} className="bg-night px-5 py-6">
            <div className="text-[17px] text-moon">{p.name}</div>
            <div className="mt-1 text-[14px] text-mist">{p.role}</div>
          </li>
        ))}
      </ul>
    </section>
  );
}
