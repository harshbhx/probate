'use client';
import { RootProvider } from 'fumadocs-ui/provider/next';
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
      search={{ SearchDialog }}
      theme={{ forcedTheme: 'dark', defaultTheme: 'dark', enableSystem: false }}
    >
      {children}
    </RootProvider>
  );
}
