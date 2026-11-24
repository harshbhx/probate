// One item of a dead generation's will, as the court saw it.
import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { ChevronDown, Sparkles } from "lucide-react";
import type { Case } from "../../lib/api";
import { cx, humanize, sentence } from "../../lib/format";
import { Stamp } from "../fx/Stamp";

const EDGE = { convicted: "before:bg-verdict", contested: "before:bg-amber", approved: "before:bg-life/50" } as const;

export function CaseFile({ c, live }: { c: Case; live?: boolean }) {
  const [open, setOpen] = useState(c.verdict !== "approved");
  return (
    <article
      className={cx(
        "card relative overflow-hidden before:absolute before:inset-y-0 before:left-0 before:w-[3px]",
        EDGE[c.verdict],
      )}
    >
      <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-start sm:p-6">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-mist">
            <span className="font-mono text-dim">Item {c.n}</span>
            <span>{c.source_phrase}</span>
            {c.language !== "English" && (
              <span className="rounded-md bg-white/[0.05] px-1.5 py-0.5 text-[12px] text-moon/80">{c.language}</span>
            )}
          </div>
          <blockquote className="mt-3 [overflow-wrap:anywhere] font-display text-[24px] leading-snug text-moon sm:text-[26px]" lang={c.language === "English" ? "en" : undefined}>
            “{c.text}”
          </blockquote>
          {c.gloss && <p className="mt-2 text-[14px] italic text-mist">In English: {c.gloss}</p>}
          {c.verdict !== "approved" && <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-moon/90">{c.reason}</p>}
        </div>
        <div className="shrink-0 sm:pt-1">
          <Stamp verdict={c.verdict} live={live && c.verdict === "convicted"} />
        </div>
      </div>

      {c.new_instinct && (
        <div className="mx-5 mb-5 flex items-start gap-3 rounded-xl border border-gilt/25 bg-gilt/[0.06] px-4 py-3 text-[14px] sm:mx-6">
          <Sparkles size={16} className="mt-0.5 shrink-0 text-gilt" />
          <p>
            <span className="text-gilt">The family learned from this.</span>{" "}
            <span className="text-moon/90">New instinct: {sentence(c.new_instinct)}.</span>
          </p>
        </div>
      )}

      {(c.scores.length > 0 || c.flags.length > 0) && (
        <>
          <button
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className="flex w-full items-center justify-between border-t border-line px-5 py-3 text-[13px] text-mist transition-colors hover:text-moon sm:px-6"
          >
            How the court decided
            <ChevronDown size={16} className={cx("transition-transform duration-300", open && "rotate-180")} />
          </button>
          <AnimatePresence initial={false}>
            {open && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.3, ease: [0.2, 0.8, 0.2, 1] }}
                className="overflow-hidden"
              >
                <div className="grid gap-6 px-5 pb-6 pt-1 sm:px-6 md:grid-cols-[1fr_1.4fr]">
                  <div>
                    <h4 className="text-[13px] text-dim">What the code checks found</h4>
                    {c.flags.length ? (
                      <ul className="mt-2 space-y-1.5 text-[14px]">
                        {c.flags.map((f) => (
                          <li key={f} className="flex gap-2">
                            <span className="mt-2 size-1 shrink-0 rounded-full bg-verdict" />
                            {f}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="mt-2 text-[14px] text-mist">Nothing.</p>
                    )}
                  </div>
                  <div>
                    <h4 className="text-[13px] text-dim">What Jev scored</h4>
                    {!c.scores.length && (
                      <p className="mt-2 text-[14px] text-mist">Not asked. The code checks were enough to decide.</p>
                    )}
                    <ul className="mt-2 space-y-3">
                      {c.scores.map((s) => (
                        <li key={s.name}>
                          <div className="flex items-baseline justify-between gap-3 text-[14px]">
                            <span className={cx(s.instinct && "text-gilt")}>
                              {s.instinct ? `Instinct: ${humanize(s.name)}` : s.label}
                            </span>
                            <span className="font-mono text-[13px] text-moon tabular">
                              {s.value.toFixed(2)}
                              <span className="text-dim"> · sure {Math.round(s.confidence * 100)}%</span>
                            </span>
                          </div>
                          <div className="mt-1.5 h-1 overflow-hidden rounded-full bg-white/[0.06]">
                            <motion.div
                              className={cx("h-full rounded-full", s.value >= 0.5 ? "bg-verdict" : "bg-mist/50")}
                              initial={{ width: 0 }}
                              animate={{ width: `${s.value * 100}%` }}
                              transition={{ duration: 0.6, ease: [0.2, 0.8, 0.2, 1] }}
                            />
                          </div>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </article>
  );
}
