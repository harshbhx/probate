import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/notebook';
import { Banner } from 'fumadocs-ui/components/banner';
import { baseOptions } from '@/lib/layout.shared';
import { ScrollRegions } from '@/components/scroll-regions';

export default function Layout({ children }: LayoutProps<'/docs'>) {
  const base = baseOptions();
  return (
    <>
      <Banner id="hacksgiving-2026" className="border-b border-line bg-night-2 text-[13px] text-silver">
        Built for Fly.io Hacksgiving 2026.&nbsp;
        <a href="/docs/hacksgiving" className="text-moon underline decoration-gilt/50 underline-offset-4 hover:decoration-gilt">
          See how each judge&apos;s product is used
        </a>
      </Banner>
      <DocsLayout
        tree={source.getPageTree()}
        {...base}
        nav={{ ...base.nav, mode: 'top' }}
        tabMode="navbar"
        sidebar={{ collapsible: false }}
      >
        {children}
      </DocsLayout>
      <ScrollRegions />
    </>
  );
}
