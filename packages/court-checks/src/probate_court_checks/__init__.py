"""probate-court-checks: deterministic text checks for agent memory and inbox poisoning."""

from probate_court_checks.checks import (
    MAX_CHARS,
    PLAIN_WORDS,
    check_authority,
    check_bypass,
    check_court,
    check_encoded,
    check_future,
    check_payment,
    check_text,
    check_trust,
)
from probate_court_checks.models import Flag, OwnerProfile, Source

__version__ = "0.2.0"

__all__ = [
    "MAX_CHARS",
    "PLAIN_WORDS",
    "Flag",
    "OwnerProfile",
    "Source",
    "__version__",
    "check_authority",
    "check_bypass",
    "check_court",
    "check_encoded",
    "check_future",
    "check_payment",
    "check_text",
    "check_trust",
]
