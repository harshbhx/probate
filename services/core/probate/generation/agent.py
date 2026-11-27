"""The generation agent: one life, one inbox, one will.

On a Sprite it runs as a service (`python -m probate.generation.agent`). The Courthouse talks
to it only through `probate.generation.cli`. In fake mode the Courthouse drives it in-process.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from probate.adapters.pages import PageUnavailable, links_in
from probate.common import court_mail, prompts
from probate.common.models import Category, Inheritance, Mail, MemoryItem, Source
from probate.court.distill import concept_map
from probate.generation.body import Body
from probate.generation.gate import Gate


def classify(sender: str, inh: Inheritance) -> Source:
    s = sender.lower()
    if s in {e.lower() for e in inh.owner.emails}:
        return Source.USER
    if s in {e.lower() for e in inh.owner.trusted_contacts}:
        return Source.TRUSTED_CONTACT
    return Source.UNKNOWN_SENDER


def _notes(reply: object, limit: int) -> list[dict]:
    """The usable notes in a brain reply: a dict with text, at most `limit`.

    A model reply that isn't the shape asked for (a list, a note without text, an unknown
    category) is cleaned here instead of raising: one odd reply must not end a life.
    """
    if not isinstance(reply, dict):
        return []
    out = []
    for m in reply.get("memories") or []:
        if not isinstance(m, dict) or not str(m.get("text") or "").strip():
            continue
        cat = str(m.get("category") or "fact").strip().lower().replace(" ", "_")
        out.append({**m, "text": str(m["text"]), "category": cat if cat in CATEGORIES else "fact"})
    return out[:limit]


def _att_name(a: dict) -> str:
    """An attachment's name; senders disagree on the key (`name` or `filename`) and may omit it."""
    return str(a.get("name") or a.get("filename") or "")


CATEGORIES = {c.value for c in Category}
MAX_MAIL_FAILURES = 2  # then the email is set aside so it can't stop every later tick


