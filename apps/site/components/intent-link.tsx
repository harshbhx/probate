'use client';
// A next/link that does not prefetch on its own. Next prefetches every link that scrolls into view, which on the
// landing page means downloading the docs shell (about 150 KB of script) right after load, for a click that may
// never come. This one warms the destination when the pointer, a finger or the keyboard arrives at the link.
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type { ComponentProps } from 'react';

export default function IntentLink({ onPointerEnter, onFocus, onTouchStart, ...props }: ComponentProps<typeof Link>) {
  const router = useRouter();
  const warm = () => {
    if (typeof props.href === 'string' && props.href.startsWith('/')) router.prefetch(props.href);
  };
  return (
    <Link
      {...props}
      prefetch={false}
      onPointerEnter={(e) => {
        warm();
        onPointerEnter?.(e);
      }}
      onFocus={(e) => {
        warm();
        onFocus?.(e);
      }}
      onTouchStart={(e) => {
        warm();
        onTouchStart?.(e);
      }}
    />
  );
}
