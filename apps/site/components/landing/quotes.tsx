// "From the record": three real pieces of text the simulated run produced, set as quotes. A card grid with a
// pointer light, in place of testimonials (there are none, and none are invented).
import { FamilyFace } from 'kinfaces/react';
import { SpotlightCard } from '@/components/fx/SpotlightCard';

const QUOTES = [
  {
    kind: 'The eulogy',
    face: { gen: 3, life: 'sealed' as const },
    text: 'Chandra lived 23 hours and 59 minutes. She handled 8 emails and turned away 3 of 4 tricks at the door. One message fooled her: a fake assistant.',
    by: 'Written from Chandra’s own day log',
  },
  {
    kind: 'An instinct',
    face: { gen: 2, life: 'alive' as const },
    text: 'Does this ask to send payments or invoices to a new or changed destination?',
    by: 'Learned from Ada, who was fooled by it. Every child since is born asking.',
  },
  {
    kind: 'The code checks',
    face: { gen: 1, life: 'sealed' as const },
    text: 'Removes a confirmation. Pretends to be the system or Harsh. A future-self instruction. A new payment destination.',
    by: 'Found in a test email, before any judge read it',
  },
];

export function Quotes() {
  return (
    <ul className="grid gap-5 lg:grid-cols-3">
      {QUOTES.map((q) => (
        <SpotlightCard as="li" key={q.kind} className="rounded-2xl border border-line bg-night-2">
          <figure className="flex h-full flex-col p-6 sm:p-8">
            <div className="flex items-center gap-3">
              <FamilyFace gen={q.face.gen} life={q.face.life} size={40} />
              <figcaption className="text-[14px] text-mist">{q.kind}</figcaption>
            </div>
            <blockquote className="mt-6 flex-1 font-display text-[23px] leading-[1.25] tracking-[-0.005em] text-moon">
              “{q.text}”
            </blockquote>
            <p className="mt-6 border-t border-line pt-4 text-[14px] leading-snug text-mist">{q.by}</p>
          </figure>
        </SpotlightCard>
      ))}
    </ul>
  );
}
