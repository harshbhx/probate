import Link from '@/components/intent-link';
import { SiteFooter } from '@/components/chrome/site-footer';
import { ScrollProgress } from '@/components/fx/ScrollProgress';
import { SiteHeader } from '@/components/chrome/site-header';

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <>
      <aside aria-label="Hacksgiving 2026" className="border-b border-line bg-night-2 text-[13px] text-mist">
        <p className="mx-auto max-w-6xl px-5 py-2.5 text-center sm:px-6">
          <span className="hidden sm:inline">Probate is an entry in Fly.io Hacksgiving 2026.</span>
          <span className="sm:hidden">A Hacksgiving 2026 entry.</span>{' '}
          <Link href="/docs/architecture/sprites" className="text-moon underline decoration-gilt/50 underline-offset-[3px] hover:decoration-gilt">
            See how it uses Sprites
          </Link>
        </p>
      </aside>
      <ScrollProgress />
      <SiteHeader />
      <main id="content" className="flex flex-1 flex-col">
        {children}
      </main>
      <SiteFooter />
    </>
  );
}
