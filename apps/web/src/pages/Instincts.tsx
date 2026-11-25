import { Link } from "react-router-dom";
import type { Instinct } from "../lib/api";
import { cx, sentence } from "../lib/format";
import { useApi, useTitle } from "../lib/hooks";
import { SpotlightCard } from "../components/fx/SpotlightCard";
import { FamilyFace } from "@probate/faces";
import { Page, SimBanner } from "../components/ui/Shell";
import { Empty, ErrorState, PageSkeleton } from "../components/ui/States";

export function Instincts({ mode }: { mode?: string }) {
  const { data, error, loading } = useApi<{ instincts: Instinct[] }>("/api/genome");
  useTitle("Instincts");
  if (loading && !data) return <Page><PageSkeleton /></Page>;
  if (error || !data) return <Page><ErrorState /></Page>;
  const list = data.instincts;

  return (
    <Page>
      <SimBanner mode={mode} />
      <header className="max-w-3xl">
        <h1 className="font-display text-[56px] leading-[0.98] tracking-tight sm:text-[76px]">What the family knows</h1>
        <p className="mt-5 text-[18px] leading-relaxed text-mist">
          Each instinct is a question the court learned to ask after a generation got fooled. Every child is born with
          all of them, and they screen each email before the child reads it.
        </p>
      </header>

      {list.length === 0 ? (
        <div className="mt-12">
          <Empty title="Born knowing nothing" action={{ to: "/", label: "Meet the family" }}>
            No instincts yet. The first one is written at the first trial that convicts something new.
          </Empty>
        </div>
      ) : (
        <ul className="mt-14 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {list.map((i, k) => (
            <li key={i.name} className={cx("min-w-0", k === 0 && (list.length + 1) % 3 === 0 && "lg:col-span-2")}>
              <SpotlightCard className="flex h-full flex-col p-6" color="rgb(226 190 106 / 0.10)">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-2 text-[13px] text-gilt">
                    <span className="size-2 rotate-45 bg-gilt" /> since Gen {i.added_in_gen}
                  </span>
                  {i.learned_from && (
                    <Link to={`/trial/${i.learned_from.gen}`} className="flex items-center gap-2 text-[13px] text-mist hover:text-moon">
                      learned from {i.learned_from.name}
                      <FamilyFace gen={i.learned_from.gen} life="sealed" size={30} />
                    </Link>
                  )}
                </div>
                <h2 className="mt-5 font-display text-[32px] leading-[1.05]">{sentence(i.name)}</h2>
                <p className="mt-3 text-[15px] leading-relaxed text-silver">{i.question}</p>
                {i.lore && <p className="mt-3 text-[14px] text-mist">{i.lore}</p>}
                {i.example && (
                  <blockquote className="mt-auto break-words border-l-2 border-verdict/50 pl-3 pt-6 text-[14px] text-mist [overflow-wrap:anywhere]">
                    “{i.example}”
                  </blockquote>
                )}
              </SpotlightCard>
            </li>
          ))}
        </ul>
      )}
    </Page>
  );
}
