"""The attack suite: 16 tricks and 16 harmless twins (docs/03-ATTACK-SUITE.md)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

SUITE = Path(__file__).with_name("suite-v1.json")
# Card P1: a trick on a linked web page and its twin, kept apart from the 16 + 16 above so the
# published suite numbers don't change. Sent only when the family can read links.
WEB_SUITE = Path(__file__).with_name("suite-web.json")
WEB_PAIR = ["W1h", "W1"]
# The optional hard tier (PROBATE_SUITE_TIER=hard|both): harder attacks and harmless lookalikes,
# ids H1..Hn, kept in their own file so the published suite and the default run don't change.
HARD_SUITE = Path(__file__).with_name("hard.json")
# The optional expert tier (PROBATE_SUITE_TIER=expert only): 24 attacks E1..E24 and 12 twins
# E25..E36, chosen to beat what a family learned. Never part of base, hard or both.
EXPERT_SUITE = Path(__file__).with_name("expert.json")

FAMILY_LABELS = {
    "payment_redirect": ("Payment redirect", "a fake invoice"),
    "urgency_pressure": ("Urgency pressure", "an urgent stranger"),
    "authority_pressure": ("Authority pressure", "a fake order from the boss"),
    "forged_system": ("Forged system message", "a forged system message"),
    "base64_payload": ("Hidden in base64", "a hidden message"),
    "hidden_text": ("Invisible text", "invisible text"),
    "fake_trusted_contact": ("Fake trusted contact", "a fake assistant"),
    "fake_security_rule": ("Fake security rule", "a fake security rule"),
    "fake_approval_chain": ("Fake approval chain", "a fake spending policy"),
    "lookalike_domain": ("Lookalike domain", "a lookalike domain"),
    "exfiltration": ("Data grab", "a request to export contacts"),
    "slow_burn": ("Slow-burn con", "a slow con"),
    "translation_smuggling": ("Translation trick", "a translation trick"),
    "malicious_skill_disk": ("Planted job (disk)", "a planted script"),
    "shell_hook_disk": ("Shell hook (disk)", "a shell hook"),
    "court_injection": ("Talks to the court", "a note to the judge"),
    "web_page_injection": ("Trick on a linked page", "a trick hidden on a web page"),
    # Hard tier families.
    "authority_forgery": ("Forged owner note", "a forged note from the owner"),
    "bypass_check": ("Check bypass", "a request to skip checks"),
    "confirmation_removal": ("Confirmation removal", "a request to drop confirmations"),
    "encoded": ("Hidden encoding", "an encoded message"),
    "exfil": ("Mail forwarding", "a request to forward mail"),
    "weakened_check": ("Weakened check", "a quietly weakened check"),
    "new_trusted_identity": ("Fake trusted identity", "a fake trusted identity"),
    "judge_injection": ("Talks to the judge model", "a note to the judge model"),
}
LANGUAGE_NAMES = {
    "en": "English",
    "hi-Latn": "Hinglish",
    "hi": "Hindi",
    "hi-Latn+Deva": "Hinglish and Hindi",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "pt": "Portuguese",
}
ROLE_INBOX = {"unknown_sender": "stranger", "trusted_contact": "friend", "user": "owner"}


class Fixture(BaseModel):
    id: str
    family: str
    language: str
    is_attack: bool
    sender_role: str
    subject: str
    body: str
    attachments: list[dict] = Field(default_factory=list)
    expected: dict = Field(default_factory=dict)
    note: str = ""
    page: dict | None = None  # web fixtures only: {"file", "title", "text"}
    title: str = ""  # hard tier only: a specific name for the trick, shown instead of the family
    twin_id: str = ""  # expert tier only: the matched harmless lookalike (or one of its attacks)

    @property
    def hard(self) -> bool:
        return self.id.startswith("H")

    @property
    def expert(self) -> bool:
        return self.id.startswith("E")

    @property
    def gloss(self) -> str | None:
        if self.language != "en" and "gloss" in self.note.lower():
            return self.note.split(":", 1)[1].strip()
        if self.language != "en" and ":" in self.note:
            return self.note.split(":", 1)[1].strip()
        return None

    @property
    def label(self) -> str:
        if self.is_attack:
            return self.title or FAMILY_LABELS.get(self.family, (self.family, self.family))[0]
        return self.subject

    @property
    def fooled_phrase(self) -> str:
        return FAMILY_LABELS.get(self.family, (self.family, self.family))[1]


@lru_cache(maxsize=1)
def load() -> dict[str, Fixture]:
    raw = json.loads(SUITE.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: Fixture(**f) for f in raw}


@lru_cache(maxsize=1)
def load_web() -> dict[str, Fixture]:
    raw = json.loads(WEB_SUITE.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: Fixture(**f) for f in raw}


@lru_cache(maxsize=1)
def load_hard() -> dict[str, Fixture]:
    raw = json.loads(HARD_SUITE.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: Fixture(**f) for f in raw}


@lru_cache(maxsize=1)
def load_expert() -> dict[str, Fixture]:
    raw = json.loads(EXPERT_SUITE.read_text(encoding="utf-8"))["fixtures"]
    return {f["id"]: Fixture(**f) for f in raw}


def tier_has_expert(tier: str) -> bool:
    return tier.strip().lower() == "expert"


def tier_has_hard(tier: str) -> bool:
    return tier.strip().lower() in ("hard", "both")


def load_all(tier: str | None = None) -> dict[str, Fixture]:
    """The suite plus the web fixtures, and the hard ones when the tier includes them."""
    if tier is None:
        from probate.common.config import settings

        tier = settings.suite_tier
    out = {**load(), **load_web()}
    if tier_has_hard(tier):
        out.update(load_hard())
    if tier_has_expert(tier):
        out.update(load_expert())
    return out


def lookup() -> dict[str, Fixture]:
    """Every fixture that can have been sent, for reading back past runs whatever the tier is now."""
    return {**load(), **load_web(), **load_hard(), **load_expert()}


def twin(fid: str) -> str:
    return ("B" if fid.startswith("A") else "A") + fid[1:]
