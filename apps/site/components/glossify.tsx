import { Children, type ReactNode } from 'react';
import { GLOSSARY } from '@/lib/glossary';
import { Gloss } from './gloss';

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

// One pattern per entry; letters or hyphens on either side mean it's part of a longer word.
const PATTERNS = GLOSSARY.map((e) => ({
  term: e.term,
  re: new RegExp(`(?<![\\w-])(?:${e.match.map(escape).join('|')})(?![\\w-])`, e.exactCase ? '' : 'i'),
}));

/**
 * Wraps the first use of each glossary word on a page in <Gloss>. `seen` is shared by every
 * paragraph, list item and table cell of one page, so a word is marked only once per page.
 */
export function glossify(children: ReactNode, seen: Set<string>): ReactNode {
  let key = 0;
  const out: ReactNode[] = [];
  Children.forEach(children, (child) => {
    if (typeof child !== 'string') {
      out.push(child);
      return;
    }
    let rest = child;
    for (;;) {
      let best: { term: string; index: number; text: string } | undefined;
      for (const p of PATTERNS) {
        if (seen.has(p.term)) continue;
        const m = p.re.exec(rest);
        if (m && (!best || m.index < best.index)) best = { term: p.term, index: m.index, text: m[0] };
      }
      if (!best) break;
      seen.add(best.term);
      if (best.index > 0) out.push(rest.slice(0, best.index));
      out.push(
        <Gloss key={`g${key++}`} term={best.term}>
          {best.text}
        </Gloss>,
      );
      rest = rest.slice(best.index + best.text.length);
    }
    if (rest) out.push(rest);
  });
  return out;
}

/** p, li and td that mark glossary words. Headings, links and code are left alone. */
export function glossComponents(seen: Set<string>) {
  return {
    p: (props: React.ComponentProps<'p'>) => <p {...props}>{glossify(props.children, seen)}</p>,
    li: (props: React.ComponentProps<'li'>) => <li {...props}>{glossify(props.children, seen)}</li>,
    td: (props: React.ComponentProps<'td'>) => <td {...props}>{glossify(props.children, seen)}</td>,
  };
}
