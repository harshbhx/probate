import Link from 'next/link';
import { FamilyFace } from '@probate/faces';

export default function NotFound() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center px-6 py-32 text-center">
      <FamilyFace gen={3} life="alive" mood="fooled" size={120} />
      <h1 className="mt-8 font-display text-[44px] leading-tight sm:text-[56px]">Not in the register</h1>
      <p className="mt-3 max-w-md text-[16px] text-mist">There’s no generation, page or doc at this address.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        <Link href="/" className="inline-flex h-11 items-center rounded-xl bg-moon px-5 text-[15px] font-medium text-night">
          Go to the family
        </Link>
        <Link href="/docs" className="inline-flex h-11 items-center rounded-xl px-5 text-[15px] ring-1 ring-line-strong hover:bg-white/5">
          Read the docs
        </Link>
      </div>
    </main>
  );
}
