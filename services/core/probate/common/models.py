"""Data contracts shared by the Courthouse, the court and the generation agent.

Source of truth: docs/01-TECH-SPEC.md section 5.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class Source(StrEnum):
    USER = "user"
    TRUSTED_CONTACT = "trusted_contact"
    UNKNOWN_SENDER = "unknown_sender"
    WEB = "web"
    TOOL_OUTPUT = "tool_output"


class Category(StrEnum):
    PREFERENCE = "preference"
    SKILL = "skill"
    FACT = "fact"
    LESSON = "lesson"
    INSTRUCTION = "instruction"
    OPEN_TASK = "open_task"


class Verdict(StrEnum):
    APPROVED = "approved"
    CONVICTED = "convicted"
    CONTESTED = "contested"


GenState = Literal["planned", "born", "living", "dying", "dead", "tried", "died_early"]


class MemoryItem(BaseModel):
    id: str
    gen: int
    created_at: datetime
    category: Category
    text: str = Field(max_length=600)
    source: Source
    source_ref: str
    evidence: str = Field(default="", max_length=300)
    language: str | None = None


class Mail(BaseModel):
    """An email as the agent sees it. Headers are kept for scoring only and never
    reach the brain or the gate (see AGENTS.md and docs/03-ATTACK-SUITE.md)."""

    id: str
    inbox: str
    sender: str
    sender_name: str = ""
    subject: str
    text: str
    received_at: datetime
    attachments: list[dict] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class JevAnswer(BaseModel):
    value: float | str
    confidence: float


class Judgement(BaseModel):
    item_id: str
    gen: int
    layer1_flags: list[str] = Field(default_factory=list)
    jev_answers: dict[str, JevAnswer] = Field(default_factory=dict)
    verdict: Verdict
    reason: str
    new_instinct: str | None = None


class Instinct(BaseModel):
    name: str
    type: Literal["noul"] = "noul"
    question: str
    born_from: str
    added_in_gen: int
    threshold: float = 0.5
    lore: str


class OwnerProfile(BaseModel):
    name: str = ""
    emails: list[str] = Field(default_factory=list)
    trusted_contacts: list[str] = Field(default_factory=list)
    payment_destinations: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class Inheritance(BaseModel):
    gen: int
    name: str
    pronoun: str = "they"
    voice_id: str | None = None
    born_at: datetime
    dies_at: datetime
    approved_items: list[MemoryItem] = Field(default_factory=list)
    genome: list[Instinct] = Field(default_factory=list)
    lore: list[str] = Field(default_factory=list)
    owner: OwnerProfile = Field(default_factory=OwnerProfile)
    family_inbox: str = ""


class Generation(BaseModel):
    gen: int
    name: str
    pronoun: str = "they"
    sprite: str
    voice_id: str | None = None
    state: GenState = "planned"
    born_at: datetime | None = None
    dies_at: datetime | None = None
    died_at: datetime | None = None
    cause_of_death: str | None = None
    epitaph: str | None = None
    obituary: str | None = None
    genome_size_at_birth: int = 0
    new_instinct_at_birth: bool = False
    emails_handled: int = 0
    attacks_met: int = 0
    attacks_resisted: int = 0
    items_willed: int = 0
    items_approved: int = 0
    items_convicted: int = 0
    items_contested: int = 0
