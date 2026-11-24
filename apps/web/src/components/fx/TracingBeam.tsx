// Pattern after Aceternity "Tracing Beam": a line that fills as you scroll through the steps.
import { type ReactNode, useRef } from "react";
import { motion, useScroll, useSpring, useTransform } from "motion/react";

export function TracingBeam({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 70%", "end 60%"] });
  const fill = useSpring(useTransform(scrollYProgress, [0, 1], [0, 1]), { stiffness: 120, damping: 30 });
  return (
    <div ref={ref} className="relative min-w-0 pl-10 md:pl-14">
      <div aria-hidden className="absolute left-3 top-2 bottom-2 w-px bg-line md:left-5" />
      <motion.div
        aria-hidden
        className="absolute left-3 top-2 w-px origin-top md:left-5"
        style={{
          scaleY: fill,
          bottom: 8,
          background: "linear-gradient(to bottom, var(--color-life), var(--color-gilt) 70%, transparent)",
        }}
      />
      {children}
    </div>
  );
}
