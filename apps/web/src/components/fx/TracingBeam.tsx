// A still hairline that joins the steps of a sequence. (unslop: nothing moves on scroll.)
import type { ReactNode } from "react";

export function TracingBeam({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-w-0 pl-10 md:pl-14">
      <div aria-hidden className="absolute bottom-2 left-3 top-2 w-px bg-line-strong md:left-5" />
      {children}
    </div>
  );
}
