import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';
import { Seal } from '@/components/seal';
import { githubUrl, liveUrl } from './shared';

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: (
        <span className="flex items-center gap-2.5">
          <Seal size={26} />
          <span className="font-display text-[22px] leading-none tracking-tight">Probate</span>
        </span>
      ),
    },
    themeSwitch: { enabled: false },
    githubUrl: githubUrl || undefined,
    links: [
      { text: 'Docs', url: '/docs', active: 'nested-url' },
      ...(liveUrl ? [{ text: 'Live family', url: liveUrl, external: true }] : []),
    ],
  };
}
