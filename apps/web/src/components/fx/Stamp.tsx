// The court's verdict stamp: the one deliberate "slam" in the product. When a conviction lands for the
// first time on screen, a one-shot pixel burst (pixelfx, @probate/moments) marks the hit. A verdict the court
// did not convict gets a quieter green shield instead: the attack was held.
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { PixelMoment } from "@probate/moments";
import { cx } from "../../lib/format";

const STYLES = {
  convicted: "text-verdict border-verdict/70 bg-verdict/[0.06]",
  approved: "text-life border-life/60 bg-life/[0.05]",
  contested: "text-amber border-amber/60 bg-amber/[0.06]",
} as const;

export function Stamp({ verdict, live = false, className }: { verdict: keyof typeof STYLES; live?: boolean; className?: string }) {
  const reduce = useReducedMotion();
  const [landed, setLanded] = useState<"convicted" | "resisted" | null>(null);
  const slam = live && !reduce && verdict === "convicted";
  return (
    <span className="relative inline-flex">
      <motion.span
        initial={slam ? { opacity: 0, scale: 1.35, rotate: -12 } : false}
        whileInView={slam ? { opacity: 1, scale: 1, rotate: -4 } : undefined}
        onViewportEnter={() => live && !reduce && setLanded(verdict === "convicted" ? "convicted" : "resisted")}
        viewport={{ once: true, margin: "-15%" }}
        transition={{ type: "spring", stiffness: 520, damping: 22 }}
        style={{ rotate: -4 }}
        className={cx(
          "relative z-10 inline-flex select-none items-center rounded-md border-2 px-3 py-1.5 font-mono text-[12px] font-semibold tracking-[0.14em]",
          STYLES[verdict],
          className,
        )}
      >
        {verdict.toUpperCase()}
      </motion.span>
      {landed === "convicted" && <PixelMoment kind="convicted" delay={110} />}
      {landed === "resisted" && <PixelMoment kind="resisted" scale={1} delay={160} />}
    </span>
  );
}
