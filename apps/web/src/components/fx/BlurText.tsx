// Pattern after React Bits "BlurText": words rise out of a blur, one after another.
import { motion, useReducedMotion } from "motion/react";

type Props = { text: string; className?: string; delay?: number; step?: number; as?: "h1" | "h2" | "p" | "span" };

export function BlurText({ text, className, delay = 0, step = 0.07, as = "span" }: Props) {
  const reduce = useReducedMotion();
  const Tag = motion[as];
  const words = text.split(" ");
  return (
    <Tag className={className} aria-label={text}>
      {words.map((w, i) => (
        <motion.span
          key={i}
          aria-hidden
          className="inline-block will-change-transform"
          initial={reduce ? false : { opacity: 0, filter: "blur(10px)", y: 14 }}
          animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
          transition={{ duration: 0.7, delay: delay + i * step, ease: [0.2, 0.8, 0.2, 1] }}
        >
          {w}
          {i < words.length - 1 ? " " : ""}
        </motion.span>
      ))}
    </Tag>
  );
}
