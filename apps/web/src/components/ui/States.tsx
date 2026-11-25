import { Link } from "react-router-dom";
import { cx } from "../../lib/format";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cx("rounded-xl bg-night-2 motion-safe:animate-pulse", className)} />;
}

export function PageSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading">
      <Skeleton className="h-12 w-2/3" />
      <Skeleton className="h-5 w-1/2" />
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
        <Skeleton className="h-44" />
      </div>
    </div>
  );
}

export function Empty({ title, children, action }: { title: string; children: React.ReactNode; action?: { to: string; label: string } }) {
  return (
    <div className="card max-w-xl p-8">
      <h2 className="font-display text-3xl">{title}</h2>
      <p className="mt-3 text-mist">{children}</p>
      {action && (
        <Link to={action.to} className="mt-6 inline-flex h-11 items-center rounded-lg bg-moon px-5 text-[15px] font-medium text-night">
          {action.label}
        </Link>
      )}
    </div>
  );
}

export function ErrorState({ status }: { status?: number }) {
  if (status === 404) {
    return (
      <Empty title="Not in the register" action={{ to: "/", label: "Go to the family" }}>
        There's no generation, trial or page at this address.
      </Empty>
    );
  }
  return (
    <Empty title="The Courthouse tripped" action={{ to: "/", label: "Go to the family" }}>
      Something went wrong on our side. The family keeps living; try this page again in a minute.
    </Empty>
  );
}

export function SectionHead({ title, children, className }: { title: string; children?: React.ReactNode; className?: string }) {
  return (
    <div className={cx("mb-8 max-w-2xl", className)}>
      <h2 className="font-display text-[40px] leading-[1.05] tracking-tight sm:text-5xl">{title}</h2>
      {children && <p className="mt-3 text-[17px] leading-relaxed text-mist">{children}</p>}
    </div>
  );
}
