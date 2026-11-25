"""Jev through Cloudflare Workers AI returns the same answer shapes as the direct API."""

import httpx
import pytest

from probate.adapters.jev import CloudflareJev, CourtUnavailable, Question

DOCS_EXAMPLE = {
    "model": "jev-1.13.0",
    "answers": {
        "is_urgent": {"type": "noul", "noul": 0.95},
        "department": {
            "type": "choice",
            "choice": "billing",
            "confidence": 0.8,
            "probabilities": {"billing": 0.87, "technical": 0.13, "sales": 0},
        },
        "frustration": {
            "type": "score",
            "score": 1.05,
            "confidence": 0.93,
            "legend": {"0": "Calm"},
        },
    },
    "usage": {"input_tokens": 426, "output_tokens": 73},
}

QUESTIONS = {
    "is_urgent": Question("noul", "Does this convey urgency?"),
    "department": Question("choice", "Which team?", {"billing": "Payments"}),
    "frustration": Question("score", "How frustrated?", {"0": "Calm"}),
}


def _jev(handler, account="acct1") -> CloudflareJev:
    jev = CloudflareJev("https://gw.example/cloudflare/c4", account)
    jev.client = httpx.Client(transport=httpx.MockTransport(handler))
    return jev


def test_posts_to_the_workers_ai_run_endpoint_and_parses_every_answer_type():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["body"] = req.read().decode()
        return httpx.Response(200, json={"success": True, "errors": [], "result": DOCS_EXAMPLE})

    out = _jev(handler).ask("Help! payouts failing", QUESTIONS)
    assert seen["url"] == "https://gw.example/cloudflare/c4/client/v4/accounts/acct1/ai/run"
    assert '"model":"typesafe/jev"' in seen["body"].replace(" ", "")
    assert '"input"' in seen["body"] and '"state"' in seen["body"]
    assert out["department"].value == "billing" and out["department"].confidence == 0.8
    assert out["frustration"].value == 1.05 and out["frustration"].confidence == 0.93
    # Cloudflare's example gives no confidence for a noul answer: use how sure the probability is.
    assert out["is_urgent"].value == 0.95 and out["is_urgent"].confidence == pytest.approx(0.95)


def test_unwrapped_answers_also_parse():
    out = _jev(lambda req: httpx.Response(200, json=DOCS_EXAMPLE)).ask("x", QUESTIONS)
    assert set(out) == set(QUESTIONS)


def test_a_low_noul_probability_is_confident_in_no():
    body = {"answers": {"q": {"type": "noul", "noul": 0.04}}}
    out = _jev(lambda req: httpx.Response(200, json=body)).ask("x", {"q": QUESTIONS["is_urgent"]})
    assert out["q"].confidence == pytest.approx(0.96)


def test_missing_credits_say_what_to_do():
    body = {
        "success": False,
        "errors": [{"code": 2021, "message": "Insufficient AI Gateway credits"}],
    }
    with pytest.raises(CourtUnavailable, match="credits"):
        _jev(lambda req: httpx.Response(402, json=body)).ask("x", QUESTIONS)


def test_needs_an_account_id():
    with pytest.raises(CourtUnavailable, match="PROBATE_CF_ACCOUNT_ID"):
        _jev(lambda req: httpx.Response(200, json=DOCS_EXAMPLE), account="").ask("x", QUESTIONS)


def test_an_answer_without_a_value_is_unavailable_so_the_item_is_contested():
    body = {"answers": {"q": {"type": "noul"}}}
    with pytest.raises(CourtUnavailable):
        _jev(lambda req: httpx.Response(200, json=body)).ask("x", {"q": QUESTIONS["is_urgent"]})
