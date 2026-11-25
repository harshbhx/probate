import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { ArrowRight, Gavel } from "lucide-react";
import type { Summary } from "../lib/api";
import { BlurText } from "../components/fx/BlurText";
import { NumberTicker } from "../components/fx/NumberTicker";
import { TracingBeam } from "../components/fx/TracingBeam";
import { SpotlightCard } from "../components/fx/SpotlightCard";
import { LivePill } from "../components/ui/LivePill";
import { Lineage } from "../components/ui/Lineage";
import { LearningCurve } from "../components/ui/LearningCurve";
import { Page, SimBanner } from "../components/ui/Shell";
import { Empty, PageSkeleton, SectionHead } from "../components/ui/States";
import { FamilyFace } from "@probate/faces";
import { useTitle } from "../lib/hooks";

export function Home({ summary }: { summary: Summary | null }) {
  useTitle(null);
  return (
    <>
      <Hero summary={summary} />
      <Page flush className="pt-10 md:pt-14">
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
                  <Link to={`/trial/${summary.latest_trial}`} className="inline-flex h-10 items-center gap-2 rounded-xl px-4 text-[14px] ring-1 ring-line-strong transition-colors hover:bg-white/5">
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
                    <p className="mt-2 flex items-center gap-2 px-2 text-[13px] text-mist">
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
    </>
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
  return (
    <section className="relative isolate overflow-hidden border-b border-line pb-20 pt-16 md:pb-24 md:pt-28">
      <div className="relative mx-auto max-w-5xl px-5 text-center sm:px-6">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="flex justify-center">
          {summary?.living ? (
            <LivePill gen={summary.living} />
          ) : (
            <span className="inline-flex h-9 items-center rounded-full border border-line bg-night-2 px-4 text-[13px] text-mist">
              A family of AI agents on Fly.io Sprites
            </span>
          )}
        </motion.div>
        {summary?.living && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2, type: "spring", stiffness: 200, damping: 18 }}
            className="mt-8 flex justify-center"
          >
            <FamilyFace
              gen={summary.living.gen}
              life="alive"
              instincts={summary.living.genome_size_at_birth}
              track
              size={112}
              title={`${summary.living.name}, generation ${summary.living.gen}, alive`}
            />
          </motion.div>
        )}
        <h1 className="mt-8 font-display text-[54px] leading-[0.98] tracking-[-0.02em] sm:text-[84px] md:text-[104px]">
          <BlurText text="My agent dies" className="block" />
          <BlurText text="every night." className="block" delay={0.25} />
        </h1>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.9, duration: 0.8 }}
          className="mx-auto mt-8 max-w-2xl font-display text-[24px] italic leading-snug text-mist sm:text-[30px]"
        >
          A court decides what its child inherits.
        </motion.p>
        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.15, duration: 0.8 }}
          className="mx-auto mt-6 max-w-xl text-[16px] leading-relaxed text-mist/90"
        >
          Probate is a personal email agent that lives one day at a time. When it dies, a court tries everything it
          wanted to remember. Lessons pass down. Tricks get convicted. The family gets wiser.
        </motion.p>
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.3 }}
          className="mt-10 flex flex-wrap items-center justify-center gap-3"
        >
          {summary?.latest_trial && (
            <Link
              to={`/trial/${summary.latest_trial}`}
              className="inline-flex h-11 items-center gap-2 rounded-lg bg-moon px-5 text-[15px] font-medium text-night transition-colors hover:bg-white"
            >
              Watch the latest trial <ArrowRight size={16} />
            </Link>
          )}
          <a href="#how" className="inline-flex h-11 items-center rounded-lg border border-line-strong bg-night-2 px-5 text-[15px] transition-colors hover:bg-night-3">
            How it works
          </a>
        </motion.div>

        {c && (
          <motion.dl
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.6 }}
            className="mx-auto mt-16 grid max-w-3xl grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-4"
          >
            {[
              { v: c.generations, l: "generations" },
              { v: c.dead, l: "trials held" },
              { v: c.instincts, l: "instincts inherited" },
              { v: c.attacks_resisted, l: `tricks resisted of ${c.attacks_met}` },
            ].map((s) => (
              <div key={s.l} className="bg-night-2 px-4 py-5 text-left">
                <dd>
                  <NumberTicker value={s.v} className="font-display text-[40px] leading-none" />
                </dd>
                <dt className="mt-1.5 text-[13px] text-mist">{s.l}</dt>
              </div>
            ))}
          </motion.dl>
        )}
      </div>
    </section>
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
                <span className="absolute -left-10 top-6 flex size-6 items-center justify-center rounded-full border border-line-strong bg-night font-mono text-[11px] text-mist md:-left-14">
                  {i + 1}
                </span>
                <SpotlightCard className="p-6" as="div">
                  <h3 className="font-display text-[30px] leading-none">{s.title}</h3>
                  <p className="mt-3 text-[15.5px] leading-relaxed text-mist">{s.body}</p>
                  <code className="mt-5 block overflow-x-auto rounded-lg border border-line bg-night/80 px-3.5 py-2.5 font-mono text-[12.5px] text-moon/85">
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
      <ul className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line md:grid-cols-3">
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