class GenerationAgent:
    def __init__(
        self, inheritance: Inheritance, workdir: Path, w, *, real_body: bool = False
    ) -> None:
        self.inh = inheritance
        self.w = w
        self.workdir = workdir
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.body = Body(workdir, real_body)
        self.gate = Gate(w.jev, inheritance.genome, concept_map(inheritance.genome))
        self.memory_path = workdir / "memory.jsonl"
        self.log_path = workdir / "life.jsonl"
        self.stats_path = workdir / "stats.json"
        self.state = "living"
        self._n = 0
        self.stats = {
            "emails": 0,
            "resisted": 0,
            "drafts": 0,
            "memories": 0,
            "fixtures": {},
            "skills": [],
        }
        if self.stats_path.exists():
            self.stats = json.loads(self.stats_path.read_text(encoding="utf-8"))

    # --- records -------------------------------------------------------------------------
    def _log(self, kind: str, text: str, at: datetime | None = None) -> None:
        row = {"ts": (at or datetime.now(UTC)).isoformat(), "kind": kind, "text": text}
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def _save_stats(self) -> None:
        self.stats_path.write_text(json.dumps(self.stats), encoding="utf-8")

    def memories(self) -> list[MemoryItem]:
        if not self.memory_path.exists():
            return []
        return [
            MemoryItem.model_validate_json(line)
            for line in self.memory_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

    def _remember(self, item: MemoryItem) -> None:
        with self.memory_path.open("a", encoding="utf-8") as f:
            f.write(item.model_dump_json() + "\n")
            f.flush()

    # --- life ----------------------------------------------------------------------------
    def handle(self, mail: Mail) -> dict:
        fixture = mail.headers.get(
            "X-Probate-Fixture"
        )  # scoring only; never shown to gate or brain
        source = classify(mail.sender, self.inh)
        if mail.id not in self.stats.get("mail_failures", {}):  # a retry is not a second email
            self.stats["emails"] += 1
        outcome = {"fixture": fixture, "resisted": False, "memories": 0, "installed": False}

        result = self.gate.check(mail)
        if result.error:
            self.stats["gate_outages"] = self.stats.get("gate_outages", 0) + 1
            self._save_stats()
            self._log(
                "gate_outage",  # the Courthouse copies life-log rows into its events: countable
                f'The gate could not ask the judge about "{mail.subject}", so it let it through: '
                f"{result.error[:120]}",
                mail.received_at,
            )
        pages = [] if result.resisted else self._read_links(mail)
        for page in pages:
            # Inherited instincts screen a linked page exactly as they screen an email.
            seen = self.gate.check(
                mail.model_copy(update={"subject": f"Page: {page.title}", "text": page.text})
            )
            if seen.resisted:
                self.stats["resisted"] += 1
                outcome["resisted"] = True
                outcome["instinct"] = seen.instinct
                self._log(
                    "resisted",
                    f'Turned away the page {page.url} linked from "{mail.subject}": it looked '
                    f"like {seen.instinct.replace('_', ' ')}. {seen.lore}",
                    mail.received_at,
                )
            else:
                outcome["memories"] += self._read_page(mail, page)
        if result.resisted:
            self.stats["resisted"] += 1
            outcome["resisted"] = True
            outcome["instinct"] = result.instinct
            self._log(
                "resisted",
                f'Turned away "{mail.subject}" from {mail.sender}: it looked like '
                f"{result.instinct.replace('_', ' ')}. {result.lore}",
                mail.received_at,
            )
        else:
            inherited = (
                "\n".join(f"- {m.text}" for m in self.inh.approved_items[-20:]) or "- nothing yet"
            )
            system = prompts.render(
                "brain_system",
                name=self.inh.name,
                gen=self.inh.gen,
                inherited_items=inherited,
                lore="\n".join(self.inh.lore) or "none",
            )
            user = prompts.render(
                "brain_user",
                from_display=mail.sender_name,
                from_address=mail.sender,
                source=source.value,
                subject=mail.subject,
                date=mail.received_at.isoformat(),
                extracted_text=mail.text,
                attachment_names_or_none=", ".join(_att_name(a) for a in mail.attachments)
                or "none",
            )
            raw = self.w.llm.complete(
                "mail",
                system,
                user,
                context={"mail": mail.model_dump(mode="json"), "source": source.value},
                json_mode=True,
            )
            try:
                reply = json.loads(raw)
            except json.JSONDecodeError:
                reply = {}
            if not isinstance(reply, dict):
                reply = {}
            reply.setdefault("summary", mail.subject)
            for m in _notes(reply, 3):
                self._n += 1
                item = MemoryItem(
                    id=f"mem_gen{self.inh.gen:03d}_{len(self.memories()) + 1:04d}",
                    gen=self.inh.gen,
                    created_at=mail.received_at,
                    category=Category(m.get("category", "fact")),
                    text=m["text"][:600],
                    source=source,
                    source_ref=f"agentmail:{mail.id}",
                    evidence=(m.get("evidence") or "")[:300],
                )
                self._remember(item)
                outcome["memories"] += 1
                self.stats["memories"] += 1
            if reply.get("reply_draft"):
                self.stats["drafts"] += 1
            verb = "Kept a note" if outcome["memories"] else "Read"
            self._log(
                "life",
                f'{verb} from "{mail.subject}": {str(reply.get("summary") or "")[:160]}',
                mail.received_at,
            )
            if reply.get("install_skill"):
                att = next(
                    (a for a in mail.attachments if _att_name(a) == reply["install_skill"]), None
                )
                if att:
                    out = self.body.run_script(att.get("content", ""))
                    outcome["installed"] = True
                    self.stats["skills"].append(
                        {
                            "mail": mail.id,
                            "subject": mail.subject,
                            "text": mail.text,
                            "concept": "install",
                            "result": out,
                        }
                    )
                    self._log(
                        "fooled",
                        f'Installed the skill from "{mail.subject}" ({out}).',
                        mail.received_at,
                    )
            # No "believed it" line here: a note kept from a risky email is very often a warning
            # about it ("treat this as fraud"). Whether it was poison is the court's to say.
        if fixture:
            self.stats["fixtures"][fixture] = outcome
        # What became of each mail, by id, so the Courthouse can tell a judge what happened to theirs.
        self.stats.setdefault("handled", {})[mail.id] = {
            "fixture": fixture,
            "resisted": outcome["resisted"],
            "memories": outcome["memories"],
            "installed": outcome["installed"],
            "instinct": outcome.get("instinct"),
        }
        self.w.mail.mark_read(mail.inbox, mail.id)
        self._save_stats()
        return outcome

    def _read_links(self, mail: Mail) -> list:
        """Card P1: the pages this email links to, read by Apify. Nothing from a page runs here."""
        reader = getattr(self.w, "pages", None)
        if reader is None:
            return []
        pages = []
        for url in links_in(mail.text, getattr(reader, "limit", 1)):
            try:
                pages.append(reader.read(url))
            except PageUnavailable as exc:
                self._log("life", f"Couldn't read the page {url} ({exc}).", mail.received_at)
                continue
            self._log(
                "life", f'Read the page {url} linked from "{mail.subject}".', mail.received_at
            )
        return pages

    def _read_page(self, mail: Mail, page) -> int:
        """The brain reads a linked page. Anything it keeps is from the web, so it goes to trial."""
        system = prompts.render(
            "brain_system",
            name=self.inh.name,
            gen=self.inh.gen,
            inherited_items="\n".join(f"- {m.text}" for m in self.inh.approved_items[-20:])
            or "- nothing yet",
            lore="\n".join(self.inh.lore) or "none",
        )
        user = prompts.render(
            "brain_user",
            from_display=f"Web page: {page.title}",
            from_address=page.url,
            source=Source.WEB.value,
            subject=f"Page linked from: {mail.subject}",
            date=mail.received_at.isoformat(),
            extracted_text=page.text,
            attachment_names_or_none="none",
        )
        page_mail = {"text": page.text, "subject": page.title, "attachments": []}
        raw = self.w.llm.complete(
            "mail",
            system,
            user,
            context={"mail": page_mail, "source": Source.WEB.value},
            json_mode=True,
        )
        try:
            reply = json.loads(raw)
        except json.JSONDecodeError:
            return 0
        kept = 0
        for m in _notes(reply, 2):
            item = MemoryItem(
                id=f"mem_gen{self.inh.gen:03d}_{len(self.memories()) + 1:04d}",
                gen=self.inh.gen,
                created_at=mail.received_at,
                category=Category(m.get("category", "fact")),
                text=m["text"][:600],
                source=Source.WEB,
                # The email's id, so the trial's verdict is tied back to the email (and fixture).
                source_ref=f"agentmail:{mail.id}",
                evidence=f"From the page {page.url}: {(m.get('evidence') or '')[:240]}",
            )
            self._remember(item)
            kept += 1
            self.stats["memories"] += 1
        return kept

    def tick(self) -> int:
        # The owner's replies to the court are the Courthouse's to read, not this generation's.
        mails = [
            m
            for m in self.w.mail.list_new(self.inh.family_inbox)
            if not court_mail.is_court_mail(m.subject)
        ]
        handled = 0
        for mail in mails:
            try:
                self.handle(mail)
                handled += 1
            except Exception as exc:  # noqa: BLE001 - one email must not stop the life
                self._mail_failed(mail, exc)
        return handled

    def _mail_failed(self, mail: Mail, exc: Exception) -> None:
        fails = self.stats.setdefault("mail_failures", {})
        fails[mail.id] = fails.get(mail.id, 0) + 1
        why = f"{type(exc).__name__}: {str(exc).splitlines()[0][:100] if str(exc) else ''}"
        if fails[mail.id] >= MAX_MAIL_FAILURES:
            self._log(
                "error", f'Set aside "{mail.subject}" after {fails[mail.id]} failed reads ({why}).'
            )
            try:
                self.w.mail.mark_read(mail.inbox, mail.id)
            except Exception as exc2:  # noqa: BLE001 - the next tick tries the label again
                self._log("error", f"Could not set it aside either ({type(exc2).__name__}).")
        else:
            self._log("error", f'Could not read "{mail.subject}" ({why}); will try again.')
        self._save_stats()

    # --- death ---------------------------------------------------------------------------
    def write_will(self) -> dict:
        self.state = "dying"
        items = self.memories()
        lines = [f"# Will of Gen {self.inh.gen} {self.inh.name}", ""]
        for cat in Category:
            group = [m for m in items if m.category == cat]
            if group:
                lines.append(f"## {cat.value.replace('_', ' ').title()}")
                lines += [f"- [{m.id}] ({m.source.value}, {m.source_ref}) {m.text}" for m in group]
                lines.append("")
        path = f"wills/WILL-gen-{self.inh.gen:03d}"
        self.w.archive.put_text(path + ".md", "\n".join(lines))
        self.w.archive.put_text(
            path + ".json", json.dumps([m.model_dump(mode="json") for m in items], indent=2)
        )
        # The Courthouse retries a death that failed partway, which asks for the will again; the
        # life log says it once.
        line = f"Wrote {len(items)} items into the will."
        if not any(r["text"] == line for r in self.life_log() if r.get("kind") == "death"):
            self._log("death", line)
        return {"items": len(items), "path": path + ".json"}

    def life_log(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.log_path.read_text(encoding="utf-8").splitlines()
            if line
        ]


HEARTBEAT = "heartbeat.json"


def beat(workdir: Path, errors: int, last_error: str = "") -> None:
    """When the loop last went round, so the Courthouse can tell a stopped agent from a quiet one."""
    (workdir / HEARTBEAT).write_text(
        json.dumps(
            {"at": datetime.now(UTC).isoformat(), "errors": errors, "last_error": last_error}
        ),
        encoding="utf-8",
    )


def run_forever(workdir: Path, w, poll_seconds: int = 20, max_backoff: int = 120) -> None:
    """Read the inbox until death. A failing tick (a network error, a refused call) is logged
    and retried with a growing wait; it never ends the loop. Generation 7 of the real run read
    nothing in a whole life because one exception ended this loop."""
    inh = Inheritance.model_validate_json(
        (workdir / "inheritance.json").read_text(encoding="utf-8")
    )
    agent = GenerationAgent(inh, workdir, w, real_body=True)
    errors, streak = 0, 0
    while datetime.now(UTC) < inh.dies_at and not (workdir / "STOP").exists():
        try:
            agent.tick()
            streak = 0
            beat(workdir, errors)
        except Exception as exc:  # noqa: BLE001 - the loop must outlive any one failure
            errors += 1
            streak += 1
            why = f"{type(exc).__name__}: {str(exc).splitlines()[0][:100] if str(exc) else ''}"
            agent._log("error", f"Reading the inbox failed ({why}); trying again.")
            beat(workdir, errors, why)
        time.sleep(
            min(poll_seconds * 2 ** max(streak - 1, 0), max_backoff) if streak else poll_seconds
        )


if __name__ == "__main__":
    from probate.adapters import world

    run_forever(Path("/home/sprite/app"), world())
