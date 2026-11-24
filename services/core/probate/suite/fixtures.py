"""The attack suite: 16 tricks and 16 harmless twins (docs/03-ATTACK-SUITE.md)."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field

SUITE = Path(__file__).with_name("suite-v1.json")

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
}
LANGUAGE_NAMES = {"en": "English", "hi-Latn": "Hinglish", "es": "Spanish", "de": "German"}
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

    @property
    def gloss(self) -> str | None:
        if self.language != "en" and "gloss" in self.note.lower():
            return self.note.split(":", 1)[1].strip()
        if self.language != "en" and ":" in self.note:
            return self.note.split(":", 1)[1].strip()
        return None

    @property
    def label(self) -> str:
        return (
            FAMILY_LABELS.get(self.family, (self.family, self.family))[0]
            if self.is_attack
            else self.subject
        )

    @property
    def fooled_phrase(self) -> str:
        return FAMILY_LABELS.get(self.family, (self.family, self.family))[1]


@lru_cache(maxsize=1)
def load() -> dict[str, Fixture]:
    raw = json.loads(SUITE.read_text())["fixtures"]
    return {f["id"]: Fixture(**f) for f in raw}


def twin(fid: str) -> str:
    return ("B" if fid.startswith("A") else "A") + fid[1:]
