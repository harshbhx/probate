"""Work out what a release run should do, and refuse anything unclear. Used by release.yml.

    python scripts/release_plan.py --event push --ref-type tag --ref-name kinfaces-v0.2.0
    python scripts/release_plan.py --event workflow_dispatch --package client --dry-run true \
        --ref-type branch --ref-name main

Tags are <key>-v<version>. The key picks a package directory; the directory decides whether
it is an npm package (package.json) or a Python package (pyproject.toml). Writes key=value
lines to $GITHUB_OUTPUT (or stdout when run by hand). Any problem exits non-zero with a
message that says what to do.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# tag key -> package directory. Packages are added by their own PRs; a key whose directory
# is not on the checked-out ref fails with a clear message instead of publishing nothing.
PACKAGES = {
    "kinfaces": "packages/faces",
    "court-checks": "packages/court-checks",
    "client": "packages/client",
    "client-py": "packages/client-py",
    "mcp": "packages/mcp",
}


def fail(msg: str) -> None:
    print(f"::error title=Release plan::{msg}")
    sys.exit(1)


def split_tag(tag: str) -> tuple[str, str]:
    for key in sorted(PACKAGES, key=len, reverse=True):
        if tag.startswith(f"{key}-v") and len(tag) > len(key) + 2:
            return key, tag[len(key) + 2 :]
    fail(f"Tag '{tag}' does not match any of: " + ", ".join(f"{k}-v<version>" for k in PACKAGES))
    raise AssertionError


def describe(pkg_dir: Path, key: str) -> dict:
    if not pkg_dir.is_dir():
        fail(
            f"{pkg_dir.relative_to(ROOT)} does not exist on this ref, so '{key}' cannot be released from it. "
            "The package probably has not merged to main yet. Merge its pull request, or dispatch a dry run "
            "from the branch that adds it."
        )
    has_npm = (pkg_dir / "package.json").is_file()
    has_py = (pkg_dir / "pyproject.toml").is_file()
    if has_npm == has_py:
        fail(f"{pkg_dir.relative_to(ROOT)} must contain exactly one of package.json or pyproject.toml.")
    if has_npm:
        meta = json.loads((pkg_dir / "package.json").read_text(encoding="utf-8"))
        if meta.get("private"):
            fail(
                f"{meta.get('name', pkg_dir.name)} is marked \"private\": true in package.json, which npm will "
                "refuse to publish. Remove it in a pull request when the package is ready to ship."
            )
        return {"kind": "npm", "name": meta.get("name", ""), "version": meta.get("version", "")}
    proj = tomllib.loads((pkg_dir / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    if not proj.get("name"):
        fail(f"{pkg_dir.relative_to(ROOT)}/pyproject.toml has no [project] name.")
    return {"kind": "python", "name": proj["name"], "version": proj.get("version", "")}


def main() -> None:
    global ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--event", required=True, choices=["push", "workflow_dispatch"])
    ap.add_argument("--ref-type", required=True)
    ap.add_argument("--ref-name", required=True)
    ap.add_argument("--package", default="")
    ap.add_argument("--dry-run", default="true")
    ap.add_argument("--root", default=str(ROOT), help="repository root (for tests)")
    a = ap.parse_args()
    ROOT = Path(a.root).resolve()

    tag_version = ""
    if a.event == "push":
        if a.ref_type != "tag":
            fail("A push release must be triggered by a tag.")
        key, tag_version = split_tag(a.ref_name)
        publish = True
        tag = a.ref_name
    else:
        key = a.package
        if key not in PACKAGES:
            fail(f"Unknown package '{key}'. Choose one of: {', '.join(PACKAGES)}.")
        publish = a.dry_run.lower() == "false"
        tag = ""
        if publish:
            if a.ref_type != "tag":
                fail("A real release must be dispatched on a tag (use 'Run workflow' with the tag selected), not a branch.")
            k2, tag_version = split_tag(a.ref_name)
            if k2 != key:
                fail(f"Tag '{a.ref_name}' belongs to '{k2}', but you chose package '{key}'.")
            tag = a.ref_name

    info = describe(ROOT / PACKAGES[key], key)
    if tag_version:
        if not info["version"]:
            print(f"::warning::{info['name']} has no static version, so the tag version {tag_version} was not checked.")
        elif info["version"] != tag_version:
            fail(f"Tag version {tag_version} does not match {info['name']}'s version {info['version']}. Bump it first.")
    version = tag_version or info["version"] or "0.0.0"

    out = {
        "key": key,
        "dir": PACKAGES[key],
        "kind": info["kind"],
        "name": info["name"],
        "version": version,
        "tag": tag,
        "publish": str(publish).lower(),
        "prerelease": str("-" in version or any(c.isalpha() for c in version)).lower(),
    }
    lines = "".join(f"{k}={v}\n" for k, v in out.items())
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as f:
            f.write(lines)
    print(lines, end="")


if __name__ == "__main__":
    main()
