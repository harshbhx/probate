export const cx = (...xs: (string | false | null | undefined)[]) => xs.filter(Boolean).join(" ");

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function dayTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

export function day(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

export function clock(iso: string): string {
  const d = new Date(iso);
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

export function pad(n: number) {
  return String(n).padStart(2, "0");
}

export function countdown(ms: number): string {
  if (ms <= 0) return "00:00:00";
  const s = Math.floor(ms / 1000);
  return `${pad(Math.floor(s / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
}

export function pct(v: number | null | undefined): string {
  if (v === null || v === undefined) return "n/a";
  return v < 10 && v % 1 ? `${v.toFixed(1)}%` : `${Math.round(v)}%`;
}

export function plural(n: number, one: string, many = one + "s") {
  return `${n} ${n === 1 ? one : many}`;
}

export function humanize(name: string) {
  return name.replace(/_/g, " ");
}

export function sentence(name: string) {
  const h = humanize(name);
  return h.charAt(0).toUpperCase() + h.slice(1);
}
