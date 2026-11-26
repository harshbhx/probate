'use client';
import { RootProvider } from 'fumadocs-ui/provider/next';
import { DocsIntentLink } from '@/components/intent-link';
import { lazy, useState, type ComponentProps, type ReactNode } from 'react';

const LazySearchDialog = lazy(() => import('@/components/search'));

// The search index and dialog (about 110 KB) are fetched the first time someone opens search, not with every page.
function SearchDialog(props: ComponentProps<typeof LazySearchDialog>) {
  const [wanted, setWanted] = useState(false);
  if (props.open && !wanted) setWanted(true);
  return wanted ? <LazySearchDialog {...props} /> : null;
}

export function Provider({ children }: { children: ReactNode }) {
  return (
    <RootProvider
      // Docs links prefetch when a pointer, finger or the keyboard arrives, not when they scroll into view:
      // the sidebar alone would otherwise fetch and parse about twenty pages during load.
      components={{ Link: DocsIntentLink }}
      search={{ SearchDialog }}
      theme={{ forcedTheme: 'dark', defaultTheme: 'dark', enableSystem: false }}
    >
      {children}
    </RootProvider>
  );
}
