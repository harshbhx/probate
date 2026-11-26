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
