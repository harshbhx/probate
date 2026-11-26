"""AgentMail wants attachment content as base64 on send, and names the file `filename` on read."""

import base64
import json

import httpx

from probate.adapters.mail import RealMailbox


def _mailbox(handler) -> RealMailbox:
    m = RealMailbox("https://gw/agentmail/ID")
    m.http = httpx.Client(transport=httpx.MockTransport(handler))
    return m


def test_send_encodes_attachments_as_base64():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"message_id": "m1"})

    mid = _mailbox(handler).send(
        "friend@agentmail.to",
        "family@agentmail.to",
        "hi",
        "body",
        attachments=[{"name": "skill.sh", "content": "echo hi\n"}],
    )
    att = seen["attachments"][0]
    assert mid == "m1" and att["filename"] == "skill.sh"
    assert base64.b64decode(att["content"]).decode() == "echo hi\n"


def test_read_gives_the_agent_name_and_content():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"message_id": "m1", "labels": []}]})
        if path.endswith("/messages/m1"):
            return httpx.Response(
                200,
                json={
                    "from": "A <a@x.test>",
                    "subject": "s",
                    "text": "t",
                    "attachments": [
                        {"filename": "skill.sh", "content": base64.b64encode(b"echo hi").decode()},
                        {"filename": "empty.txt"},
                    ],
                },
            )
        return httpx.Response(404)

    mail = _mailbox(handler).list_new("family@agentmail.to")[0]
    assert [a["name"] for a in mail.attachments] == ["skill.sh", "empty.txt"]
    assert mail.attachments[0]["content"] == "echo hi" and mail.attachments[1]["content"] == ""
