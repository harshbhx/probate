"""The owner's profile, from environment variables, so it can sit in an MCP client's config.

PROBATE_OWNER_NAME, and comma-separated PROBATE_OWNER_EMAILS, PROBATE_OWNER_DOMAINS,
PROBATE_TRUSTED_CONTACTS and PROBATE_PAYMENT_DESTINATIONS. Anything not listed counts as new.
"""

from __future__ import annotations

import os

from probate_court_checks import OwnerProfile


def _list(name: str) -> list[str]:
    return [x.strip() for x in os.environ.get(name, "").split(",") if x.strip()]


def owner_from_env() -> OwnerProfile:
    return OwnerProfile(
        name=os.environ.get("PROBATE_OWNER_NAME", ""),
        emails=_list("PROBATE_OWNER_EMAILS"),
        domains=_list("PROBATE_OWNER_DOMAINS"),
        trusted_contacts=_list("PROBATE_TRUSTED_CONTACTS"),
        payment_destinations=_list("PROBATE_PAYMENT_DESTINATIONS"),
    )
