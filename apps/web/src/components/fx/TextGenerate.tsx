// Pattern after Aceternity "Text Generate Effect": the answer appears word by word.
import { motion, useReducedMotion } from "motion/react";

export function TextGenerate({ text, className }: { text: string; className?: string }) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <p className={className} aria-live="polite">
      {words.map((w, i) => (
        <motion.span
          key={`${i}-${w}`}
          initial={reduce ? false : { opacity: 0, filter: "blur(6px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          transition={{ duration: 0.35, delay: i * 0.035 }}
        >
          {w}{" "}
        </motion.span>
      ))}
    </p>
  );
}
