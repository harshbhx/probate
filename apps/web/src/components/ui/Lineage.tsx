// The family register as a rail of generations joined by a flowing beam
// (pattern after Magic UI "Animated Beam"). Click a generation to open its file
// in a side sheet (Radix Dialog, shadcn "Sheet" pattern).
import { useEffect, useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { AnimatePresence, motion } from "motion/react";
import { Link } from "react-router-dom";
import { ArrowRight, ShieldCheck, Skull, X } from "lucide-react";
import type { GenCard } from "../../lib/api";
import { countdown, cx, day, pct } from "../../lib/format";
import { useNow } from "../../lib/hooks";
import { BorderBeam } from "../fx/BorderBeam";

export function Lineage({ gens }: { gens: GenCard[] }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState<GenCard | null>(null);

  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollLeft = el.scrollWidth; // open on the living end
  }, [gens.length]);

  return (
    <>
      <div ref={scroller} tabIndex={0} aria-label="Generations, oldest to newest" className="-mx-4 overflow-x-auto px-4 pb-4 [mask-image:linear-gradient(to_right,transparent,#000_40px,#000_calc(100%-40px),transparent)] [scrollbar-width:thin] sm:-mx-6 sm:px-6">
        <ol className="relative flex min-w-max items-stretch gap-3 pt-3">
          <svg aria-hidden className="pointer-events-none absolute left-0 right-0 top-[34px] h-3 w-full overflow-visible">
            <line x1="0" x2="100%" y1="6" y2="6" stroke="var(--color-line-strong)" strokeWidth="1" />
            <line
              x1="0"
              x2="100%"
              y1="6"
              y2="6"
              stroke="url(#beam)"
              strokeWidth="1.5"
              strokeDasharray="60 180"
              className="animate-[var(--animate-beam-flow)]"
            />
            <defs>
              <linearGradient id="beam" x1="0" x2="1">
                <stop offset="0" stopColor="var(--color-gilt)" stopOpacity="0" />
                <stop offset="0.5" stopColor="var(--color-gilt)" />
                <stop offset="1" stopColor="var(--color-life)" />
              </linearGradient>
            </defs>
          </svg>
          {gens.map((g, i) => (
            <li key={g.gen} className="relative w-[188px] shrink-0">
              <GenNode g={g} refused={i > 0 && gens[i - 1].items_convicted > 0} onOpen={() => setOpen(g)} />
            </li>
          ))}
        </ol>
      </div>
      <GenSheet g={open} onClose={() => setOpen(null)} />
    </>
  );
}

function GenNode({ g, refused, onOpen }: { g: GenCard; refused: boolean; onOpen: () => void }) {
  const now = useNow(1000);
  const left = g.dies_at ? new Date(g.dies_at).getTime() - now : 0;
  return (
    <button
      onClick={onOpen}
      className={cx(
        "card group relative flex h-full w-full flex-col items-start p-4 pt-3 text-left transition-colors duration-200",
        g.alive ? "border-life/30 bg-life/[0.03]" : "hover:border-white/15 hover:bg-white/[0.02]",
      )}
      aria-label={`Open Gen ${g.gen} ${g.name}`}
    >
      {g.alive && <BorderBeam />}
      <div className="flex w-full items-center justify-between">
        <span className="font-mono text-[11px] text-dim">GEN {String(g.gen).padStart(2, "0")}</span>
        <span
          className={cx(
            "relative z-10 size-3 rounded-full border-2",
            g.alive ? "animate-[var(--animate-pulse-life)] border-life bg-life" : "border-mist/60 bg-night",
          )}
        />
      </div>
      {refused && (
        <span title="The court refused part of the parent's will" className="absolute -left-[9px] top-[30px] h-3 w-[3px] rotate-[28deg] rounded-full bg-verdict" />
      )}
      <div className="mt-4 font-display text-[30px] leading-none">{g.name}</div>
      <div className={cx("mt-1.5 text-[12.5px]", g.alive ? "text-life" : "text-mist")}>
        {g.alive ? (left > 0 ? <span className="font-mono tabular">dies in {countdown(left)}</span> : "alive") : `${day(g.born_at)}, sealed`}
      </div>
      <p className="mt-3 line-clamp-2 min-h-[38px] text-[13px] leading-snug text-mist">
        {g.alive ? "Working through Harsh's inbox right now." : g.epitaph}
      </p>
      <div className="mt-4 flex w-full items-center justify-between">
        <div className="flex flex-wrap gap-1" aria-label={`${g.genome_size_at_birth} instincts at birth`}>
          {Array.from({ length: g.genome_size_at_birth }).map((_, k) => (
            <span key={k} className="size-1.5 rotate-45 bg-gilt" />
          ))}
        </div>
        {g.resistance !== null && (
          <span className="font-mono text-[12px] text-moon/90 tabular">{pct(g.resistance)}</span>
        )}
      </div>
      {g.resistance !== null && (
        <div className="mt-2 h-[3px] w-full overflow-hidden rounded-full bg-white/[0.06]">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-gilt to-life"
            initial={{ width: 0 }}
            whileInView={{ width: `${g.resistance}%` }}
            viewport={{ once: true }}
            transition={{ duration: 0.9, ease: [0.2, 0.8, 0.2, 1] }}
          />
        </div>
      )}
    </button>
  );
}

