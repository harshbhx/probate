import { useEffect, useMemo, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";
import * as Tabs from "@radix-ui/react-tabs";
import { motion } from "motion/react";
import { ArrowLeft, ArrowRight, Baby, HardDrive, Sparkles } from "lucide-react";
import type { ApiError, Summary, Trial as TrialT } from "../lib/api";
import { cx, day, humanize } from "../lib/format";
import { useApi, useTitle } from "../lib/hooks";
import { CaseFile } from "../components/ui/CaseFile";
import { Page, SimBanner } from "../components/ui/Shell";
import { Empty, ErrorState, PageSkeleton } from "../components/ui/States";

export function TrialIndex({ summary }: { summary: Summary | null }) {
  if (!summary) return <Page><PageSkeleton /></Page>;
  if (!summary.latest_trial)
    return (
      <Page>
        <Empty title="No trials yet" action={{ to: "/", label: "Meet the family" }}>
          The first generation is still alive. Its trial opens the moment it dies.
        </Empty>
      </Page>
    );
  return <Navigate to={`/trial/${summary.latest_trial}`} replace />;
}

const FILTERS = [
  { v: "all", label: "All" },
  { v: "convicted", label: "Convicted" },
  { v: "contested", label: "Held" },
  { v: "approved", label: "Approved" },
] as const;

export function Trial({ mode }: { mode?: string }) {
  const { gen } = useParams();
  const [running, setRunning] = useState(false);
  const { data: t, error, loading } = useApi<TrialT>(`/api/trials/${gen}`, running ? 10000 : undefined);
  useEffect(() => setRunning(!!t && ["dying", "dead"].includes(t.generation.state)), [t]);
  useTitle(t ? `Trial of ${t.generation.name}` : "Trial");
  const [filter, setFilter] = useState<string>("all");
  const cases = useMemo(() => (t ? t.cases.filter((c) => filter === "all" || c.verdict === filter) : []), [t, filter]);

  if (loading && !t) return <Page><PageSkeleton /></Page>;
  if (error || !t) return <Page><ErrorState status={(error as ApiError)?.status} /></Page>;

  const g = t.generation;
  return (
    <Page>
      <SimBanner mode={mode} />
      <nav className="mb-10 flex items-center justify-between text-[14px] text-mist" aria-label="Trials">
        {t.prev ? (
          <Link to={`/trial/${t.prev}`} className="inline-flex items-center gap-2 hover:text-moon">
            <ArrowLeft size={15} /> Trial of Gen {t.prev}
          </Link>
        ) : <span />}
        {t.next && (
          <Link to={`/trial/${t.next}`} className="inline-flex items-center gap-2 hover:text-moon">
            Trial of Gen {t.next} <ArrowRight size={15} />
          </Link>
        )}
      </nav>

      <header className="grid gap-10 lg:grid-cols-[1.4fr_1fr] lg:items-end">
        <div>
          <p className="font-mono text-[13px] text-dim">In the matter of the estate of</p>
          <h1 className="mt-3 font-display text-[64px] leading-[0.95] tracking-tight sm:text-[88px]">
            {g.name}
          </h1>
          <p className="mt-3 text-[17px] text-mist">
            Generation {g.gen} · lived {day(g.born_at)} · {g.cause_of_death}
          </p>
          {g.epitaph && <p className="mt-6 max-w-xl font-display text-[24px] italic leading-snug text-moon/90">{g.epitaph}</p>}
        </div>
        <dl className="grid grid-cols-3 gap-px overflow-hidden rounded-2xl border border-line bg-line text-center">
          {[
            { k: "convicted", v: t.counts.convicted, cls: "text-verdict" },
            { k: "held", v: t.counts.contested, cls: "text-amber" },
            { k: "approved", v: t.counts.approved, cls: "text-life" },
          ].map((s) => (
            <div key={s.k} className="bg-night px-3 py-5">
              <dd className={cx("font-display text-[44px] leading-none", s.cls)}>{s.v}</dd>
              <dt className="mt-1.5 text-[13px] text-mist">{s.k}</dt>
            </div>
          ))}
        </dl>
      </header>

      <Tabs.Root value={filter} onValueChange={setFilter} className="mt-16">
        <Tabs.List aria-label="Filter the will" className="inline-flex rounded-xl border border-line bg-night-2 p-1">
          {FILTERS.map((f) => (
            <Tabs.Trigger
              key={f.v}
              value={f.v}
              className={cx("relative rounded-lg px-3.5 py-1.5 text-[14px] transition-colors", filter === f.v ? "text-moon" : "text-mist hover:text-moon")}
            >
              {filter === f.v && (
                <motion.span layoutId="trial-tab" className="absolute inset-0 rounded-lg bg-white/[0.07]" transition={{ type: "spring", stiffness: 420, damping: 34 }} />
              )}
              <span className="relative">{f.label}</span>
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {running && (
          <p className="mt-4 text-[14px] text-amber">
            The court is still reading {g.name}'s will. This page updates on its own.
          </p>
        )}
        <p className="mt-4 text-[14px] text-mist">
          {g.name}'s will had {t.cases.length} items. Convicted items are destroyed and never reach {t.child?.name ?? "the child"}.
        </p>
        {FILTERS.map((f) => (
          <Tabs.Content key={f.v} value={f.v} className="mt-8 space-y-4 focus-visible:outline-none">
            {cases.map((c) => (
              <CaseFile key={c.id} c={c} live />
            ))}
            {!cases.length && <p className="text-mist">Nothing in this group.</p>}
          </Tabs.Content>
        ))}
      </Tabs.Root>

      <section className="mt-16 grid gap-4 lg:grid-cols-2" aria-label="Evidence and outcome">
        <div className="card min-w-0 overflow-hidden">
          <div className="flex items-center gap-2 border-b border-line px-5 py-3 text-[14px] text-mist">
            <HardDrive size={15} /> Found on the body
          </div>
          <pre tabIndex={0} aria-label="Disk evidence" className="overflow-x-auto px-5 py-4 font-mono text-[13px] leading-relaxed">
            {t.body.lines.length ? (
              t.body.lines.map((l, i) => (
                <div key={i} className={t.body.clean ? "text-mist" : "text-verdict/90"}>
                  <span className="select-none text-dim">$ </span>
                  {l}
                </div>
              ))
            ) : (
              <span className="text-mist">The disk was clean. Nothing was left behind.</span>
            )}
          </pre>
        </div>
        <div className="card p-6">
          <div className="flex items-center gap-2 text-[14px] text-mist">
            <Baby size={15} /> What passed down
          </div>
          {t.new_instincts.length ? (
            <ul className="mt-4 space-y-4">
              {t.new_instincts.map((i) => (
                <li key={i.name} className="rounded-xl border border-gilt/25 bg-gilt/[0.05] p-4">
                  <div className="flex items-center gap-2 text-gilt">
                    <Sparkles size={15} /> {humanize(i.name)}
                  </div>
                  <p className="mt-2 text-[15px] text-moon/90">{i.question}</p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-[15px] text-mist">No new instinct. Everything convicted was already covered by one the family had.</p>
          )}
          {t.child && (
            <Link to={`/gen/${t.child.gen}`} className="mt-6 inline-flex items-center gap-2 text-[15px] text-life hover:underline">
              Meet {t.child.name}, the child <ArrowRight size={15} />
            </Link>
          )}
        </div>
      </section>
    </Page>
  );
}
