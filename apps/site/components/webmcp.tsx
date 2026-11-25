'use client';
// Offers Probate's WebMCP tools (lib/webmcp-tools.ts) to an AI agent in the visitor's browser. Browsers without
// WebMCP never load the tools.
import { useEffect } from 'react';

export function WebMCP() {
  useEffect(() => {
    const mc = (navigator as Navigator & { modelContext?: unknown }).modelContext;
    if (!mc) return;
    let undo: (() => void) | undefined;
    let gone = false;
    import('@/lib/webmcp-tools').then(({ registerProbateTools }) => {
      if (!gone) undo = registerProbateTools(mc as Parameters<typeof registerProbateTools>[0]);
    });
    return () => {
      gone = true;
      undo?.();
    };
  }, []);
  return null;
}
