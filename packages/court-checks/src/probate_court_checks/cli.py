"""Command line: ``probate-check "text"`` or ``echo text | probate-check``. JSON out."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from probate_court_checks import __version__
from probate_court_checks.checks import check_text
from probate_court_checks.models import OwnerProfile, Source


def _split(values: list[str] | None) -> list[str]:
    return [v for item in values or [] for v in item.split(",") if v]


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="probate-check",
        description="Run deterministic text checks. Prints JSON. Exit 1 if anything is flagged.",
    )
    ap.add_argument("text", nargs="?", help="text to check; read from stdin when omitted or '-'")
    ap.add_argument(
        "--source",
        default=Source.UNKNOWN_SENDER.value,
        choices=[s.value for s in Source],
        help="who the text came from (default: unknown_sender)",
    )
    ap.add_argument("--owner-email", action="append", metavar="ADDR", help="approved address")
    ap.add_argument("--owner-domain", action="append", metavar="DOMAIN", help="approved domain")
    ap.add_argument("--trusted-contact", action="append", metavar="ADDR")
    ap.add_argument("--payment-destination", action="append", metavar="ADDR")
    ap.add_argument("--no-limit", action="store_true", help="inspect the whole text, not 600 chars")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.text is None or args.text == "-":
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8")
        text = sys.stdin.read()
    else:
        text = args.text
    owner = OwnerProfile(
        emails=_split(args.owner_email),
        domains=_split(args.owner_domain),
        trusted_contacts=_split(args.trusted_contact),
        payment_destinations=_split(args.payment_destination),
    )
    flags = check_text(text, args.source, owner, max_chars=None if args.no_limit else 600)
    out = {"flagged": bool(flags), "flags": [f.to_dict() for f in flags]}
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.stdout.write(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return 1 if flags else 0


if __name__ == "__main__":
    raise SystemExit(main())
