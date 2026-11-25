'use client';
import { useEffect } from 'react';

// Boxes that scroll sideways (long API paths on phones) must be reachable by keyboard
// (WCAG 2.1.1). Give any such box without a focusable child a tab stop and a name.
export function ScrollRegions() {
  useEffect(() => {
    const fix = () => {
      document.querySelectorAll<HTMLElement>('#nd-page .overflow-x-auto').forEach((el) => {
        if (el.hasAttribute('tabindex') || el.scrollWidth <= el.clientWidth) return;
        if (el.querySelector('a, button, input, select, textarea, [tabindex]')) return;
        el.tabIndex = 0;
        el.setAttribute('role', 'region');
        el.setAttribute('aria-label', 'Scrollable content');
      });
    };
    fix();
    const obs = new MutationObserver(fix);
    obs.observe(document.body, { childList: true, subtree: true });
    window.addEventListener('resize', fix);
    return () => {
      obs.disconnect();
      window.removeEventListener('resize', fix);
    };
  }, []);
  return null;
}
