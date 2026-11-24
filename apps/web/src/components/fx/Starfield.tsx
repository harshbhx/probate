// Pattern after Aceternity "Stars Background" / React Bits "Particles": a quiet night sky.
// Few stars, slow twinkle, paused when the tab is hidden or motion is reduced.
import { useEffect, useRef } from "react";

export function Starfield({ density = 0.00012, className }: { density?: number; className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let stars: { x: number; y: number; r: number; p: number; s: number }[] = [];

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      const { width, height } = canvas.getBoundingClientRect();
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const n = Math.floor(width * height * density);
      stars = Array.from({ length: n }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 1.1 + 0.2,
        p: Math.random() * Math.PI * 2,
        s: 0.4 + Math.random() * 0.8,
      }));
    };

    const draw = (t: number) => {
      const { width, height } = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, width, height);
      for (const st of stars) {
        const a = reduce ? 0.55 : 0.25 + 0.45 * (0.5 + 0.5 * Math.sin(st.p + (t / 1000) * st.s));
        ctx.beginPath();
        ctx.arc(st.x, st.y, st.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(232, 236, 244, ${a})`;
        ctx.fill();
      }
      if (!reduce && !document.hidden) raf = requestAnimationFrame(draw);
    };

    resize();
    raf = requestAnimationFrame(draw);
    const onVis = () => {
      if (!document.hidden) raf = requestAnimationFrame(draw);
    };
    window.addEventListener("resize", resize);
    document.addEventListener("visibilitychange", onVis);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [density]);

  return <canvas ref={ref} aria-hidden className={className ?? "pointer-events-none absolute inset-0 h-full w-full"} />;
}
