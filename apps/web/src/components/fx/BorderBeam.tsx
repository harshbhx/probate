// Pattern after Magic UI "BorderBeam": a short beam of light travels around the border.
// Used only on the living generation, so life is the one thing that moves on its own.
export function BorderBeam({ size = 90, color = "var(--color-life)" }: { size?: number; color?: string }) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 rounded-[inherit] [mask-clip:padding-box,border-box] [mask-composite:intersect] [mask-image:linear-gradient(transparent,transparent),linear-gradient(#000,#000)] border border-transparent"
    >
      <div
        className="absolute aspect-square animate-[var(--animate-border-beam)]"
        style={{
          width: size,
          offsetPath: "rect(0 auto auto 0 round 20px)",
          background: `linear-gradient(to left, ${color}, transparent)`,
        }}
      />
    </div>
  );
}
