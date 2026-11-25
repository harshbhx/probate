"""Live mode: a new process must not re-handle mail the family already processed."""

import httpx

from probate.adapters.mail import PROCESSED, RealMailbox


def test_processed_label_is_the_familys_memory():
    listing = {
        "messages": [
            {"message_id": "m1", "labels": ["received", PROCESSED]},
            {"message_id": "m2", "labels": ["received"]},
        ]
    }

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/messages"):
            return httpx.Response(200, json=listing)
        mid = req.url.path.rsplit("/", 1)[-1]
        return httpx.Response(
            200, json={"from": "Owner <harsh@example.com>", "subject": mid, "text": "hi"}
        )

    box = RealMailbox("https://gateway.example/agentmail/c1")
    box.http = httpx.Client(transport=httpx.MockTransport(handler))
    new = box.list_new("family@agentmail.example")
    assert [m.id for m in new] == ["m2"]
    assert new[0].sender == "harsh@example.com"
