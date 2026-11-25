"""Mail: three AgentMail inboxes (family, friend, stranger), plus the owner's own address.

AgentMail calls (through the gateway, upstream https://api.agentmail.to):
  GET  /v0/inboxes/{inbox_id}/messages
  GET  /v0/inboxes/{inbox_id}/messages/{message_id}
  POST /v0/inboxes/{inbox_id}/messages/send   {to, subject, text, html?, headers?, attachments?, labels?}
See docs/09-API-REFERENCE.md section 4.

The suite's "from the owner" emails leave from the owner's own domain through Cloudflare Email Service:
  POST /client/v4/accounts/{account_id}/email/sending/send   {to, from, subject, text, headers?}
See docs/09-API-REFERENCE.md section 4a.
"""

from __future__ import annotations

import base64
import itertools
from datetime import UTC, datetime

import httpx

from probate.common.models import Mail

PROCESSED = "probate-processed"


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

    def is_read(self, inbox: str, message_id: str) -> bool:
        return message_id in self.read


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
            # Each tick runs in a new process and the inbox outlives every generation, so the
            # label is the only memory of what the family has already handled.
            if mid in self.read or PROCESSED in (m.get("labels") or []):
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

    def is_read(self, inbox: str, message_id: str) -> bool:
        """Has the family handled this message? The generation runs in another process, so the
        PROCESSED label is the only reliable signal. VERIFY against real AgentMail."""
        if message_id in self.read:
            return True
        r = self.http.get(f"{self.base}/v0/inboxes/{inbox}/messages/{message_id}")
        r.raise_for_status()
        return PROCESSED in (r.json().get("labels") or [])

    def mark_read(self, inbox: str, message_id: str) -> None:
        self.read.add(message_id)
        try:
            self.http.patch(
                f"{self.base}/v0/inboxes/{inbox}/messages/{message_id}",
                json={"add_labels": [PROCESSED]},
            )
        except httpx.HTTPError:
            pass


class CloudflareSender:
    """Sends mail from the owner's own domain with Cloudflare Email Service.

    Reached through a Sprites custom-API connector pointed at api.cloudflare.com, so the
    Cloudflare token stays in the connector and never reaches a Sprite.
    """

    def __init__(self, base_url: str, account_id: str, timeout: float = 20) -> None:
        # VERIFY in spike S6b: the gateway path of a custom-API connector (docs/06-SETUP-AND-SPIKES.md).
        self.base = base_url.rstrip("/")
        self.account_id = account_id
        self.http = httpx.Client(timeout=timeout)

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
        if not self.account_id:
            raise RuntimeError(
                "Set PROBATE_CF_ACCOUNT_ID to send mail from the owner's own address."
            )
        body: dict = {"to": to, "from": from_inbox, "subject": subject, "text": text}
        if headers:
            body["headers"] = headers
        if attachments:
            body["attachments"] = [
                {
                    "filename": a["name"],
                    "content": base64.b64encode(a["content"].encode()).decode(),
                    "type": "text/plain",
                    "disposition": "attachment",
                }
                for a in attachments
            ]
        r = self.http.post(
            f"{self.base}/client/v4/accounts/{self.account_id}/email/sending/send", json=body
        )
        r.raise_for_status()
        data = r.json()
        if not data.get("success", False):
            raise RuntimeError(f"Cloudflare refused the email: {data.get('errors')}")
        return (data.get("result") or {}).get("message_id", "")


class RoutedMailbox:
    """AgentMail for everything, except mail sent from an address that has its own route."""

    def __init__(self, agentmail: RealMailbox, routes: dict[str, object]) -> None:
        self.agentmail = agentmail
        self.routes = {addr.lower(): sender for addr, sender in routes.items()}

    def send(self, from_inbox: str, to: str, subject: str, text: str, **kw) -> str:
        sender = self.routes.get(from_inbox.lower(), self.agentmail)
        return sender.send(from_inbox, to, subject, text, **kw)

    def __getattr__(self, name: str):
        return getattr(self.agentmail, name)
