// Family faces for the docs: a single face, or a strip of the family with the living child last.
import { FamilyFace } from 'kinfaces/react';
import { inheritedChange, type Life, type Mood } from 'kinfaces';

export function Face({ gen = 1, life = 'alive', mood = 'idle', instincts = 0, size = 72, label }: {
  gen?: number;
  life?: Life;
  mood?: Mood;
  instincts?: number;
  size?: number;
  label?: string;
}) {
  return (
    <figure className="not-prose inline-flex flex-col items-center gap-2 align-top">
      <FamilyFace gen={gen} life={life} mood={mood} instincts={instincts} size={size} title={label} />
      {label && <figcaption className="text-center text-[12.5px] text-fd-muted-foreground">{label}</figcaption>}
    </figure>
  );
}

const NAMES = ['Ada', 'Ben', 'Chandra', 'Dara', 'Emeka', 'Farah', 'Grace'];

export function FamilyStrip({ count = 7 }: { count?: number }) {
  const n = Math.min(count, NAMES.length);
  return (
    <figure tabIndex={0} aria-label="The family, oldest to youngest" className="not-prose my-6 overflow-x-auto rounded-2xl border border-fd-border bg-fd-card p-5">
      <ol className="flex min-w-max items-end gap-5">
        {NAMES.slice(0, n).map((name, i) => {
          const alive = i === n - 1;
          const change = inheritedChange(i + 1);
          return (
            <li key={name} className="flex w-[84px] flex-col items-center text-center">
              <FamilyFace gen={i + 1} life={alive ? 'alive' : 'sealed'} instincts={Math.min(i, 3)} size={alive ? 64 : 52} track={alive} />
              <span className={`mt-2 text-[14px] ${alive ? 'text-[var(--color-life)]' : 'text-fd-foreground'}`}>{name}</span>
              <span className="mt-0.5 text-[11.5px] leading-tight text-fd-muted-foreground">{change ?? 'the founder'}</span>
            </li>
          );
        })}
      </ol>
      <figcaption className="mt-4 text-[13px] text-fd-muted-foreground">
        Every generation gets a face. Each child copies its parent and changes one thing. Gold diamonds are the instincts it was born
        with.
      </figcaption>
    </figure>
  );
}
