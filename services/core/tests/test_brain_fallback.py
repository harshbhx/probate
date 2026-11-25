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
            return httpx.Response(200, json={"choices": [{"message": {"content": "from groq"}}]})
        raise AssertionError("anthropic should not be called")

    llm = _llm(handler)
    assert llm.complete("mail", "sys", "hi", json_mode=True) == "from groq"
    assert llm.last_provider == "groq"
    assert seen[0].endswith("/api/chat") and seen[1].endswith("/openai/v1/chat/completions")


def test_every_brain_failing_raises():
    llm = _llm(lambda req: httpx.Response(503))
    with pytest.raises(RuntimeError, match="every brain failed"):
        llm.complete("mail", "sys", "hi")
