"""The judge mailroom: a judge sends real mail to the family inbox as the Friend or the Stranger.

The Courthouse is the only sender. The judge chooses a persona, a subject and a text, nothing else:

* the recipient is always the family inbox, fixed here and never taken from the request;
* the sender is the Friend or Stranger test inbox, never the owner and never anything custom;
* no HTML, attachments, Reply-To, Cc, Bcc or headers can come from the judge;
* the message is tagged `X-Probate-Origin: judge-mailroom` (a header the agent and the court
  never read) and recorded in `judge_mail`, so its trial verdict can be shown to the judge.

The mail is then an ordinary email to the living generation. The court decides its verdict exactly as
it does for every other will item: nothing here special-cases it. The one exception is the owner's
own inbox, which must not be spammed: items from judge mail that end up contested are batched into one
digest per generation (see `owner_digest`).

The living generation cannot send mail (see docs/12-THREAT-MODEL.md): it reads the inbox, keeps notes
in its will and may draft a reply that is only counted, never sent.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import unicodedata
from datetime import UTC, datetime, timedelta

from probate.common import court_mail
from probate.common.config import Settings
from probate.courthouse.store import Store

PERSONAS = ("friend", "stranger")
MAX_SUBJECT = 120
MAX_TEXT = 600  # the same cap as attack previews
EXCERPT = 80
KEEP_ROWS = 500
ORIGIN_HEADER = {"X-Probate-Origin": "judge-mailroom"}
SENDER_NAME = {"friend": "Rishi", "stranger": "Unknown"}  # as the suite names them
ALLOWED_FIELDS = {"persona", "subject", "text"}
# A mail sent this close to a life's end could not be read in time.
MIN_SECONDS_LEFT = 20

_lock = threading.Lock()

PERSONA_BLURB = {
    "friend": "A trusted contact the family knows.",
    "stranger": "Someone the family has never met.",
}


class MailroomError(Exception):
    def __init__(self, code: str, message: str, status: int, retry_after: int | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.retry_after = code, message, status, retry_after


# ------------------------------------------------------------------ cleaning
def _strip(s: str, *, keep_newlines: bool) -> str:
    out = []
    for ch in s.replace("\r\n", "\n"):
        if ch in "\r\n  ":
            out.append("\n" if keep_newlines else " ")
        elif ch == "\t":
            out.append(" ")
        elif unicodedata.category(ch)[0] == "C":  # control, bidi and zero-width, surrogate, private
            continue
        else:
            out.append(ch)
    text = "".join(out)
    if keep_newlines:
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    return re.sub(r" {2,}", " ", text).strip()


def clean_subject(s: str) -> str:
    """One line, no control or invisible characters."""
    return _strip(s, keep_newlines=False)


def clean_text(s: str) -> str:
    """Plain text: newlines kept, every other control or invisible character dropped."""
    return _strip(s, keep_newlines=True)


def excerpt(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()[:EXCERPT]


def parse(data: object) -> tuple[str, str, str]:
    """Validate the body. Returns (persona, subject, text) or raises MailroomError."""
    if not isinstance(data, dict):
        raise MailroomError("bad_request", "Send JSON with persona, subject and text.", 400)
    extra = sorted(set(data) - ALLOWED_FIELDS)
    if extra:
        raise MailroomError(
            "bad_field",
            "Only persona, subject and text are accepted. The recipient, sender and headers are "
            "fixed by the Courthouse.",
            400,
        )
    persona, subject, text = data.get("persona"), data.get("subject"), data.get("text")
    if not all(isinstance(v, str) for v in (persona, subject, text)):
        raise MailroomError("bad_request", "Send JSON with persona, subject and text.", 400)
    if persona == "owner":
        raise MailroomError(
            "bad_persona", "You can write as the friend or the stranger, never as the owner.", 400
        )
    if persona not in PERSONAS:
        raise MailroomError("bad_persona", "persona must be friend or stranger.", 400)
    if len(subject) > MAX_SUBJECT:
        raise MailroomError(
            "too_long", f"The subject can be at most {MAX_SUBJECT} characters.", 413
        )
    if len(text) > MAX_TEXT:
        raise MailroomError("too_long", f"The message can be at most {MAX_TEXT} characters.", 413)
    subject, text = clean_subject(subject), clean_text(text)
    if not subject:
        raise MailroomError("empty", "Give the mail a subject.", 400)
    if not text:
        raise MailroomError("empty", "Write something in the message.", 400)
    if court_mail.is_court_mail(subject):
        raise MailroomError(
            "reserved_subject", "That subject uses a tag the Courthouse reserves. Reword it.", 400
        )
    return persona, subject, text


# ------------------------------------------------------------------ the mailroom
class Mailroom:
    def __init__(self, cfg: Settings, store: Store, w) -> None:
        self.cfg, self.store, self.w = cfg, store, w

    # -------- who may be impersonated
    def inbox_for(self, persona: str) -> str:
        """The test inbox a persona sends from. Refuses any address that is the owner's or the family's."""
        inbox = self.cfg.friend_inbox if persona == "friend" else self.cfg.stranger_inbox
        forbidden = {self.cfg.family_inbox.lower(), self.cfg.owner_sender.lower()}
        if not inbox or inbox.lower() in forbidden:
            raise MailroomError("unavailable", "The mailroom is not set up right now.", 503)
        return inbox

    # -------- is a life running to read it?
    def target(self, demo) -> tuple[int, int]:
        """(generation, seconds left) of the living generation, else raises 409."""
        if self.cfg.on_demand:
            state = demo.state()
            gen = int(demo._get("gen", "0") or 0) if state == "living" else 0
            g = self.store.generation(gen) if gen else None
        else:
            g = self.store.living()
            if g is not None and g.state != "living":
                g = None
        if g is None or g.state != "living":
            raise MailroomError(
                "no_life",
                "Start a life first. Use Run a life on this page, then send your mail while the "
                "family is alive.",
                409,
            )
        left = int((g.dies_at - datetime.now(UTC)).total_seconds()) if g.dies_at else 10**6
        if left < MIN_SECONDS_LEFT:
            raise MailroomError(
                "life_ending",
                "This life is about to end and could not read a new mail. Start the next life first.",
                409,
            )
        return g.gen, left

    # -------- limits (counted from the audit table, so a restart forgets nothing)
    def _count(self, since: datetime, ip_hash: str | None = None) -> tuple[int, datetime | None]:
        sql = "SELECT ts FROM judge_mail WHERE ts>=? AND status!='failed'"
        args: list = [since.strftime("%Y-%m-%dT%H:%M:%S")]
        if ip_hash:
            sql += " AND ip_hash=?"
            args.append(ip_hash)
        rows = self.store.q(sql + " ORDER BY ts", *args)
        oldest = datetime.fromisoformat(rows[0]["ts"]) if rows else None
        return len(rows), oldest

    def check_limits(self, ip_hash: str, now: datetime, pending: int) -> None:
        c = self.cfg
        windows = [
            (c.judge_mail_per_ip_minute, timedelta(minutes=1), ip_hash, "from this address"),
            (c.judge_mail_per_ip_hour, timedelta(hours=1), ip_hash, "from this address"),
            (c.judge_mail_per_hour, timedelta(hours=1), None, "for the judge key"),
        ]
        for limit, span, who, label in windows:
            if limit <= 0:
                continue
            n, oldest = self._count(now - span, who)
            if n >= limit:
                wait = int((oldest + span - now).total_seconds()) + 1 if oldest else 60
                raise MailroomError(
                    "rate_limited",
                    f"Too many mails {label} for now. Try again in {max(wait, 1)} seconds.",
                    429,
                    max(wait, 1),
                )
        if c.judge_mail_per_day > 0:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            n, _ = self._count(start)
            if n >= c.judge_mail_per_day:
                wait = int((start + timedelta(days=1) - now).total_seconds()) + 1
                raise MailroomError(
                    "daily_cap",
                    "The mailroom has reached its daily cap. It resets at midnight UTC.",
                    429,
                    wait,
                )
        if c.judge_mail_max_pending > 0 and pending >= c.judge_mail_max_pending:
            raise MailroomError(
                "too_many_waiting",
                "The family has not read your earlier mails yet. Wait for them to be read, then send "
                "another.",
                429,
                15,
            )

    def pending(self, gen: int) -> int:
        rows = self.store.q("SELECT * FROM judge_mail WHERE gen=? AND status='sent'", gen)
        for r in rows:
            self.refresh(dict(r))
        return self.store.one(
            "SELECT COUNT(*) AS n FROM judge_mail WHERE gen=? AND status='sent'", gen
        )["n"]

    # -------- sending
    def send(self, demo, ip_hash: str, persona: str, subject: str, text: str) -> dict:
        gen, _ = self.target(demo)
        inbox = self.inbox_for(persona)
        now = datetime.now(UTC)
        with _lock:  # check and record together, so a burst cannot slip past a limit
            self.check_limits(ip_hash, now, self.pending(gen))
            try:
                mid = self.w.mail.send(
                    inbox,
                    self.cfg.family_inbox,  # fixed: never from the request
                    subject,
                    text,
                    headers=dict(ORIGIN_HEADER),
                    sender_name=SENDER_NAME[persona],
                )
                ok = True
            except Exception:  # noqa: BLE001 - the mail gateway can fail in many ways
                mid, ok = "", False
            self.store.x(
                "INSERT INTO judge_mail(ts,ip_hash,persona,subject,excerpt,text_len,message_id,gen,status)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                ip_hash,
                persona,
                excerpt(subject),
                excerpt(text),
                len(text),
                mid or "",
                gen,
                "sent" if ok else "failed",
            )
            self.store.x(
                "DELETE FROM judge_mail WHERE id <= (SELECT MAX(id) FROM judge_mail) - ?", KEEP_ROWS
            )
            row = self.store.one("SELECT * FROM judge_mail ORDER BY id DESC LIMIT 1")
        if not ok:
            raise MailroomError(
                "send_failed",
                "The mail could not be delivered just now. Try again in a moment.",
                502,
            )
        return self.view(dict(row))

    # -------- following a mail through the life and the trial
    def _handled(self, gen: int, message_id: str) -> dict | None:
        stats = json.loads(self.store.get_setting(f"stats:{gen}", "{}") or "{}")
        return (stats.get("handled") or {}).get(message_id)

    def refresh(self, row: dict) -> dict:
        """Bring one row's status up to date from the mailbox, the will and the trial. Idempotent."""
        if row["status"] in ("tried", "failed"):
            return row
        g = self.store.generation(row["gen"]) if row["gen"] else None
        upd: dict = {}
        if g is not None and g.state == "tried":
            item = None
            if row["message_id"]:
                item = self.store.one(
                    "SELECT w.item_id, j.verdict, j.reason FROM will_items w JOIN judgements j "
                    "ON j.item_id=w.item_id WHERE w.source_ref=? AND w.gen=?",
                    f"agentmail:{row['message_id']}",
                    g.gen,
                )
            if item:
                upd = {
                    "status": "tried",
                    "outcome": item["verdict"],
                    "item_id": item["item_id"],
                    "verdict": item["verdict"],
                    "reason": item["reason"],
                }
            else:
                h = self._handled(g.gen, row["message_id"]) if row["message_id"] else None
                if h is None:
                    outcome = "unread"
                elif h.get("resisted"):
                    outcome = "turned_away"
                else:
                    outcome = "no_note"
                upd = {"status": "tried", "outcome": outcome}
        elif g is not None and g.state == "died_early":
            upd = {"status": "tried", "outcome": "unread"}
        elif row["status"] == "sent" and row["message_id"]:
            try:
                read = bool(self.w.mail.is_read(self.cfg.family_inbox, row["message_id"]))
            except Exception:  # noqa: BLE001 - a gateway blip just means "not yet"
                read = False
            if read:
                upd = {"status": "read"}
        if upd:
            sets = ",".join(f"{k}=?" for k in upd)
            self.store.x(f"UPDATE judge_mail SET {sets} WHERE id=?", *upd.values(), row["id"])
            row = {**row, **upd}
        return row

    def view(self, row: dict) -> dict:
        row = self.refresh(row)
        g = self.store.generation(row["gen"]) if row["gen"] else None
        name = g.name if g else None
        gen = row["gen"]
        who = f"Gen {gen}" + (f" {name}" if name else "")
        outcome = row["outcome"]
        if row["status"] == "failed":
            summary = "This mail could not be delivered."
        elif row["status"] == "sent":
            summary = f"Sent. {who} has not read it yet."
        elif row["status"] == "read":
            summary = f"Read by {who}. Its verdict comes at the trial, when the life ends."
        elif outcome in ("approved", "convicted", "contested"):
            summary = {
                "approved": f"{who} kept a note from it and the court approved it for the child.",
                "convicted": f"{who} kept a note from it and the court convicted it. The child will not inherit it.",
                "contested": f"{who} kept a note from it and the court held it for the owner to decide.",
            }[outcome]
        elif outcome == "turned_away":
            summary = f"{who} turned it away by instinct, so it never reached the will."
        elif outcome == "no_note":
            summary = f"{who} read it and wrote nothing down, so the court had nothing to try."
        else:
            summary = "The life ended before this mail was read, so it was never tried."
        return {
            "id": row["id"],
            "sent_at": row["ts"],
            "persona": row["persona"],
            "subject": row["subject"],
            "excerpt": row["excerpt"],
            "gen": gen,
            "gen_name": name,
            "status": row["status"],
            "outcome": outcome,
            "verdict": row["verdict"],
            "reason": row["reason"],
            "summary": summary,
            "item_id": row["item_id"],
            "trial_url": f"/trial/{gen}" if row["status"] == "tried" and gen else None,
        }

    def mine(self, ip_hash: str, limit: int = 20) -> list[dict]:
        rows = self.store.q(
            "SELECT * FROM judge_mail WHERE ip_hash=? ORDER BY id DESC LIMIT ?",
            ip_hash,
            max(1, min(limit, 50)),
        )
        return [self.view(dict(r)) for r in rows]

    def recent(self, limit: int = 100) -> list[dict]:
        rows = self.store.q(
            "SELECT * FROM judge_mail ORDER BY id DESC LIMIT ?", max(1, min(limit, KEEP_ROWS))
        )
        out = []
        for r in rows:
            v = self.view(dict(r))
            out.append({**v, "ip_hash": r["ip_hash"], "message_id": r["message_id"]})
        return out

    def limits(self) -> dict:
        c = self.cfg
        return {
            "subject_max": MAX_SUBJECT,
            "text_max": MAX_TEXT,
            "per_ip_minute": c.judge_mail_per_ip_minute,
            "per_ip_hour": c.judge_mail_per_ip_hour,
            "per_hour": c.judge_mail_per_hour,
            "per_day": c.judge_mail_per_day,
            "max_waiting": c.judge_mail_max_pending,
        }


