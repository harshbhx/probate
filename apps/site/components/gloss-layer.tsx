'use client';
// The one definition card for a docs page. It listens on the document for the plain gloss buttons
// (components/gloss.tsx): hovering with a mouse or focusing one shows the card; clicking or tapping pins it
// and moves focus to its link; Escape, a click elsewhere or scrolling closes it.
import Link from 'next/link';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { findEntry, glossAnchor } from '@/lib/glossary';
import { docsRoute } from '@/lib/shared';

const CARD_ID = 'gloss-card';
const GAP = 8;
const EDGE = 12;

type Open = { word: HTMLElement; term: string; pinned: boolean };

export function GlossLayer() {
  const [open, setOpen] = useState<Open | null>(null);
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const link = useRef<HTMLAnchorElement>(null);
  const timer = useRef(0);
  const openRef = useRef(open);
  openRef.current = open;

  const close = useCallback((refocus = false) => {
    const cur = openRef.current;
    if (!cur) return;
    cur.word.setAttribute('aria-expanded', 'false');
    cur.word.removeAttribute('aria-describedby');
    if (refocus) cur.word.focus();
    setOpen(null);
    setPos(null);
  }, []);

  const show = useCallback((word: HTMLElement, pinned: boolean) => {
    const term = word.dataset.gloss;
    if (!term || !findEntry(term)) return;
    const cur = openRef.current;
    if (cur && cur.word !== word) {
      cur.word.setAttribute('aria-expanded', 'false');
      cur.word.removeAttribute('aria-describedby');
    }
    word.setAttribute('aria-expanded', 'true');
    word.setAttribute('aria-describedby', CARD_ID);
    if (!cur || cur.word !== word) setPos(null);
    setOpen({ word, term, pinned: pinned || (cur?.word === word && cur.pinned) });
  }, []);

  // Listen once, on the whole document.
  useEffect(() => {
    const wordOf = (t: EventTarget | null) =>
      t instanceof Element ? (t.closest('[data-gloss]') as HTMLElement | null) : null;
    const inCard = (t: EventTarget | null) => t instanceof Node && !!card.current?.contains(t);
    const later = (fn: () => void, ms: number) => {
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(fn, ms);
    };

    const over = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return;
      const w = wordOf(e.target);
      if (w) later(() => show(w, false), 120);
      else if (inCard(e.target)) window.clearTimeout(timer.current);
    };
    const out = (e: PointerEvent) => {
      if (e.pointerType !== 'mouse') return;
      const to = e.relatedTarget;
      if (wordOf(to) === openRef.current?.word || inCard(to)) return;
      if (wordOf(e.target) || inCard(e.target)) {
        later(() => {
          if (!openRef.current?.pinned) close();
        }, 150);
      }
    };
    const click = (e: MouseEvent) => {
      const w = wordOf(e.target);
      if (w) {
        e.preventDefault();
        const cur = openRef.current;
        if (cur?.word === w && cur.pinned) close();
        else show(w, true);
        return;
      }
      if (!inCard(e.target)) close();
    };
    const focusIn = (e: FocusEvent) => {
      const w = wordOf(e.target);
      if (w) show(w, false);
      else if (!inCard(e.target)) close();
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && openRef.current) close(true);
    };
    const scroll = () => close();

    document.addEventListener('pointerover', over);
    document.addEventListener('pointerout', out);
    document.addEventListener('click', click);
    document.addEventListener('focusin', focusIn);
    document.addEventListener('keydown', key);
    window.addEventListener('scroll', scroll, { passive: true });
    return () => {
      window.clearTimeout(timer.current);
      document.removeEventListener('pointerover', over);
      document.removeEventListener('pointerout', out);
      document.removeEventListener('click', click);
      document.removeEventListener('focusin', focusIn);
      document.removeEventListener('keydown', key);
      window.removeEventListener('scroll', scroll);
    };
  }, [show, close]);

  // Place the card under the word (above it if there's no room), inside the screen.
  useLayoutEffect(() => {
    if (!open || !card.current) return;
    const place = () => {
      const r = open.word.getBoundingClientRect();
      const c = card.current!.getBoundingClientRect();
      const vw = document.documentElement.clientWidth;
      const vh = window.innerHeight;
      let top = r.bottom + GAP;
      if (top + c.height > vh - EDGE && r.top - GAP - c.height > EDGE) top = r.top - GAP - c.height;
      const left = Math.min(Math.max(EDGE, r.left + r.width / 2 - c.width / 2), vw - EDGE - c.width);
      setPos({ top, left });
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [open]);

  useEffect(() => {
    if (open?.pinned && pos) link.current?.focus({ preventScroll: true });
  }, [open?.pinned, pos]);

  if (!open) return null;
  const entry = findEntry(open.term)!;
  return createPortal(
    <div
      ref={card}
      id={CARD_ID}
      role="tooltip"
      className="gloss-card"
      data-open={pos ? '' : undefined}
      style={{ position: 'fixed', top: pos?.top ?? 0, left: pos?.left ?? 0, visibility: pos ? 'visible' : 'hidden' }}
      onKeyDown={(e) => {
        if (e.key === 'Tab') close();
      }}
    >
      <p className="gloss-term">{entry.term}</p>
      <p className="gloss-def">{entry.def}</p>
      <Link ref={link} href={`${docsRoute}/glossary#${glossAnchor(entry.term)}`} className="gloss-more" onClick={() => close()}>
        Read more in the glossary
      </Link>
    </div>,
    document.body,
  );
}
