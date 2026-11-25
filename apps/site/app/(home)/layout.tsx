import Link from 'next/link';
import { SiteFooter } from '@/components/chrome/site-footer';
import { SiteHeader } from '@/components/chrome/site-header';

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <>
      <div className="border-b border-line bg-night-2 text-[13px] text-mist">
        <p className="mx-auto max-w-6xl px-5 py-2.5 text-center sm:px-6">
          <span className="hidden sm:inline">Probate is an entry in Fly.io Hacksgiving 2026.</span>
          <span className="sm:hidden">A Hacksgiving 2026 entry.</span>{' '}
          <Link href="/docs/architecture/sprites" className="text-moon underline decoration-gilt/50 underline-offset-[3px] hover:decoration-gilt">
            See how it uses Sprites
          </Link>
        </p>
      </div>
      <SiteHeader />
      <main id="content" className="flex flex-1 flex-col">
        {children}
      </main>
      <SiteFooter />
    </>
  );
}
