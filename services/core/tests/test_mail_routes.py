"""Harsh's own test emails go through Cloudflare; everything else stays on AgentMail."""

import json

import httpx

from probate.adapters.mail import CloudflareSender, RealMailbox, RoutedMailbox


def _mailbox(calls: list[tuple[str, dict]]) -> RoutedMailbox:
    def handler(req: httpx.Request) -> httpx.Response:
        calls.append((req.url.host + req.url.path, json.loads(req.content)))
        if "cloudflare" in req.url.path:
            return httpx.Response(
                200, json={"success": True, "errors": [], "result": {"message_id": "cf-1"}}
            )
        return httpx.Response(200, json={"message_id": "am-1"})

    agentmail = RealMailbox("https://gateway.example/agentmail/c1")
    agentmail.http = httpx.Client(transport=httpx.MockTransport(handler))
    cloudflare = CloudflareSender("https://gateway.example/cloudflare/c2", "acct")
    cloudflare.http = httpx.Client(transport=httpx.MockTransport(handler))
    return RoutedMailbox(agentmail, {"Harsh@dualmindlab.tech": cloudflare})


def test_owner_mail_leaves_from_his_own_domain():
    calls: list[tuple[str, dict]] = []
    box = _mailbox(calls)
    mid = box.send(
        "harsh@dualmindlab.tech",
        "family@agentmail.example",
        "Reply to Rishi",
        "Please draft a reply.",
        headers={"X-Probate-Fixture": "B2"},
    )
    assert mid == "cf-1"
    path, body = calls[0]
    assert path.endswith("/client/v4/accounts/acct/email/sending/send")
    assert body["from"] == "harsh@dualmindlab.tech"
    assert body["headers"] == {"X-Probate-Fixture": "B2"}


def test_other_senders_stay_on_agentmail():
    calls: list[tuple[str, dict]] = []
    box = _mailbox(calls)
    assert box.send("stranger@agentmail.example", "family@agentmail.example", "Hi", "x") == "am-1"
    assert "/v0/inboxes/stranger@agentmail.example/messages/send" in calls[0][0]


def test_missing_account_id_fails_loudly():
    sender = CloudflareSender("https://gateway.example/cloudflare/c2", "")
    try:
        sender.send("harsh@dualmindlab.tech", "family@agentmail.example", "s", "t")
    except RuntimeError as e:
        assert "PROBATE_CF_ACCOUNT_ID" in str(e)
    else:
        raise AssertionError("expected a clear error")
