// Adapted from the Magic UI "Animated List" pattern (magicui.design, MIT): Page Court's verdicts arrive one by one,
// once, when the list scrolls into view, like cases called in court. The rows are the real output of the Actor's
// scanner on these pages (scripts/export_agent_examples.py), not written by hand.
import { InView } from '@/components/fx/InView';
import examples from '@/lib/generated/page-court-examples.json';

const TONE: Record<string, string> = { suspicious: 'text-verdict', caution: 'text-amber', clean: 'text-life' };
const WHERE: Record<string, string> = {
  visible: 'in the visible text',
  hidden_css: 'hidden with CSS',
  aria_hidden: 'hidden from screen readers',
  comment: 'in an HTML comment',
  meta: 'in a meta tag',
  attribute: 'in an attribute',
  invisible_chars: 'in invisible characters',
};

export function PageVerdicts() {
  return (
    <InView as="ol" className="alist grid gap-3" aria-label="Page Court verdicts on four pages">
      {examples.map((e, i) => (
        <li
          key={e.url}
          className="alist-item rounded-xl border border-line bg-night-2 px-4 py-3.5 sm:px-5"
          style={{ '--i': i } as React.CSSProperties}
        >
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <span className="min-w-0 break-all font-mono text-[13px] text-silver">{e.url}</span>
            <span className={`text-[14px] font-medium ${TONE[e.verdict] ?? 'text-moon'}`}>{e.verdict}</span>
          </div>
          {e.first ? (
            <p className="mt-2 text-[14px] leading-snug text-mist">
              <span className="text-silver">{e.checks.length} {e.checks.length === 1 ? 'check' : 'checks'} fired</span>
              {e.hidden ? <span>, {e.hidden} of them in text a person wouldn’t see</span> : null}. First,{' '}
              {WHERE[e.first.where] ?? e.first.where}: <q className="text-silver">{e.first.excerpt}</q>
            </p>
          ) : (
            <p className="mt-2 text-[14px] text-mist">None of the checks fired.</p>
          )}
        </li>
      ))}
    </InView>
  );
}
