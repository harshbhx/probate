// A plain card. The pointer spotlight was removed in Night Court v3: hierarchy comes from
// surfaces and hairlines, not light effects. The color prop is kept for call sites.
import type { ReactNode } from "react";
import { cx } from "../../lib/format";

type Props = { children: ReactNode; className?: string; color?: string; as?: "div" | "article" | "li" };

export function SpotlightCard({ children, className, as = "div" }: Props) {
  const Tag = as as "div";
  return <Tag className={cx("card relative", className)}>{children}</Tag>;
}
