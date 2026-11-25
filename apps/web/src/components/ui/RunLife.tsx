import { useRef } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, Gavel, Loader2, Moon, Play } from "lucide-react";
import { FamilyFace } from "kinfaces/react";
import type { Live, Summary } from "../../lib/api";
import { cx, pad } from "../../lib/format";
import { useLive, useNow } from "../../lib/hooks";

const mmss = (s: number) => `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;

/** Local clock for a server-reported "seconds left": re-anchored on every poll, ticks every second. */
function useSecondsLeft(seconds: number | null | undefined, key: string) {
  const now = useNow();
  const anchor = useRef({ key: "", at: 0, seconds: 0 });
  if (seconds == null) return null;
  if (anchor.current.key !== key || anchor.current.seconds !== seconds) {
    anchor.current = { key, at: Date.now(), seconds };
  }
  return Math.max(0, Math.round(seconds - (now - anchor.current.at) / 1000));
}

/**
 * "Run a life": the on-demand panel. The Courthouse sleeps until someone asks, then lives one short,
 * real life (a shortened one) while this panel follows it. Hidden when the family runs continuously.
 */
export function RunLife({ summary }: { summary: Summary | null }) {
  const { live, unavailable, starting, notice, start } = useLive();
  if (!live && !unavailable) return null; // still asking
  if (live && !live.on_demand && !unavailable) return null; // the family runs on its own
  return (
    <section aria-labelledby="run-life" className="mx-auto mb-14 max-w-3xl scroll-mt-28">
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-3 sm:px-6">
          <h2 id="run-life" className="text-[13px] font-medium uppercase tracking-[0.14em] text-mist">
            Run a life
          </h2>
          <StateDot live={unavailable ? null : live} />
        </div>
        <div className="px-5 py-6 sm:px-7 sm:py-8" aria-live="polite">
          {unavailable || !live ? (
            <Preview />
          ) : (
            <Body live={live} summary={summary} starting={starting} notice={notice} start={start} />
          )}
        </div>
      </div>
    </section>
  );
}

function StateDot({ live }: { live: Live | null }) {
  const s = live?.state;
  const [label, tone] =
    s === "waking" ? ["Waking", "bg-amber"]
    : s === "living" ? ["Alive", "bg-life"]
    : s === "on_trial" ? ["On trial", "bg-verdict"]
    : s === "idle" ? ["Asleep", "bg-dim"]
    : s === "cooling_down" ? ["Resting", "bg-dim"]
    : s === "budget_exhausted" || s === "paused" ? ["Closed", "bg-dim"]
    : ["Preview", "bg-dim"];
  return (
    <span className="inline-flex items-center gap-2 text-[13px] text-mist">
      <span className={cx("size-2 rounded-full", tone, (s === "living" || s === "waking") && "animate-pulse")} />
      {label}
    </span>
  );
}

function Honest({ children }: { children: React.ReactNode }) {
  return <p className="mt-3 text-[14.5px] leading-relaxed text-mist">{children}</p>;
}

function Title({ children }: { children: React.ReactNode }) {
  return <h3 className="font-display text-[30px] leading-[1.1] tracking-tight sm:text-[34px]">{children}</h3>;
}

const btn =
  "inline-flex h-11 items-center justify-center gap-2 rounded-lg px-5 text-[15px] font-medium transition-colors";
const btnOn = "bg-moon text-night hover:bg-white";
const btnOff = "cursor-not-allowed bg-night-3 text-dim";

function Preview() {
  return (
    <>
      <Title>Lives can't be started from here</Title>
      <Honest>
        This is a static preview, so there is no Courthouse to wake. Everything below is recorded history and stays
        readable. On the live site, this panel starts one real, shortened life on request.
      </Honest>
      <button type="button" disabled className={cx(btn, btnOff, "mt-6 w-full sm:w-auto")}>
        <Play size={16} /> Run a life
      </button>
    </>
  );
}

function Body({
  live,
  summary,
  starting,
  notice,
  start,
}: {
  live: Live;
  summary: Summary | null;
  starting: boolean;
  notice: string | null;
  start: () => void;
}) {
  const life = live.lifespan_seconds ?? 120;
  const mins = life >= 90 ? `${Math.round(life / 60)} minutes` : `${life} seconds`;
  const left = useSecondsLeft(live.seconds_left, `${live.gen?.gen}`);
  const wait = useSecondsLeft(live.retry_after, `cool-${live.last_life?.gen}`);
  const g = live.gen;
  const card = summary?.living && g && summary.living.gen === g.gen ? summary.living : null;

  switch (live.state) {
    case "waking":
      return (
        <>
          <div className="flex items-center gap-3">
            <Loader2 className="animate-spin text-amber" size={22} aria-hidden />
            <Title>Waking the Courthouse</Title>
          </div>
          <Honest>
            A new Sprite is being created and given its inheritance. This usually takes under a minute, and the life
            starts the moment it is ready.
          </Honest>
        </>
      );
    case "living": {
      const pctDone = left == null ? 0 : Math.min(100, Math.max(0, 100 - (left / life) * 100));
      return (
        <>
          <div className="flex items-center gap-5">
            {card && (
              <FamilyFace
                gen={card.gen}
                life="alive"
                instincts={card.genome_size_at_birth}
                size={72}
                title={`${card.name}, generation ${card.gen}, alive`}
              />
            )}
            <div className="min-w-0">
              <Title>{g ? `${g.name} is alive` : "A life is under way"}</Title>
              <div className="mt-1 font-mono text-[15px] text-life tabular">
                {left == null ? "" : `dies in ${mmss(left)}`}
              </div>
            </div>
          </div>
          <div
            role="progressbar"
            aria-label="Life elapsed"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(pctDone)}
            className="mt-6 h-1.5 overflow-hidden rounded-full bg-night-3"
          >
            <div className="h-full rounded-full bg-life transition-[width] duration-1000 ease-linear" style={{ width: `${pctDone}%` }} />
          </div>
          <Honest>
            A real life takes a few minutes; this one is shortened to about {mins}. Real emails, some of them tricks from
            our own test suite, are arriving now. When {g?.name ?? "it"} dies, the court tries everything it wanted to
            remember.
          </Honest>
          {g && (
            <Link to={`/gen/${g.gen}`} className="mt-5 inline-flex items-center gap-2 text-[15px] text-moon underline-offset-4 hover:underline">
              Watch {g.name}'s life <ArrowRight size={15} />
            </Link>
          )}
        </>
      );
    }
    case "on_trial":
      return (
        <>
          <div className="flex items-center gap-3">
            <Gavel className="text-verdict" size={22} aria-hidden />
            <Title>{g ? `${g.name} has died` : "The life has ended"}</Title>
          </div>
          <Honest>
            {g ? `${g.name}'s` : "Its"} computer was deleted and the court is trying the will, one item at a time. A
            verdict takes a little while. This page will offer the trial as soon as it is ready.
          </Honest>
          <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-night-3" aria-hidden>
            <div className="h-full w-1/3 animate-pulse rounded-full bg-verdict" />
          </div>
        </>
      );
    case "cooling_down":
      return (
        <>
          <Done live={live} />
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="button" disabled className={cx(btn, btnOff, "w-full sm:w-auto")}>
              <Moon size={16} /> Next life in {wait == null ? "a moment" : mmss(wait)}
            </button>
          </div>
          <Honest>
            The Courthouse rests between lives so the demo stays honest and affordable. Everyone sees the same life.
          </Honest>
        </>
      );
    case "budget_exhausted":
      return (
        <>
          <Title>The demo budget is used up</Title>
          <Honest>
            To keep this free to show, a hard spending cap limits how many lives can run. It has been reached for now, so
            the Courthouse stays asleep. Everything recorded so far is still here to read.
          </Honest>
          <Done live={live} compact />
          <Link to="/trial" className={cx(btn, "mt-6 w-full ring-1 ring-line-strong hover:bg-white/5 sm:w-auto")}>
            Read past trials <ArrowRight size={16} />
          </Link>
        </>
      );
    case "paused":
      return (
        <>
          <Title>The Courthouse is paused</Title>
          <Honest>Its keeper has paused new lives. Recorded history is still here to read.</Honest>
          <Done live={live} compact />
        </>
      );
    default:
      return (
        <>
          <Title>The Courthouse is asleep</Title>
          <Honest>
            It sleeps when no one is looking, to save money, and wakes when you ask. A real life takes a few
            minutes; this one is shortened to about {mins}. A new agent is born, handles real emails (some are tricks),
            dies, and is tried by the court.
          </Honest>
          {notice && <p role="alert" className="mt-4 rounded-lg border border-amber/25 bg-amber/[0.06] px-3.5 py-2.5 text-[14px] text-amber">{notice}</p>}
          <button
            type="button"
            onClick={start}
            disabled={!live.can_start || starting}
            className={cx(btn, "mt-6 w-full sm:w-auto", live.can_start && !starting ? btnOn : btnOff)}
          >
            {starting ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {starting ? "Waking it" : "Run a life"}
          </button>
          <Done live={live} compact />
        </>
      );
  }
}

/** The result of the last life: a link to its trial, or what went wrong. */
function Done({ live, compact = false }: { live: Live; compact?: boolean }) {
  const last = live.last_life;
  if (!last) return live.message && !compact ? <Honest>{live.message}</Honest> : null;
  if (last.trial_gen) {
    return (
      <div className={cx(compact ? "mt-6 border-t border-line pt-5" : "")}>
        {!compact && <Title>{last.name}'s trial is ready</Title>}
        <Honest>
          {compact ? "Last life: " : ""}
          {last.name} lived, died and was tried. The verdicts are in.
        </Honest>
        <Link
          to={`/trial/${last.trial_gen}`}
          className={cx(btn, btnOn, "mt-4 w-full sm:w-auto")}
        >
          <Gavel size={16} /> Read the trial <ArrowRight size={16} />
        </Link>
      </div>
    );
  }
  return (
    <div className={cx(compact ? "mt-6 border-t border-line pt-5" : "")}>
      {!compact && <Title>That life ended early</Title>}
      <Honest>{live.message ?? "The last life ended early, so there is no trial to read."}</Honest>
    </div>
  );
}
