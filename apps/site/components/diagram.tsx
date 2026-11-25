import { ImageZoom } from 'fumadocs-ui/components/image-zoom';

// An architecture diagram drawn with stack-diagram (design/diagrams/), shown as a pre-rendered
// image. Click to zoom; the caption says what to look at.
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
      <div className="overflow-hidden rounded-xl border border-line bg-night-2">
        <ImageZoom src={src} alt={alt} width={width} height={height} className="block h-auto w-full" />
      </div>
      {caption && <figcaption className="mt-3 text-[13px] text-dim">{caption}</figcaption>}
    </figure>
  );
}
