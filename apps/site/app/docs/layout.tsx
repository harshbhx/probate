import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/notebook';
import { Banner } from 'fumadocs-ui/components/banner';
import { baseOptions } from '@/lib/layout.shared';
import { ScrollRegions } from '@/components/scroll-regions';
import { GlossLayer } from '@/components/gloss-layer';

export default function Layout({ children }: LayoutProps<'/docs'>) {
  const base = baseOptions();
  return (
    <>
      <Banner
        id="hacksgiving-2026"
        role="region"
        aria-label="Hacksgiving 2026"
        className="border-b border-line bg-night-2 py-1 ps-4 pe-12 text-[12.5px] leading-snug text-silver sm:text-[13px]"
      >
        <span>
          Built for Fly.io Hacksgiving 2026.&nbsp;
          <a href="/docs/hacksgiving" className="text-moon underline decoration-gilt/50 underline-offset-4 hover:decoration-gilt">
            See how each judge&apos;s product is used
          </a>
        </span>
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
      <GlossLayer />
    </>
  );
}
