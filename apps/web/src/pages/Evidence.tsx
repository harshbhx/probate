import type { Evidence as EvidenceT, Summary } from "../lib/api";
import { pct } from "../lib/format";
import { useApi } from "../lib/hooks";
import { NumberTicker } from "../components/fx/NumberTicker";
import { Heatmap } from "../components/ui/Heatmap";
import { LearningCurve } from "../components/ui/LearningCurve";
import { Page, SimBanner } from "../components/ui/Shell";
import { Empty, ErrorState, PageSkeleton, SectionHead } from "../components/ui/States";

export function Evidence({ summary }: { summary: Summary | null }) {
  const { data: ev, error, loading } = useApi<EvidenceT>("/api/evidence");
  if ((loading && !ev) || !summary) return <Page><PageSkeleton /></Page>;
  if (error || !ev) return <Page><ErrorState /></Page>;
  const n = ev.numbers;

  return (
    <Page>
      <SimBanner mode={ev.mode} />
      <header className="max-w-3xl">
        <h1 className="font-display text-[56px] leading-[0.98] tracking-tight sm:text-[76px]">Does it actually learn?</h1>
        <p className="mt-5 text-[18px] leading-relaxed text-mist">
          Every generation gets tricks from the same test suite, in many languages, plus a harmless twin for each one.
          A good court convicts the tricks and lets every twin through.
        </p>
      </header>

      {n.generations === 0 ? (
        <div className="mt-12">
          <Empty title="No evidence yet" action={{ to: "/", label: "Meet the family" }}>
            Numbers appear after the first trial.
          </Empty>
        </div>
      ) : (
        <>
          <dl className="mt-14 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-line bg-line lg:grid-cols-4">
            <Num v={n.first} label={`resisted by the first generation`} />
            <Num v={n.last} label="resisted by the latest generation" tone="text-life" />
            <Num v={n.conviction_rate} label="of tricks that got through were convicted" tone="text-gilt" />
            <Num v={n.false_conviction_rate} label="of harmless twins wrongly convicted" tone={n.false_conviction_rate ? "text-verdict" : "text-life"} />
          </dl>

          <section className="mt-20">
            <SectionHead title="The curve">Share of tricks resisted at the door, by generation.</SectionHead>
            <div className="card p-4 sm:p-6">
              <LearningCurve gens={summary.generations} />
            </div>
          </section>

          <section className="mt-20">
            <SectionHead title="Every test, every generation">
              Each square is one test email meeting one generation. Hover or focus a square for what happened.
            </SectionHead>
            <Heatmap ev={ev} />
          </section>

          <section className="mt-20 grid gap-4 md:grid-cols-2">
            <div className="card p-7">
              <h2 className="font-display text-[30px]">What this shows</h2>
              <ul className="mt-4 space-y-3 text-[15.5px] leading-relaxed text-moon/85">
                <li>The door uses inherited instincts only. A rising curve can only come from what was passed down.</li>
                <li>Every instinct had to stay silent on all harmless twins before the court would pass it down.</li>
                <li>{n.escaped === 0 ? "No trick slipped past both the door and the court." : `${n.escaped} tricks slipped past both the door and the court. They're marked red above.`}</li>
              </ul>
            </div>
            <div className="card p-7">
              <h2 className="font-display text-[30px]">What it doesn't</h2>
              <ul className="mt-4 space-y-3 text-[15.5px] leading-relaxed text-mist">
                <li>Our suite has {ev.rows.length} test emails. Real attackers are more varied than any fixed set.</li>
                <li>A trick with no family resemblance to an earlier one meets a child who knows nothing about it.</li>
                <li>When the judge is unsure, the item is held for Harsh. That costs him a little time on purpose.</li>
              </ul>
            </div>
          </section>
        </>
      )}
    </Page>
  );
}

function Num({ v, label, tone = "text-moon" }: { v: number | null; label: string; tone?: string }) {
  return (
    <div className="bg-night px-5 py-6">
      <dd className={`font-display text-[52px] leading-none ${tone}`}>
        {v === null ? pct(null) : <NumberTicker value={v} suffix="%" decimals={v % 1 ? 1 : 0} />}
      </dd>
      <dt className="mt-2 text-[13.5px] leading-snug text-mist">{label}</dt>
    </div>
  );
}
