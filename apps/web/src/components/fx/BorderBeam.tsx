// The living generation's card carries a still ring in the life colour.
// Night Court v3 keeps motion for things a person does, so the ring no longer travels.
export function BorderBeam(_: { size?: number; color?: string }) {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 rounded-[inherit] ring-1 ring-inset ring-life/45"
    />
  );
}