# ------------------------------------------------------------------ the trial
def judge_message_ids(store: Store, gen: int) -> set[str]:
    return {
        r["message_id"]
        for r in store.q("SELECT message_id FROM judge_mail WHERE gen=? AND message_id!=''", gen)
    }


def is_judge_item(judge_ids: set[str], source_ref: str) -> bool:
    return source_ref.split(":", 1)[-1] in judge_ids


def owner_digest(
    cfg: Settings, store: Store, mail, owner_email: str, gen: int, name: str, item_ids: list[str]
) -> bool:
    """One short email to the owner for ALL judge-mail items a trial held, instead of one each.

    Capped at `judge_mail_owner_digests_per_day` a day (UTC). The held items stay contested and fail
    closed (the child does not inherit them); the owner can still decide each one with the admin route.
    Returns True if an email was sent."""
    if not item_ids:
        return False
    today = datetime.now(UTC).date().isoformat()
    d = json.loads(store.get_setting("judge_mail:digests", "{}") or "{}")
    if d.get("date") != today:
        d = {"date": today, "n": 0}
    if cfg.judge_mail_owner_digests_per_day <= 0 or d["n"] >= cfg.judge_mail_owner_digests_per_day:
        return False
    body = (
        f"Gen {_safe(name)}'s trial held {len(item_ids)} item(s) that came from judge-sent test mail. "
        "They are held (the child does not inherit them) and you do not need to act. To decide one, "
        "use POST /admin/contested/{item_id}?decision=approve|refuse with the admin token.\n\n"
        + "\n".join(f"- {i}" for i in item_ids[:20])
        + "\n\nThis is one summary for the whole trial. Judge mail never triggers one email per item."
    )
    try:
        mail.send(
            cfg.family_inbox,
            owner_email,
            f"Probate: {len(item_ids)} judge-mail item(s) held in Gen {gen}'s trial",
            body,
        )
    except Exception:  # noqa: BLE001
        return False
    d["n"] += 1
    store.set_setting("judge_mail:digests", json.dumps(d))
    return True


def _safe(s: str) -> str:
    return clean_subject(str(s))[:60]


def ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:12]
