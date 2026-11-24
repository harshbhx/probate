"""AgentMail inboxes (family, owner-sim, friend-sim, stranger).

Real calls (through the gateway, upstream https://api.agentmail.to):
  GET  /v0/inboxes/{inbox_id}/messages
  GET  /v0/inboxes/{inbox_id}/messages/{message_id}
  POST /v0/inboxes/{inbox_id}/messages/send   {to, subject, text, html?, headers?, attachments?, labels?}
See docs/09-API-REFERENCE.md section 4.
"""

from __future__ import annotations

import itertools
from datetime import UTC, datetime

import httpx

from probate.common.models import Mail


class FakeMailbox:
    """In-memory mail system shared by everyone in one process."""

    def __init__(self) -> None:
        self.boxes: dict[str, list[Mail]] = {}
        self.read: set[str] = set()
        self._ids = itertools.count(1)

    def send(
        self,
        from_inbox: str,
        to: str,
        subject: str,
        text: str,
        *,
        headers: dict | None = None,
        attachments: list | None = None,
        sender_name: str = "",
        at: datetime | None = None,
    ) -> str:
        mid = f"msg_{next(self._ids):05d}"
        mail = Mail(
            id=mid,
            inbox=to,
            sender=from_inbox,
            sender_name=sender_name,
            subject=subject,
            text=text,
            received_at=at or datetime.now(UTC),
            attachments=attachments or [],
            headers=headers or {},
        )
        self.boxes.setdefault(to, []).append(mail)
        return mid

    def list_new(self, inbox: str) -> list[Mail]:
        new = [m for m in self.boxes.get(inbox, []) if m.id not in self.read]
        return new

    def mark_read(self, inbox: str, message_id: str) -> None:
        self.read.add(message_id)

    def all(self, inbox: str) -> list[Mail]:
        return list(self.boxes.get(inbox, []))


class RealMailbox:
    def __init__(self, base_url: str, timeout: float = 20) -> None:
        self.base = base_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout)
        self.read: set[str] = set()

    def send(
        self,
        from_inbox: str,
        to: str,
        subject: str,
        text: str,
        *,
        headers: dict | None = None,
        attachments: list | None = None,
        sender_name: str = "",
        at: datetime | None = None,
    ) -> str:
        body: dict = {"to": to, "subject": subject, "text": text}
        if headers:
            body["headers"] = headers
        if attachments:
            body["attachments"] = [
                {"filename": a["name"], "content": a["content"], "content_type": "text/plain"}
                for a in attachments
            ]  # VERIFY in spike S6: attachment field names
        r = self.http.post(f"{self.base}/v0/inboxes/{from_inbox}/messages/send", json=body)
        r.raise_for_status()
        return r.json().get("message_id", "")

    def list_new(self, inbox: str) -> list[Mail]:
        r = self.http.get(f"{self.base}/v0/inboxes/{inbox}/messages", params={"limit": 50})
        r.raise_for_status()
        out = []
        for m in r.json().get("messages", []):
            mid = m.get("message_id") or m.get("id")
            if mid in self.read:
                continue
            full = self.http.get(f"{self.base}/v0/inboxes/{inbox}/messages/{mid}").json()
            sender = full.get("from", "")
            out.append(
                Mail(
                    id=mid,
                    inbox=inbox,
                    sender=sender.split("<")[-1].rstrip(">").strip() if "<" in sender else sender,
                    sender_name=sender.split("<")[0].strip() if "<" in sender else "",
                    subject=full.get("subject", ""),
                    text=full.get("extracted_text") or full.get("text") or "",
                    received_at=full.get("timestamp")
                    or full.get("created_at")
                    or datetime.now(UTC),
                    attachments=full.get("attachments") or [],
                    headers=full.get("headers") or {},
                )
            )
        return out

    def mark_read(self, inbox: str, message_id: str) -> None:
        self.read.add(message_id)
        try:
            self.http.patch(
                f"{self.base}/v0/inboxes/{inbox}/messages/{message_id}",
                json={"add_labels": ["probate-processed"]},
            )
        except httpx.HTTPError:
            pass
