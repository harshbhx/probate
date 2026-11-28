// "See it live on the Sprite": the read-only public demo of the Courthouse. The address is demoUrl in lib/shared.ts
// (NEXT_PUBLIC_LIVE_URL when the build sets it).
import { ArrowUpRight, Radio } from 'lucide-react';
import { cn } from '@/lib/cn';
import { demoUrl } from '@/lib/shared';

export function SeeItLive({ className, hint = true, primary = false }: { className?: string; hint?: boolean; primary?: boolean }) {
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <a
        href={demoUrl}
        target="_blank"
        rel="noreferrer"
        className={cn(
          'inline-flex h-12 w-full items-center justify-center gap-2 rounded-lg border px-6 text-[16px] font-medium transition-colors sm:w-auto sm:self-start',
          primary
            ? 'border-transparent bg-moon text-night hover:bg-white'
            : 'border-life/40 bg-life/[0.08] text-moon hover:border-life/70 hover:bg-life/[0.14]',
        )}
      >
        <Radio size={17} aria-hidden className={primary ? undefined : 'text-life'} />
        See it live on the Sprite
        <ArrowUpRight size={16} aria-hidden />
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
      {hint && (
        <p className="text-[13px] leading-snug text-mist">
          A read-only public demo with 49 generations. If its Sprite is asleep it wakes in a moment: give it a few seconds.
        </p>
      )}
    </div>
  );
}
