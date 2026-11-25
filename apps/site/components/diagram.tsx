// An architecture diagram drawn with stack-diagram (design/diagrams/), shown as a pre-rendered image.
// The caption says what to look at; the link opens the full-size picture.
export function Diagram({
  src,
  alt,
  width,
  height,
  caption,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  caption?: string;
}) {
  return (
    <figure className="not-prose my-8">
      <a href={src} className="block overflow-hidden rounded-xl border border-line bg-night-2" aria-label={`${alt} (open full size)`}>
        {/* eslint-disable-next-line @next/next/no-img-element -- static export, pre-sized WebP */}
        <img src={src} alt={alt} width={width} height={height} loading="lazy" decoding="async" className="block h-auto w-full" />
      </a>
      {caption && <figcaption className="mt-3 text-[13px] text-dim">{caption}</figcaption>}
    </figure>
  );
}
