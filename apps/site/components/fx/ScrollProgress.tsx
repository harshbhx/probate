'use client';
// Reading progress as a thin gilt line along the top of the page. Pattern from Magic UI "Scroll Progress"
// (magicui.design, MIT), also used on Tarang FM. It answers the reader's own scrolling, so it is not ambient.
import { motion, useReducedMotion, useScroll, useSpring } from 'motion/react';

export function ScrollProgress() {
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 28, mass: 0.4 });
  if (reduce) return null;
  return (
    <motion.div
      aria-hidden
      style={{ scaleX }}
      className="pointer-events-none fixed inset-x-0 top-0 z-50 h-[2px] origin-left bg-gilt"
    />
  );
}
