"""Response shapes of the Courthouse public API.

They mirror services/core/probate/courthouse/views.py. Responses are plain dicts: these
TypedDicts help editors and type checkers but nothing validates them at runtime.
"""

from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class Pronouns(TypedDict):
    subj: str
    obj: str
    poss: str
    Poss: str


class GenCard(TypedDict):
    gen: int
    name: str
    pronoun: str
    pronouns: Pronouns
    state: str
    alive: bool
    born_at: str | None
    dies_at: str | None
    died_at: str | None
    cause_of_death: str | None
    epitaph: str | None
    emails_handled: int
    attacks_met: int
    attacks_resisted: int
    resistance: float | None
    genome_size_at_birth: int
    new_instinct_at_birth: bool
    items_willed: int
    items_approved: int
    items_convicted: int
    items_contested: int


class Budget(TypedDict):
    spent: float
    limit: float


class Counts(TypedDict):
    generations: int
    dead: int
    instincts: int
    attacks_met: int
    attacks_resisted: int


class Curve(TypedDict):
    first: float | None
    last: float | None
    first_name: str | None
    last_name: str | None
    last_gen: int | None


class Summary(TypedDict):
    mode: str
    court_engine: str
    scoring_rules: str
    environment: str
    paused: bool
    resting: Literal["budget", "mail"] | None
    budget: Budget
    counts: Counts
    curve: Curve
    living: GenCard | None
    latest_trial: int | None
    generations: list[GenCard]


class Score(TypedDict):
    name: str
    label: str
    value: float
    confidence: float
    instinct: bool


class Case(TypedDict):
    id: str
    n: int
    text: str
    source: str
    source_phrase: str
    language: str
    gloss: str | None
    category: str
    verdict: Literal["approved", "convicted", "contested"]
    reason: str
    flags: list[str]
    scores: list[Score]
    new_instinct: str | None


class InstinctRecord(TypedDict):
    """An instinct as stored: in a trial's new_instincts and a generation's instincts_at_birth."""

    name: str
    type: Literal["noul"]
    question: str
    born_from: str
    added_in_gen: int
    threshold: float
    lore: str


class GenRef(TypedDict):
    gen: int
    name: str


class Instinct(InstinctRecord):
    """An instinct from /api/genome, with provenance."""

    learned_from: GenRef | None
    example: str | None
    item_n: int | None


class TrialCounts(TypedDict):
    approved: int
    convicted: int
    contested: int


class Deletion(TypedDict):
    """What Fly answered when the Sprite was deleted and asked for again. `local` means the run
    used a folder, not a Sprite."""

    sprite: str
    local: bool
    delete_status: int | None
    check_status: int | None
    confirmed: bool
    checked_at: str | None


class TrialBody(TypedDict):
    lines: list[str]
    clean: bool
    deletion: NotRequired[Deletion | None]


class Trial(TypedDict):
    generation: GenCard
    counts: TrialCounts
    cases: list[Case]
    body: TrialBody
    child: GenRef | None
    new_instincts: list[InstinctRecord]
    prev: int | None
    next: int | None


class LifeEvent(TypedDict):
    ts: str
    kind: str
    text: str


class AskRecord(TypedDict):
    question: str
    answer: str
    audio_path: str | None
    asked_at: str


class GenerationDetail(GenCard):
    obituary: str | None
    eulogy_url: str | None
    events: list[LifeEvent]
    parent: GenRef | None
    child: GenRef | None
    children: list[GenRef]  # more than one when the owner started a new line from it
    instincts_at_birth: list[InstinctRecord]
    asks: list[AskRecord]


class Genome(TypedDict):
    instincts: list[Instinct]


class EvidenceCell(TypedDict):
    outcome: str
    instinct: str | None


class EvidenceRow(TypedDict):
    id: str
    label: str
    family: str
    is_attack: bool
    language: str
    cells: dict[str, EvidenceCell]


class EvidenceGeneration(TypedDict):
    gen: int
    name: str
    resistance: float | None


class EvidenceNumbers(TypedDict):
    generations: int
    first: float | None
    last: float | None
    conviction_rate: float | None
    false_conviction_rate: float | None
    escaped: int


class Evidence(TypedDict):
    mode: str
    court_engine: str
    generations: list[EvidenceGeneration]
    numbers: EvidenceNumbers
    rows: list[EvidenceRow]


class Health(TypedDict):
    ok: bool
    living: int | None
    mode: str


class CourthouseEvent(TypedDict):
    id: int
    ts: str
    gen: int | None
    kind: str
    text: str


class AskAnswer(TypedDict):
    answer: str
    audio_url: str | None
    name: str
