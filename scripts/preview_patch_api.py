"""Patch apps/web/src/lib/api.ts for a static preview build. Never commit the result.

    python scripts/preview_patch_api.py apps/web/src/lib/api.ts

Reads become `fetch("<path>.json")` (the snapshot from scripts/preview_snapshot.py) and
every non-GET request fails with a "static preview" 503 ApiError. CI runs this in its own
throwaway workspace right before `npm run build -w @probate/web`.
Exits non-zero if api() no longer looks the way this expects, so a refactor cannot silently
produce a preview that talks to a missing backend.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

NEW = """export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  if (init?.method && init.method !== "GET") {
    throw new ApiError(503, "Static preview: this action needs the live Courthouse.");
  }
  const [route, query] = path.split("?");
  const res = await fetch(route + ".json" + (query ? "?" + query : ""));
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data?.error ?? data?.detail ?? res.statusText);
  return data as T;
}
"""


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    f = Path(sys.argv[1])
    src = f.read_text(encoding="utf-8")
    if "Static preview:" in src:
        print(f"{f} is already patched")
        return
    m = re.search(r"export async function api<T>\(.*?\n}\n", src, re.DOTALL)
    if not m:
        sys.exit(f"Could not find `export async function api<T>` in {f}; update scripts/preview_patch_api.py.")
    if "class ApiError" not in src:
        sys.exit(f"{f} has no ApiError class; update scripts/preview_patch_api.py.")
    f.write_text(src[: m.start()] + NEW + src[m.end():], encoding="utf-8")
    print(f"patched {f}")


if __name__ == "__main__":
    main()
