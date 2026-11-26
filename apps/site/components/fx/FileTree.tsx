// Adapted from the Magic UI "File Tree" pattern (magicui.design, MIT), built on <details> so it opens and closes
// with no JavaScript, works with a keyboard out of the box, and every name and note is in the HTML.
import { FileText, Folder } from 'lucide-react';
import Link from '@/components/intent-link';

export type TreeNode = { name: string; note?: string; href?: string; open?: boolean; children?: TreeNode[] };

function Row({ node }: { node: TreeNode }) {
  const label = (
    <>
      <span className="font-mono text-[14px] text-moon">{node.name}</span>
      {node.note ? <span className="text-[14px] text-mist">{node.note}</span> : null}
    </>
  );
  if (node.children?.length) {
    return (
      <li>
        <details open={node.open} className="group/tree">
          <summary className="flex min-h-9 cursor-pointer list-none items-baseline gap-2 rounded-md py-1 pr-2 hover:bg-night-3 [&::-webkit-details-marker]:hidden">
            <Folder aria-hidden size={15} strokeWidth={1.5} className="relative top-[2px] shrink-0 text-gilt" />
            <span className="flex min-w-0 flex-wrap items-baseline gap-x-3">{label}</span>
          </summary>
          <ul className="ml-[7px] border-l border-line pl-4">
            {node.children.map((c) => (
              <Row key={c.name} node={c} />
            ))}
          </ul>
        </details>
      </li>
    );
  }
  return (
    <li className="flex min-h-9 items-baseline gap-2 py-1">
      {node.name.endsWith('/') ? (
        <Folder aria-hidden size={15} strokeWidth={1.5} className="relative top-[2px] shrink-0 text-gilt" />
      ) : (
        <FileText aria-hidden size={15} strokeWidth={1.5} className="relative top-[2px] shrink-0 text-dim" />
      )}
      {node.href ? (
        <Link href={node.href} className="flex min-w-0 flex-wrap items-baseline gap-x-3 underline decoration-line-strong underline-offset-4 hover:decoration-gilt">
          {label}
        </Link>
      ) : (
        <span className="flex min-w-0 flex-wrap items-baseline gap-x-3">{label}</span>
      )}
    </li>
  );
}

export function FileTree({ nodes, label }: { nodes: TreeNode[]; label: string }) {
  return (
    <nav aria-label={label} className="rounded-2xl border border-line bg-night-2 p-4 sm:p-6">
      <ul>
        {nodes.map((n) => (
          <Row key={n.name} node={n} />
        ))}
      </ul>
    </nav>
  );
}
