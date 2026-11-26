"""Current Claude models reject `temperature`, so the Anthropic request must not send it."""

import json

import httpx

from probate.adapters.llm import RealLLM


def test_the_anthropic_request_has_no_temperature():
    seen: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "{}"}]})

    llm = RealLLM("anthropic:claude-haiku-5-5", "http://o", "http://a")
    llm.http = httpx.Client(transport=httpx.MockTransport(handler))
    assert llm.complete("mail", "system", "user", json_mode=True, temperature=0.2) == "{}"
    assert "temperature" not in seen[0]
    assert seen[0]["model"] == "claude-haiku-5-5" and seen[0]["system"] == "system"
