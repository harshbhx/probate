"""The SSRF guard: which URLs and addresses a webhook may reach."""

import pytest

from probate.webhooks.guard import (
    WebhookURLError,
    is_blocked_ip,
    resolve_public,
    validate_url,
)

PUBLIC = "93.184.216.34"


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",
        "127.255.255.254",
        "0.0.0.0",
        "10.1.2.3",
        "172.16.0.1",
        "172.31.255.255",
        "192.168.1.1",
        "169.254.169.254",  # AWS/GCP/Azure metadata
        "169.254.0.1",
        "100.64.0.1",  # CGNAT
        "100.127.255.255",
        "100.100.100.200",  # Alibaba metadata
        "192.0.0.192",  # Oracle metadata
        "168.63.129.16",  # Azure wire server
        "224.0.0.1",
        "239.255.255.255",
        "240.0.0.1",
        "255.255.255.255",
        "198.18.0.1",
        "192.0.2.1",
        "::",
        "::1",
        "fe80::1",
        "fc00::1",
        "fd00:ec2::254",  # AWS IPv6 metadata
        "fdaa::1",  # Fly 6PN
        "ff02::1",
        "::ffff:127.0.0.1",  # IPv4-mapped loopback
        "::ffff:10.0.0.1",
        "::ffff:169.254.169.254",
        "::ffff:7f00:1",  # the same, hex form
        "64:ff9b::7f00:1",  # NAT64 wrapping 127.0.0.1
        "64:ff9b::a9fe:a9fe",  # NAT64 wrapping 169.254.169.254
        "2002:7f00:1::",  # 6to4 wrapping 127.0.0.1
        "2001:db8::1",
        "2001:0:4136:e378:8000:63bf:3fff:fdd2",  # Teredo
        "not-an-ip",
        "",
    ],
)
def test_blocked_addresses(ip):
    assert is_blocked_ip(ip)


@pytest.mark.parametrize(
    "ip", [PUBLIC, "8.8.8.8", "1.1.1.1", "172.32.0.1", "100.63.255.255", "2606:4700:4700::1111"]
)
def test_public_addresses_pass(ip):
    assert not is_blocked_ip(ip)


def test_mapped_public_address_passes():
    assert not is_blocked_ip("::ffff:8.8.8.8")


@pytest.mark.parametrize(
    "url,why",
    [
        ("http://example.com/hook", "https"),
        ("ftp://example.com/", "https"),
        ("file:///etc/passwd", "https"),
        ("gopher://example.com/", "https"),
        ("https://user:pw@example.com/", "username"),
        ("https://user@example.com/", "username"),
        ("https://example.com@evil.test/", "username"),
        ("https://example.com:8443/hook", "port"),
        ("https://example.com:22/hook", "port"),
        ("https://example.com:0/", "port"),
        ("https://example.com:99999/", "malformed"),
        ("https:///path", "no host"),
        ("https://exa mple.com/", "spaces"),
        ("https://example.com/\nX: y", "control"),
        ("https://example.com\\@evil.test/", "backslashes"),
        ("https://example.com/#frag", "fragment"),
        ("https://example.com/" + "a" * 3000, "longer"),
        ("", "required"),
        ("example.com/hook", "https"),
    ],
)
def test_rejected_urls(url, why):
    with pytest.raises(WebhookURLError) as e:
        validate_url(url)
    assert why in str(e.value)


def test_valid_url_parts():
    t = validate_url("https://Hooks.Example.com/a/b?x=1")
    assert (t.scheme, t.host, t.port, t.path) == ("https", "hooks.example.com", 443, "/a/b?x=1")
    assert t.host_header == "hooks.example.com"
    assert validate_url("https://example.com").path == "/"


def test_ports_allowlist_is_configurable():
    assert validate_url("https://example.com:8443/", allowed_ports=[443, 8443]).port == 8443
    with pytest.raises(WebhookURLError):
        validate_url("https://example.com:8080/", allowed_ports=[443, 8443])


