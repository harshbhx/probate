// Figures are set once, in their final value. (unslop, Motion pass: numbers only tween when
// they change in front of you, never as decoration on load.)
type Props = { value: number; decimals?: number; suffix?: string; className?: string; duration?: number };

export function NumberTicker({ value, decimals = 0, suffix = "", className }: Props) {
  return (
    <span className={className}>
      <span className="tabular">{`${value.toFixed(decimals)}${suffix}`}</span>
    </span>
  );
}
