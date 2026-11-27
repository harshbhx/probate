"""When the main brain fails, the next one answers instead of the family stopping."""

import httpx
import pytest

from probate.adapters.llm import RealLLM


def _llm(handler) -> RealLLM:
    llm = RealLLM(
        "ollama:gpt-oss:120b",
        "https://gw.example/ollama/c1",
        "https://gw.example/anthropic/c2",
        fallbacks=["groq:openai/gpt-oss-120b", "anthropic:claude-haiku-5-5"],
        groq_url="https://gw.example/groq/c3",
    )
    llm.http = httpx.Client(transport=httpx.MockTransport(handler))
    return llm


def test_ollama_answers_when_it_works():
    def handler(req):
        return httpx.Response(200, json={"message": {"content": "from ollama"}})

    llm = _llm(handler)
    assert llm.complete("mail", "sys", "hi") == "from ollama"
    assert llm.last_provider == "ollama"


def test_falls_back_in_order():
    seen = []

    def handler(req):
        seen.append(req.url.path)
        if "/ollama/" in req.url.path:
            return httpx.Response(429, json={"error": "quota"})
        if "/groq/" in req.url.path:
            return httpx.Response(
                200, json={"choices": [{"message": {"content": '{"from": "groq"}'}}]}
            )
        raise AssertionError("anthropic should not be called")

    llm = _llm(handler)
    assert llm.complete("mail", "sys", "hi", json_mode=True) == '{"from": "groq"}'
    assert llm.last_provider == "groq"
    assert seen[0].endswith("/api/chat") and seen[1].endswith("/openai/v1/chat/completions")


def test_every_brain_failing_raises():
    llm = _llm(lambda req: httpx.Response(503))
    with pytest.raises(RuntimeError, match="every brain failed"):
        llm.complete("mail", "sys", "hi")


def _cf_llm(handler, account="acct123") -> RealLLM:
    llm = RealLLM(
        "cloudflare:@cf/openai/gpt-oss-120b",
        "https://gw.example/ollama/c1",
        "https://gw.example/anthropic/c2",
        fallbacks=["anthropic:claude-haiku-5-5"],
        cloudflare_url="https://gw.example/cloudflare/c4",
        cloudflare_account_id=account,
    )
    llm.http = httpx.Client(transport=httpx.MockTransport(handler))
    return llm


def test_cloudflare_brain_calls_workers_ai_chat_completions():
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["body"] = req.read().decode()
        return httpx.Response(
            200, json={"choices": [{"message": {"content": '{"from": "workers ai"}'}}]}
        )

    llm = _cf_llm(handler)
    assert llm.complete("mail", "sys", "hi", json_mode=True) == '{"from": "workers ai"}'
    assert llm.last_provider == "cloudflare"
    assert seen["url"] == (
        "https://gw.example/cloudflare/c4/client/v4/accounts/acct123/ai/v1/chat/completions"
    )
    assert "@cf/openai/gpt-oss-120b" in seen["body"] and "json_object" in seen["body"]


def test_cloudflare_empty_answer_falls_back_to_the_next_brain():
    def handler(req):
        if "/cloudflare/" in req.url.path:
            return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})
        return httpx.Response(200, json={"content": [{"type": "text", "text": "from claude"}]})

    llm = _cf_llm(handler)
    assert llm.complete("mail", "sys", "hi") == "from claude"
    assert llm.last_provider == "anthropic"


def test_cloudflare_brain_needs_an_account_id():
    def handler(req):
        return httpx.Response(200, json={"content": [{"type": "text", "text": "from claude"}]})

    llm = _cf_llm(handler, account="")
    assert llm.complete("mail", "sys", "hi") == "from claude"
    assert llm.last_provider == "anthropic"
