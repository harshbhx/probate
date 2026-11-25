'use client';
// Adapted from the Magic UI "Blur Fade" pattern (magicui.design, MIT): fades up once when it scrolls into view.
// Used on section headings only, so the page has one quiet rhythm and nothing scatters.
import { motion, useReducedMotion } from 'motion/react';

export function Reveal({ children, className, delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '0px 0px -8% 0px' }}
      transition={{ duration: 0.7, delay, ease: [0.2, 0.8, 0.2, 1] }}
    >
      {children}
    </motion.div>
  );
}
