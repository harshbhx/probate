// Pattern after Magic UI "NumberTicker": counts up with a spring when it scrolls into view.
import { useEffect } from "react";
import { animate, useMotionValue, useReducedMotion, useTransform, motion } from "motion/react";
import { useInView } from "../../lib/hooks";

type Props = { value: number; decimals?: number; suffix?: string; className?: string; duration?: number };

export function NumberTicker({ value, decimals = 0, suffix = "", className, duration = 1.4 }: Props) {
  const reduce = useReducedMotion();
  const mv = useMotionValue(reduce ? value : 0);
  const text = useTransform(mv, (v) => `${v.toFixed(decimals)}${suffix}`);
  const { ref, inView } = useInView<HTMLSpanElement>();

  useEffect(() => {
    if (!inView) return;
    if (reduce) {
      mv.set(value);
      return;
    }
    const controls = animate(mv, value, { duration, ease: [0.16, 1, 0.3, 1] });
    return () => controls.stop();
  }, [inView, value, reduce, duration, mv]);

  return (
    <span ref={ref} className={className}>
      <motion.span className="tabular">{text}</motion.span>
    </span>
  );
}
