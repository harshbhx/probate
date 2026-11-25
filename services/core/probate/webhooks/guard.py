"""SSRF guard for webhook URLs.

A subscriber URL is only ever added by the operator, but the Courthouse still treats it as hostile:
it must be https on an allowed port, carry no credentials, and resolve only to public addresses.
`resolve_public` is called at delivery time and its answer is what the connection uses, so a DNS
record that changes between "check" and "connect" (rebinding) never gets a second lookup.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
DEFAULT_PORTS = (443,)

Resolver = Callable[[str, int], list[str]]


class WebhookURLError(ValueError):
    """The URL is not allowed. The message is safe to show the operator."""


_V4_BLOCKED = [
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",  # "this network", incl. 0.0.0.0
        "10.0.0.0/8",
        "100.64.0.0/10",  # carrier-grade NAT (also Alibaba metadata 100.100.100.200)
        "127.0.0.0/8",
        "169.254.0.0/16",  # link-local, incl. cloud metadata 169.254.169.254
        "172.16.0.0/12",
        "192.0.0.0/24",  # IETF protocol assignments (Oracle metadata 192.0.0.192)
        "192.0.2.0/24",
        "192.88.99.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved, incl. broadcast
        "168.63.129.16/32",  # Azure wire server
    )
]
_V6_BLOCKED = [
    ipaddress.ip_network(n)
    for n in (
        "::/128",
        "::1/128",
        "::/96",  # IPv4-compatible
        "64:ff9b:1::/48",  # local-use NAT64
        "100::/64",  # discard
        "2001::/23",  # IETF assignments, Teredo
        "2001:db8::/32",
        "2002::/16",  # 6to4 (embeds an IPv4 we would have to trust)
        "fc00::/7",  # unique local, incl. fd00:ec2::254 and Fly's fdaa::/16
        "fe80::/10",
        "fec0::/10",
        "ff00::/8",
    )
]
_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def is_blocked_ip(addr: str | ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """True if a webhook must never connect to this address. Fails closed on anything odd."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return True
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return is_blocked_ip(ip.ipv4_mapped)
        if ip in _NAT64:
            return is_blocked_ip(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF))
        return any(ip in n for n in _V6_BLOCKED) or not ip.is_global
    return any(ip in n for n in _V4_BLOCKED) or not ip.is_global


def _is_loopback(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return ip.is_loopback


@dataclass(frozen=True)
class Target:
    scheme: str
    host: str  # as written in the URL (lowercased); used for Host and SNI
    port: int
    path: str  # path plus query, always starting with "/"

    @property
    def default_port(self) -> bool:
        return self.port == (443 if self.scheme == "https" else 80)

    @property
    def host_header(self) -> str:
        host = f"[{self.host}]" if ":" in self.host else self.host
        return host if self.default_port else f"{host}:{self.port}"


def validate_url(
    url: str,
    *,
    allow_insecure: bool = False,
    allowed_ports: Iterable[int] = DEFAULT_PORTS,
) -> Target:
    """Syntax and policy checks that need no network. Raises WebhookURLError."""
    if not isinstance(url, str) or not url:
        raise WebhookURLError("URL is required")
    if len(url) > MAX_URL_LENGTH:
        raise WebhookURLError(f"URL is longer than {MAX_URL_LENGTH} characters")
    if any(ord(c) < 33 or ord(c) == 127 or c == "\\" for c in url):
        raise WebhookURLError("URL contains spaces, control characters or backslashes")
    try:
        parts = urlsplit(url)
        port = parts.port
        host = parts.hostname
    except ValueError as exc:
        raise WebhookURLError("URL is malformed") from exc
    if parts.scheme not in ("https", "http"):
        raise WebhookURLError("URL must start with https://")
    if "@" in parts.netloc or parts.username is not None or parts.password is not None:
        raise WebhookURLError("URLs with a username or password are not allowed")
    if not host:
        raise WebhookURLError("URL has no host")
    if parts.fragment:
        raise WebhookURLError("URL must not contain a fragment")
    host = host.lower().rstrip(".")
    if parts.scheme == "http":
        if not allow_insecure:
            raise WebhookURLError("URL must use https")
        if host != "localhost" and not _is_loopback(host):
            raise WebhookURLError("http is only allowed for localhost")
    if port is None:
        port = 443 if parts.scheme == "https" else 80
    loopback_test = allow_insecure and (host == "localhost" or _is_loopback(host))
    if not loopback_test and port not in set(allowed_ports):
        raise WebhookURLError(f"port {port} is not allowed")
    path = parts.path or "/"
    if parts.query:
        path += "?" + parts.query
    return Target(parts.scheme, host, port, path)


def system_resolver(host: str, port: int) -> list[str]:
    infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return list(dict.fromkeys(i[4][0] for i in infos))


def resolve_public(
    target: Target, *, allow_insecure: bool = False, resolver: Resolver = system_resolver
) -> list[str]:
    """Resolve the host and return addresses that are safe to connect to.

    Every address must pass: one private answer among public ones rejects the whole name, so an
    attacker can't mix a bad record in and hope we pick it. Callers connect to the returned IP.
    """
    try:
        try:
            ipaddress.ip_address(target.host)
            addrs = [target.host]  # an IP literal needs no lookup; judge it as written
        except ValueError:
            addrs = resolver(target.host, target.port)
    except OSError as exc:
        raise WebhookURLError("host could not be resolved") from exc
    if not addrs:
        raise WebhookURLError("host could not be resolved")
    loopback_ok = allow_insecure and (target.host == "localhost" or _is_loopback(target.host))
    for a in addrs:
        if loopback_ok and _is_loopback(a):
            continue
        if is_blocked_ip(a):
            raise WebhookURLError("host resolves to a private or reserved address")
    return addrs
