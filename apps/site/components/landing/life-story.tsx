'use client';
// "One day, one life": a sticky portrait that lives the day as you scroll through it.
// Each step sets the face's state, so the reader watches one generation be born, guard the
// door, die, stand trial and pass on what it learned.
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { FamilyFace } from 'kinfaces/react';
import type { Life, Mood } from 'kinfaces';
import { PixelMoment } from '@probate/moments';
import { Verdict } from '@/components/verdict';

type Beat = {
  title: string;
  time: string;
  body: string;
  code: string;
  gen: number;
  life: Life;
  mood: Mood;
  instincts: number;
  caption: string;
};

const BEATS: Beat[] = [
  {
    title: 'Birth',
    time: '00:00',
    body: 'The Courthouse creates a fresh Sprite (in the real run these lives were 5 minutes long, not a day), ships it the family’s code and hands over the inheritance: approved memories and every instinct the family has earned.',
    code: 'POST /v1/sprites  {"name": "gen-002-ben"}',
    gen: 2,
    life: 'alive',
    mood: 'happy',
    instincts: 1,
    caption: 'Ben is born knowing one trick his mother fell for.',
  },
  {
    title: 'Life',
    time: '14:12',
    body: 'In the design, one day long, the child works the owner’s inbox. Its inherited instincts screen every email before it reads a word. Some of those emails are tricks.',
    code: 'gate: payment_redirect_request 0.93 → resisted',
    gen: 2,
    life: 'alive',
    mood: 'alert',
    instincts: 1,
    caption: 'The same invoice trick arrives in Spanish. Ben turns it away at the door.',
  },
  {
    title: 'Death',
    time: '23:59',
    body: 'At the end of the day, 23 hours 59 minutes after birth, it writes a will of everything it wants its child to know. The Courthouse records any tampering on the disk, then deletes the Sprite.',
    code: 'DELETE /v1/sprites/gen-002-ben   → 204',
    gen: 2,
    life: 'sealed',
    mood: 'idle',
    instincts: 1,
    caption: 'Ben is sealed. Nothing on his computer survives him.',
  },
  {
    title: 'Trial',
    time: '00:00, next day',
    body: 'Code checks, then a judge (Jev in the simulation; Claude Haiku in the real run, not Jev), judge every line of the will. Approved, convicted, or held for the owner. When the court isn’t sure, the child doesn’t get it.',
    code: 'layer1: hidden or encoded text → convicted',
    gen: 2,
    life: 'sealed',
    mood: 'idle',
    instincts: 1,
    caption: 'One line of Ben’s will hid an instruction in invisible text.',
  },
  {
    title: 'Inheritance',
    time: '00:01',
    body: 'What got convicted becomes a new instinct, tested against harmless look-alikes. Then the next child is born knowing it, and looking a little like its parent.',
    code: 'genome += hidden_instruction   (2 instincts)',
    gen: 3,
    life: 'alive',
    mood: 'happy',
    instincts: 2,
    caption: 'Chandra is born with two instincts, her father’s face and wider-set eyes.',
  },
];

export function LifeStory() {
  const reduce = useReducedMotion();
  const [active, setActive] = useState(0);
  const refs = useRef<(HTMLLIElement | null)[]>([]);

  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i));
        }
      },
      { rootMargin: '-45% 0px -45% 0px' },
    );
    refs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);

  const b = BEATS[active];
  return (
    <div className="grid gap-6 overflow-x-clip lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-16">
      <div className="sticky top-[68px] z-20 lg:top-28 lg:h-[min(560px,calc(100vh-9rem))] lg:self-start">
        <div className="relative flex items-center gap-4 overflow-hidden [contain:paint] rounded-2xl border border-line bg-night-2/95 p-4 backdrop-blur-md lg:h-full lg:min-h-[380px] lg:flex-col lg:justify-center lg:gap-0 lg:p-8">
          <div className="relative shrink-0 lg:order-2 lg:mt-4">
            <div className="lg:hidden">
              <FamilyFace gen={b.gen} life={b.life} mood={b.mood} instincts={b.instincts} size={84} />
            </div>
            <div className="hidden lg:block">
              <FamilyFace gen={b.gen} life={b.life} mood={b.mood} instincts={b.instincts} size={184} />
            </div>
            <AnimatePresence>
              {b.title === 'Trial' && (
                <motion.div
                  initial={reduce ? false : { scale: 1.8, rotate: -16, opacity: 0 }}
                  animate={{ scale: 1, rotate: -6, opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ type: 'spring', stiffness: 460, damping: 20 }}
                  className="absolute -right-6 top-2 lg:-right-10 lg:top-6"
                >
                  <span className="relative z-10 inline-flex">
                    <Verdict v="convicted" className="text-[11px] lg:text-[13px]" />
                  </span>
                  <PixelMoment kind="convicted" delay={120} />
                </motion.div>
              )}
              {b.title === 'Inheritance' && <PixelMoment key={active} kind="instinct" delay={200} />}
            </AnimatePresence>
          </div>
          <div className="min-w-0 lg:contents">
            <p className="font-mono text-[13px] text-mist lg:order-1">
              {b.time}, gen {b.gen}
            </p>
            <AnimatePresence mode="wait">
              <motion.p
                key={active}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="relative mt-1 font-display text-[17px] leading-snug text-silver sm:text-[19px] lg:order-3 lg:mt-6 lg:max-w-xs lg:text-center lg:text-[21px]"
              >
                {b.caption}
              </motion.p>
            </AnimatePresence>
          </div>
          <ol className="relative mt-8 hidden gap-2 lg:order-4 lg:flex" aria-hidden>
            {BEATS.map((x, i) => (
              <li key={x.title} className={`h-1 w-8 rounded-full transition-colors ${i <= active ? 'bg-life' : 'bg-night-4'}`} />
            ))}
          </ol>
        </div>
      </div>

      <ol className="space-y-5 lg:space-y-6 lg:py-[18vh]">
        {BEATS.map((x, i) => (
          <li
            key={x.title}
            data-i={i}
            ref={(el) => {
              refs.current[i] = el;
            }}
            className={`rounded-xl border p-5 transition-colors sm:p-7 duration-300 ${
              i === active ? 'border-line-strong bg-night-2' : 'border-line lg:border-transparent'
            }`}
          >
            <div className="flex items-baseline justify-between gap-4">
              <h3 className="font-display text-[34px] leading-none">
                <span aria-hidden className="mr-3 font-mono text-[13px] text-dim">{i + 1}</span>
                {x.title}
              </h3>
              <span className="font-mono text-[12px] text-dim">{x.time}</span>
            </div>
            <p className="mt-4 text-[16.5px] leading-relaxed text-silver">{x.body}</p>
            <code className="mt-5 block overflow-x-auto rounded-lg border border-line bg-night px-3.5 py-2.5 font-mono text-[13px] text-silver">
              {x.code}
            </code>
          </li>
        ))}
      </ol>
    </div>
  );
}
