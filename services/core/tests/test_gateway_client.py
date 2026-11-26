"""Gateway clients must not reuse kept-alive connections (stale ones fail with SSL EOF)."""

from probate.adapters.llm import RealLLM
from probate.adapters.mail import RealMailbox
from probate.common.http import gateway_client


def test_gateway_client_keeps_no_connections_alive():
    client = gateway_client(timeout=5)
    pool = client._transport._pool
    assert pool._max_keepalive_connections == 0


def test_adapters_use_it():
    for http in (
        RealLLM("anthropic:m", "http://o", "http://a").http,
        RealMailbox("http://a").http,
    ):
        assert http._transport._pool._max_keepalive_connections == 0


def test_model_and_decision_requests_are_repeatable():
    from probate.adapters.jev import CloudflareJev, RealJev

    assert RealLLM("anthropic:m", "http://o", "http://a").http.retry_all is True
    assert RealJev("http://x").client.retry_all is True
    assert CloudflareJev("http://x", "acct").client.retry_all is True
    from probate.adapters.mail import RealMailbox

    assert RealMailbox("http://a").http.retry_all is False  # a send must not be repeated