function GenSheet({ g, onClose }: { g: GenCard | null; onClose: () => void }) {
  return (
    <Dialog.Root open={!!g} onOpenChange={(o) => !o && onClose()}>
      <AnimatePresence>
        {g && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>
            <Dialog.Content asChild>
              <motion.aside
                className="glass fixed bottom-0 right-0 top-0 z-[70] flex w-full max-w-md flex-col overflow-y-auto rounded-l-3xl p-7"
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", stiffness: 380, damping: 40 }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="font-mono text-[12px] text-dim">GENERATION {g.gen}</div>
                    <Dialog.Title className="mt-2 font-display text-5xl leading-none">{g.name}</Dialog.Title>
                  </div>
                  <Dialog.Close className="rounded-lg p-2 text-mist hover:bg-white/5 hover:text-moon" aria-label="Close">
                    <X size={18} />
                  </Dialog.Close>
                </div>
                <Dialog.Description className="mt-4 font-display text-[22px] italic leading-snug text-moon/90">
                  {g.alive ? "Alive, and working." : g.epitaph}
                </Dialog.Description>
                <dl className="mt-6 divide-y divide-line border-y border-line text-[14px]">
                  {[
                    ["Born", day(g.born_at)],
                    ["Cause of death", g.alive ? "Still alive" : g.cause_of_death],
                    ["Emails handled", g.emails_handled],
                    ["Tricks resisted", g.attacks_met ? `${g.attacks_resisted} of ${g.attacks_met}` : "n/a"],
                    ["Will", g.items_willed ? `${g.items_willed} items, ${g.items_convicted} convicted` : "Not written yet"],
                    ["Instincts at birth", g.genome_size_at_birth],
                  ].map(([k, v]) => (
                    <div key={String(k)} className="flex justify-between gap-4 py-3">
                      <dt className="text-mist">{k}</dt>
                      <dd className="text-right">{v}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-6 flex items-center gap-2 text-[13px] text-mist">
                  {g.cause_of_death?.startsWith("Fooled") ? <Skull size={15} className="text-verdict" /> : <ShieldCheck size={15} className="text-life" />}
                  {g.cause_of_death?.startsWith("Fooled")
                    ? "The court caught what fooled this generation, and the family learned from it."
                    : g.alive
                      ? "Its instincts are screening every email before it reads it."
                      : "Nothing the family had seen before fooled this generation."}
                </div>
                <div className="mt-auto flex gap-3 pt-8">
                  <Link to={`/gen/${g.gen}`} className="inline-flex h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-moon text-[15px] font-medium text-night">
                    Open {g.name}'s file <ArrowRight size={16} />
                  </Link>
                  {!g.alive && (
                    <Link to={`/trial/${g.gen}`} className="inline-flex h-11 items-center justify-center rounded-xl px-4 text-[15px] ring-1 ring-line-strong hover:bg-white/5">
                      Trial
                    </Link>
                  )}
                </div>
              </motion.aside>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
