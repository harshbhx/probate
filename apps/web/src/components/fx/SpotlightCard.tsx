// Pattern after Aceternity "Card Spotlight" / React Bits "SpotlightCard":
// a soft light follows the pointer across the card surface.
import { type ReactNode, useRef } from "react";
import { cx } from "../../lib/format";

type Props = { children: ReactNode; className?: string; color?: string; as?: "div" | "article" | "li" };

export function SpotlightCard({ children, className, color = "rgb(91 227 169 / 0.10)", as = "div" }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const Tag = as as "div";
  return (
    <Tag
      ref={ref}
      onPointerMove={(e) => {
        const el = ref.current;
        if (!el) return;
        const r = el.getBoundingClientRect();
        el.style.setProperty("--mx", `${e.clientX - r.left}px`);
        el.style.setProperty("--my", `${e.clientY - r.top}px`);
      }}
      className={cx("card group relative overflow-hidden", className)}
      style={{ ["--spot" as string]: color }}
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{ background: "radial-gradient(360px circle at var(--mx) var(--my), var(--spot), transparent 60%)" }}
      />
      <div className="relative">{children}</div>
    </Tag>
  );
}
