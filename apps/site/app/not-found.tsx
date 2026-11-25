import Link from 'next/link';
import { FamilyFace } from 'kinfaces/react';
import { SiteFooter } from '@/components/chrome/site-footer';
import { SiteHeader } from '@/components/chrome/site-header';

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main id="content" className="flex flex-1 flex-col items-center justify-center px-6 py-28 text-center">
        <FamilyFace gen={3} life="alive" mood="fooled" size={120} title="A fooled generation" />
        <h1 className="mt-8 font-display text-display-md font-[420] sm:text-display-lg">Not in the register</h1>
        <p className="mt-3 max-w-md text-body text-mist">There’s no generation, page or doc at this address.</p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Link href="/" className="inline-flex h-11 items-center rounded-lg bg-moon px-5 text-[15px] font-medium text-night hover:bg-white">
            Go to the family
          </Link>
          <Link href="/docs" className="inline-flex h-11 items-center rounded-lg border border-line-strong bg-night-2 px-5 text-[15px] hover:bg-night-3">
            Read the docs
          </Link>
        </div>
      </main>
      <SiteFooter />
    </>
  );
}
