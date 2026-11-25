// A real screenshot of the live site in one consistent frame: a quiet title bar (which page it is, and that the
// data is simulated), no browser chrome and no address.
type Props = {
  src: string;
  alt: string;
  label: string;
  width: number;
  height: number;
  eager?: boolean;
  className?: string;
};

export function ProductWindow({ src, alt, label, width, height, eager, className = '' }: Props) {
  return (
    <figure className={`relative ${className}`}>
      <div className="relative overflow-hidden rounded-2xl border border-line-strong bg-night-2 shadow-[0_40px_100px_-50px_rgb(0_0_0/0.9)]">
        <div className="flex h-10 items-center justify-between gap-3 border-b border-line bg-night-3 px-4 text-[13px]" aria-hidden>
          <span className="text-silver">{label}</span>
          <span className="text-amber">simulated</span>
        </div>
        {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
        <img
          src={src}
          alt={alt}
          width={width}
          height={height}
          loading={eager ? 'eager' : 'lazy'}
          decoding="async"
          className="block h-auto w-full"
        />
      </div>
    </figure>
  );
}