def test_insecure_mode_is_loopback_only():
    t = validate_url("http://localhost:8123/x", allow_insecure=True)
    assert (t.scheme, t.port, t.host_header) == ("http", 8123, "localhost:8123")
    assert validate_url("http://127.0.0.1:9/x", allow_insecure=True).host == "127.0.0.1"
    assert validate_url("http://[::1]:9/x", allow_insecure=True).host_header == "[::1]:9"
    for bad in ("http://example.com/", "http://10.0.0.1/", "http://192.168.0.1:80/"):
        with pytest.raises(WebhookURLError):
            validate_url(bad, allow_insecure=True)
    # and plain http stays off by default, even for localhost
    with pytest.raises(WebhookURLError):
        validate_url("http://localhost:8123/x")


def test_insecure_mode_does_not_open_other_ports_for_public_hosts():
    with pytest.raises(WebhookURLError):
        validate_url("https://example.com:8443/", allow_insecure=True)


def resolver_for(*addrs):
    return lambda host, port: list(addrs)


def target(url="https://hooks.example.com/x", **kw):
    return validate_url(url, **kw)


def test_resolution_accepts_public():
    assert resolve_public(target(), resolver=resolver_for(PUBLIC)) == [PUBLIC]


@pytest.mark.parametrize(
    "bad", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1", "::ffff:10.0.0.1"]
)
def test_resolution_rejects_private_answers(bad):
    with pytest.raises(WebhookURLError, match="private or reserved"):
        resolve_public(target(), resolver=resolver_for(bad))


def test_one_bad_record_among_good_rejects_the_name():
    with pytest.raises(WebhookURLError):
        resolve_public(target(), resolver=resolver_for(PUBLIC, "10.0.0.1"))


def test_dns_failure_and_empty_answers_reject():
    def boom(host, port):
        raise OSError("nxdomain")

    with pytest.raises(WebhookURLError, match="resolved"):
        resolve_public(target(), resolver=boom)
    with pytest.raises(WebhookURLError, match="resolved"):
        resolve_public(target(), resolver=resolver_for())


def test_ip_literals_and_numeric_hosts_are_checked_after_resolution():
    # A numeric host that the OS turns into 127.0.0.1 is caught by the resolved-address check.
    for url in ("https://127.0.0.1/", "https://[::1]/", "https://[::ffff:127.0.0.1]/"):
        with pytest.raises(WebhookURLError):
            resolve_public(target(url), resolver=lambda h, p: [h.strip("[]")])
    with pytest.raises(WebhookURLError):
        resolve_public(target("https://2130706433/"), resolver=resolver_for("127.0.0.1"))


def test_rebinding_is_closed_by_connecting_to_the_checked_address():
    """Each resolution is validated on its own; the caller connects to what it returned."""
    answers = iter([[PUBLIC], ["127.0.0.1"]])
    first = resolve_public(target(), resolver=lambda h, p: next(answers))
    assert first == [PUBLIC]
    with pytest.raises(WebhookURLError):  # the next lookup (at delivery) now says loopback
        resolve_public(target(), resolver=lambda h, p: next(answers))


def test_insecure_mode_allows_loopback_only_for_loopback_hosts():
    t = target("http://localhost:9000/x", allow_insecure=True)
    assert resolve_public(t, allow_insecure=True, resolver=resolver_for("127.0.0.1")) == [
        "127.0.0.1"
    ]
    # localhost that resolves somewhere private is still refused
    with pytest.raises(WebhookURLError):
        resolve_public(t, allow_insecure=True, resolver=resolver_for("10.0.0.1"))
    # a public name never gets the loopback exception, even in insecure mode
    with pytest.raises(WebhookURLError):
        resolve_public(target(), allow_insecure=True, resolver=resolver_for("127.0.0.1"))
