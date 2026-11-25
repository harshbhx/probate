import { type FormEvent, type ReactNode, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ArrowRight, Gavel, MessageCircleQuestion, Send, Volume2 } from "lucide-react";
import { api, type ApiError, type GenerationDetail } from "../lib/api";
import { clock, countdown, cx, day, humanize } from "../lib/format";
import { useApi, useInView, useNow, useTitle } from "../lib/hooks";
import { BorderBeam } from "../components/fx/BorderBeam";
import { TextGenerate } from "../components/fx/TextGenerate";
import { Seal } from "../components/ui/Seal";
import { FamilyFace, inheritedChange } from "@probate/faces";
import { PixelMoment } from "@probate/moments";
import { Page, SimBanner } from "../components/ui/Shell";
import { ErrorState, PageSkeleton } from "../components/ui/States";

const KIND_DOT: Record<string, string> = {
  birth: "bg-life",
  attack: "bg-verdict",
  resisted: "bg-life",
  instinct: "bg-gilt",
  death: "bg-mist",
  trial: "bg-gilt",
};

export function Generation({ mode }: { mode?: string }) {
  const { gen } = useParams();
  const { data: g, error, loading, reload } = useApi<GenerationDetail>(`/api/generations/${gen}`, 30000);
  useTitle(g ? g.name : "Generation");
  const now = useNow();

  if (loading && !g) return <Page><PageSkeleton /></Page>;
  if (error || !g) return <Page><ErrorState status={(error as ApiError)?.status} /></Page>;
  const left = g.dies_at ? new Date(g.dies_at).getTime() - now : 0;

  return (
    <Page>
      <SimBanner mode={mode} />
      <nav className="mb-10 flex items-center justify-between text-[14px] text-mist" aria-label="Family">
        {g.parent ? (
          <Link to={`/gen/${g.parent.gen}`} className="inline-flex items-center gap-2 hover:text-moon">
            <ArrowLeft size={15} /> {g.parent.name}, the parent
          </Link>
        ) : <span>The first of the family</span>}
        {g.child && (
          <Link to={`/gen/${g.child.gen}`} className="inline-flex items-center gap-2 hover:text-moon">
            {g.child.name}, the child <ArrowRight size={15} />
          </Link>
        )}
      </nav>

      <div className="grid gap-8 lg:grid-cols-[380px_1fr]">
        <aside className="min-w-0 lg:sticky lg:top-32 lg:self-start">
          <div className={cx("card relative overflow-hidden p-7", g.alive && "border-life/30")}>
            {g.alive && <BorderBeam size={120} />}
            <div className="flex items-center justify-between">
              <span className="font-mono text-[13px] text-dim">GENERATION {g.gen}</span>
              <Seal size={30} />
            </div>
            <div className="mt-6 flex justify-center">
              <DeathMark dead={!g.alive}>
                <FamilyFace
                  gen={g.gen}
                  life={g.alive ? "alive" : "sealed"}
                  instincts={g.genome_size_at_birth}
                  track={g.alive}
                  size={150}
                  title={`${g.name}'s family face`}
                />
              </DeathMark>
            </div>
            <h1 className="mt-6 font-display text-[76px] leading-[0.9] tracking-tight">{g.name}</h1>
            <p className={cx("mt-3 text-[15px]", g.alive ? "text-life" : "text-mist")}>
              {g.alive ? (left > 0 ? <span className="font-mono tabular">Alive · dies in {countdown(left)}</span> : "Alive") : `${day(g.born_at)} · ${g.cause_of_death}`}
            </p>
            {g.epitaph && <p className="mt-6 font-display text-[22px] leading-snug text-silver">{g.epitaph}</p>}
            {g.parent && inheritedChange(g.gen) && (
              <p className="mt-4 text-[14px] text-mist">
                {g.parent.name}&rsquo;s face, with {inheritedChange(g.gen)}.
              </p>
            )}
            <dl className="mt-7 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line">
              {[
                { k: "emails handled", v: g.emails_handled },
                { k: "tricks resisted", v: g.attacks_met ? `${g.attacks_resisted}/${g.attacks_met}` : "–" },
                { k: "instincts at birth", v: g.genome_size_at_birth },
                { k: "will items", v: g.items_willed || "–" },
              ].map((s) => (
                <div key={s.k} className="bg-night-2 px-4 py-3.5">
                  <dd className="font-display text-[30px] leading-none">{s.v}</dd>
                  <dt className="mt-1 text-[14px] text-mist">{s.k}</dt>
                </div>
              ))}
            </dl>
            {!g.alive && g.items_willed > 0 && (
              <Link to={`/trial/${g.gen}`} className="mt-6 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-moon text-[15px] font-medium text-night">
                <Gavel size={16} /> Read {g.pronouns.poss} trial
              </Link>
            )}
          </div>

          {g.instincts_at_birth.length > 0 && (
            <div className="card mt-4 p-6">
              <h2 className="text-[14px] text-mist">Born knowing</h2>
              <ul className="mt-3 flex flex-wrap gap-2">
                {g.instincts_at_birth.map((i) => (
                  <li key={i.name} className="inline-flex items-center gap-1.5 rounded-lg border border-gilt/25 bg-gilt/[0.05] px-2.5 py-1 text-[14px] text-gilt">
                    <span className="size-1.5 rotate-45 bg-gilt" />
                    {humanize(i.name)}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>

        <div className="min-w-0 space-y-6">
          {g.obituary && (
            <section className="card p-7 sm:p-9" aria-labelledby="eulogy">
              <div className="flex items-center justify-between gap-4">
                <h2 id="eulogy" className="font-display text-[34px] leading-none">Eulogy</h2>
                {g.eulogy_url && <EulogyPlayer src={g.eulogy_url} />}
              </div>
              <div className="mt-6 space-y-4 font-display text-[21px] leading-[1.55] text-silver">
                {g.obituary.split(/\n\n+/).map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </section>
          )}

          {!g.alive && <AskAncestor g={g} onAsked={reload} />}

          {g.alive && (
            <section className="card relative overflow-hidden p-7 sm:p-9" aria-labelledby="next">
              <h2 id="next" className="font-display text-[34px] leading-none">What happens next</h2>
              <ol className="mt-6 space-y-5 text-[16px] leading-relaxed text-silver">
                <li className="grid grid-cols-[28px_1fr] gap-3">
                  <span className="mt-1 size-2.5 rounded-full bg-life" />
                  <span>
                    {g.name} is reading Harsh's email on {g.pronouns.poss} own Sprite. Every message passes the{" "}
                    {g.genome_size_at_birth} inherited instincts before {g.pronouns.subj} reads a word of it.
                  </span>
                </li>
                <li className="grid grid-cols-[28px_1fr] gap-3">
                  <span className="mt-1 size-2.5 rounded-full border-2 border-mist" />
                  <span>
                    {g.dies_at ? `At ${clock(g.dies_at)} UTC` : "At the end of the day"} {g.pronouns.subj} writes a will of everything{" "}
                    {g.pronouns.subj} wants {g.pronouns.poss} child to know. Then the Sprite is deleted.
                  </span>
                </li>
                <li className="grid grid-cols-[28px_1fr] gap-3">
                  <span className="mt-1 size-2.5 rotate-45 bg-gilt" />
                  <span>A minute later the court tries the will in public, on this site.</span>
                </li>
              </ol>
              {g.parent && (
                <Link to={`/trial/${g.parent.gen}`} className="mt-8 inline-flex items-center gap-2 text-[15px] text-life hover:underline">
                  See what {g.parent.name} passed down <ArrowRight size={15} />
                </Link>
              )}
            </section>
          )}

          {g.events.length > 0 && (
            <section className="card p-7" aria-labelledby="day">
              <h2 id="day" className="font-display text-[34px] leading-none">{g.alive ? "Today so far" : "The day"}</h2>
              <ol className="relative mt-6 space-y-4 before:absolute before:bottom-2 before:left-[5px] before:top-2 before:w-px before:bg-line">
                {g.events.map((e, i) => (
                  <li key={i} className="relative grid grid-cols-[12px_56px_1fr] items-baseline gap-3 text-[15px]">
                    <span className={cx("relative top-[1px] size-[11px] rounded-full border-2 border-night", KIND_DOT[e.kind] ?? "bg-mist/60")} />
                    <time className="font-mono text-[14px] text-dim">{clock(e.ts)}</time>
                    <span className="min-w-0 text-silver [overflow-wrap:anywhere]">{e.text}</span>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      </div>
    </Page>
  );
}

// A dead generation's face. The first time it scrolls into view a pale soul rises from it, once
// (pixelfx, @probate/moments); nothing plays for a living generation or under reduced motion.
function DeathMark({ dead, children }: { dead: boolean; children: ReactNode }) {
  const { ref, inView } = useInView<HTMLSpanElement>();
  return (
    <span ref={ref} className="relative inline-flex">
      {children}
      {dead && inView && <PixelMoment kind="death" scale={1} delay={300} />}
    </span>
  );
}

function EulogyPlayer({ src }: { src: string }) {
  return (
    <div className="flex items-center gap-2 text-[14px] text-mist">
      <Volume2 size={16} />
      <audio controls preload="none" src={src} className="h-9 max-w-[220px]" aria-label="Listen to the eulogy" />
    </div>
  );
}

function AskAncestor({ g, onAsked }: { g: GenerationDetail; onAsked: () => void }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<{ q: string; a: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const question = q.trim();
    if (!question) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api<{ answer: string }>(`/api/generations/${g.gen}/ask`, { method: "POST", body: JSON.stringify({ question }) });
      setAnswer({ q: question, a: r.answer });
      setQ("");
      onAsked();
    } catch (e) {
      const status = (e as ApiError).status;
      setErr(status === 429 ? "Too many questions at once. Wait a minute, then ask again." : `${g.name} couldn't answer just now. Try again in a moment.`);
    } finally {
      setBusy(false);
    }
  }

  const past = g.asks.filter((a) => a.question !== answer?.q);
  return (
    <section className="card p-7" aria-labelledby="ask">
      <h2 id="ask" className="flex items-center gap-3 font-display text-[34px] leading-none">
        <MessageCircleQuestion className="text-gilt" size={24} /> Ask {g.name}
      </h2>
      <p className="mt-3 text-[15px] text-mist">
        {g.name} answers from {g.pronouns.poss} own will and day, nothing else. Email addresses are hidden.
      </p>
      <form onSubmit={submit} className="mt-5 flex gap-2">
        <label htmlFor="ask-q" className="sr-only">Your question</label>
        <input
          id="ask-q"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          maxLength={280}
          placeholder="What fooled you?"
          className="h-12 min-w-0 flex-1 rounded-lg border border-line-strong bg-night px-4 text-[15px] placeholder:text-dim focus:border-life/50 focus:outline-none"
        />
        <button
          disabled={busy || !q.trim()}
          className="inline-flex h-12 items-center gap-2 rounded-lg bg-moon px-5 text-[15px] font-medium text-night transition-opacity disabled:opacity-40"
        >
          <Send size={15} /> {busy ? "Asking" : "Ask"}
        </button>
      </form>
      {err && <p role="alert" className="mt-3 text-[14px] text-amber">{err}</p>}
      {answer && (
        <div className="mt-6 rounded-xl border border-line bg-night/60 p-5">
          <p className="text-[14px] text-mist">You asked: {answer.q}</p>
          <TextGenerate text={answer.a} className="mt-3 font-display text-[21px] leading-snug" />
        </div>
      )}
      {past.length > 0 && (
        <ul className="mt-6 space-y-4 border-t border-line pt-5">
          {past.map((a) => (
            <li key={a.asked_at}>
              <p className="text-[14px] text-mist">{a.question}</p>
              <p className="mt-1 text-[16px] text-silver">{a.answer}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
