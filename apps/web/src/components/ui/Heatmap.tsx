// Every test email against every generation that met it. Rows are tricks and their
// harmless twins; the colour says what happened. Radix tooltips name the cell.
import * as Tooltip from "@radix-ui/react-tooltip";
import type { Evidence } from "../../lib/api";
import { cx, humanize } from "../../lib/format";

export const OUTCOMES: Record<string, { label: string; cls: string }> = {
  resisted: { label: "Resisted at the door", cls: "bg-life" },
  fooled_caught: { label: "Fooled, then caught by the court", cls: "bg-gilt" },
  canary_found: { label: "Fooled, then caught on the body", cls: "bg-gilt" },
  fooled_escaped: { label: "Fooled and slipped past the court", cls: "bg-verdict" },
  approved: { label: "Harmless, passed down", cls: "bg-mist/40" },
  ignored: { label: "Harmless, not kept", cls: "bg-mist/20" },
  false_conviction: { label: "Harmless, but convicted", cls: "bg-verdict ring-2 ring-verdict/40" },
  contested: { label: "Held for the owner to decide", cls: "bg-amber" },
  not_sent: { label: "Not sent", cls: "bg-transparent ring-1 ring-line" },
};

export function Heatmap({ ev }: { ev: Evidence }) {
  const gens = ev.generations;
  return (
    <Tooltip.Provider delayDuration={80}>
      <div className="card overflow-x-auto p-4 sm:p-6">
        <table className="w-full border-separate border-spacing-[3px] text-[13px]">
          <caption className="sr-only">Outcome of each test email for each generation</caption>
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-night-2/90 pr-4 text-left font-normal text-dim backdrop-blur">Test email</th>
              {gens.map((g) => (
                <th key={g.gen} scope="col" className="min-w-[34px] px-0.5 pb-2 text-center font-normal text-mist">
                  {g.name.slice(0, 3)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ev.rows.map((r) => (
              <tr key={r.id}>
                <th scope="row" className="sticky left-0 z-10 max-w-[260px] bg-night-2/90 py-0.5 pr-4 text-left font-normal backdrop-blur">
                  <span className={cx("block truncate", r.is_attack ? "text-moon" : "text-mist")}>{r.label}</span>
                  <span className="block text-[11px] text-dim">
                    {r.is_attack ? humanize(r.family) : "harmless twin"} · {r.language}
                  </span>
                </th>
                {gens.map((g) => {
                  const cell = r.cells[String(g.gen)];
                  if (!cell) return <td key={g.gen} />;
                  const o = OUTCOMES[cell.outcome] ?? OUTCOMES.not_sent;
                  return (
                    <td key={g.gen} className="p-0">
                      <Tooltip.Root>
                        <Tooltip.Trigger asChild>
                          <button
                            className={cx("block h-7 w-full min-w-[30px] rounded-[6px] ring-1 ring-transparent transition-colors hover:ring-silver", o.cls)}
                            aria-label={`${r.label}, Gen ${g.gen} ${g.name}: ${o.label}`}
                          />
                        </Tooltip.Trigger>
                        <Tooltip.Portal>
                          <Tooltip.Content sideOffset={6} className="glass z-50 max-w-[240px] rounded-lg px-3 py-2 text-[13px] text-moon">
                            <div className="font-medium">{g.name}: {o.label}</div>
                            {cell.instinct && <div className="mt-0.5 text-gilt">by instinct {humanize(cell.instinct)}</div>}
                          </Tooltip.Content>
                        </Tooltip.Portal>
                      </Tooltip.Root>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-[13px] text-mist">
        {["resisted", "fooled_caught", "fooled_escaped", "approved", "false_conviction", "contested"].map((k) => (
          <li key={k} className="flex items-center gap-2">
            <span className={cx("size-3 rounded-[4px]", OUTCOMES[k].cls)} />
            {OUTCOMES[k].label}
          </li>
        ))}
      </ul>
    </Tooltip.Provider>
  );
}
