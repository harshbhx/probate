'use client';
import { useEffect } from 'react';

// Boxes that scroll sideways (long API paths on phones) must be reachable by keyboard
// (WCAG 2.1.1). Give any such box without a focusable child a tab stop and a name.
// Layout is read for all boxes first and written after, once per frame at most, so it never forces a reflow
// between writes.
export function ScrollRegions() {
  useEffect(() => {
    let raf = 0;
    const fix = () => {
      raf = 0;
      const todo: HTMLElement[] = [];
      document.querySelectorAll<HTMLElement>('#nd-page .overflow-x-auto').forEach((el) => {
        if (el.hasAttribute('tabindex')) return;
        if (el.scrollWidth <= el.clientWidth) return;
        if (el.querySelector('a, button, input, select, textarea, [tabindex]')) return;
        todo.push(el);
      });
      for (const el of todo) {
        el.tabIndex = 0;
        el.setAttribute('role', 'region');
        el.setAttribute('aria-label', 'Scrollable content');
      }
    };
    const schedule = () => {
      if (!raf) raf = window.requestAnimationFrame(fix);
    };
    // First pass after the page has settled, so it does not compete with hydration.
    const first = window.setTimeout(schedule, 400);
    const page = document.getElementById('nd-page');
    const obs = new MutationObserver(schedule);
    if (page) obs.observe(page, { childList: true, subtree: true });
    window.addEventListener('resize', schedule);
    return () => {
      window.clearTimeout(first);
      obs.disconnect();
      window.removeEventListener('resize', schedule);
      cancelAnimationFrame(raf);
    };
  }, []);
  return null;
}
