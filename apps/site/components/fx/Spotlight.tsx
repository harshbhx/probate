// The courtroom lamp: a soft cone of gilt light falling from above the hero. Pattern after Aceternity UI
// "Spotlight" (ui.aceternity.com, MIT), rebuilt as two CSS gradients so it costs nothing and never moves.
export function Spotlight({ className = '' }: { className?: string }) {
  return (
    <div aria-hidden className={`pointer-events-none absolute inset-x-0 top-0 overflow-hidden ${className}`}>
      <div
        className="relative left-1/2 h-[620px] w-[1100px] max-w-none -translate-x-1/2 opacity-90"
        style={{
          background:
            'radial-gradient(ellipse 38% 62% at 50% 0%, rgb(217 180 106 / 0.20), transparent 70%), radial-gradient(ellipse 70% 40% at 50% 0%, rgb(237 239 243 / 0.06), transparent 75%)',
          maskImage: 'linear-gradient(to bottom, black 40%, transparent)',
          WebkitMaskImage: 'linear-gradient(to bottom, black 40%, transparent)',
        }}
      />
    </div>
  );
}
