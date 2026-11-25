import { Link } from "react-router-dom";
import type { GenCard } from "../../lib/api";
import { countdown, cx } from "../../lib/format";
import { useNow } from "../../lib/hooks";

export function LivePill({ gen, compact = false }: { gen: GenCard; compact?: boolean }) {
  const now = useNow();
  const left = gen.dies_at ? new Date(gen.dies_at).getTime() - now : 0;
  return (
    <Link
      to={`/gen/${gen.gen}`}
      className={cx(
        "group inline-flex items-center gap-2.5 rounded-full border border-life/25 bg-life/[0.07] text-[13px] transition-colors hover:border-life/40",
        compact ? "h-9 px-3" : "h-10 px-4",
      )}
    >
      <span className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-life opacity-60" />
        <span className="relative inline-flex size-2 rounded-full bg-life" />
      </span>
      <span className="text-moon">
        {compact ? gen.name : `Gen ${gen.gen} ${gen.name} is alive`}
      </span>
      {left > 0 && (
        <span className={cx("font-mono text-life/90 tabular", compact && "hidden sm:inline")}>
          {compact ? countdown(left) : `dies in ${countdown(left)}`}
        </span>
      )}
    </Link>
  );
}
