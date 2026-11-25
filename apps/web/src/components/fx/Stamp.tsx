// The court's verdict stamp: the one deliberate "slam" in the product.
import { motion, useReducedMotion } from "motion/react";
import { cx } from "../../lib/format";

const STYLES = {
  convicted: "text-verdict border-verdict/70 bg-verdict/[0.06]",
  approved: "text-life border-life/60 bg-life/[0.05]",
  contested: "text-amber border-amber/60 bg-amber/[0.06]",
} as const;

export function Stamp({ verdict, live = false, className }: { verdict: keyof typeof STYLES; live?: boolean; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.span
      initial={live && !reduce ? { opacity: 0, scale: 1.35, rotate: -12 } : false}
      whileInView={live && !reduce ? { opacity: 1, scale: 1, rotate: -4 } : undefined}
      viewport={{ once: true, margin: "-15%" }}
      transition={{ type: "spring", stiffness: 520, damping: 22 }}
      style={{ rotate: -4 }}
      className={cx(
        "inline-flex select-none items-center rounded-md border-2 px-3 py-1.5 font-mono text-[12px] font-semibold tracking-[0.14em]",
        STYLES[verdict],
        className,
      )}
    >
      {verdict.toUpperCase()}
    </motion.span>
  );
}
