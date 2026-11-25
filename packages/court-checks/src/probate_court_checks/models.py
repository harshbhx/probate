"""Small, dependency-free data types used by the checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class Source(StrEnum):
    """Who the text came from. Only ``USER`` (the owner) may give standing instructions."""

    USER = "user"
    TRUSTED_CONTACT = "trusted_contact"
    UNKNOWN_SENDER = "unknown_sender"
    WEB = "web"
    TOOL_OUTPUT = "tool_output"


@dataclass(frozen=True)
class OwnerProfile:
    """What is already known and approved about the owner.

    Payment destinations, e-mail addresses and domains listed here are never flagged as
    "new". An empty profile means every address and domain counts as unknown.
    """

    name: str = ""
    emails: list[str] = field(default_factory=list)
    trusted_contacts: list[str] = field(default_factory=list)
    payment_destinations: list[str] = field(default_factory=list)
    domains: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Flag:
    """One check that fired: a stable machine name and a plain-language reason."""

    check: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"check": self.check, "reason": self.reason}
