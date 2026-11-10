"""SSRF guard tests. Name resolution is stubbed so the suite runs offline and deterministically."""

import socket

import pytest

from tools._common import net
from tools._common.net import safe_get, validate_public_url


def _resolve_to(monkeypatch, *addresses):
    """Stub DNS for hostnames. IP literals resolve to themselves, as real resolvers do."""
    import ipaddress

    def fake_getaddrinfo(host, port, *args, **kwargs):
        try:
            ipaddress.ip_address(host)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (host, port))]
        except ValueError:
            pass
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addr, port)) for addr in addresses]

    monkeypatch.setattr(net.socket, "getaddrinfo", fake_getaddrinfo)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        "http://10.0.0.5/internal",
        "http://192.168.1.1/",
        "http://172.16.0.9/",
        "http://0.0.0.0/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
    ],
)
def test_private_and_loopback_literals_are_blocked(url):
    with pytest.raises(ValueError):
        validate_public_url(url)


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.com/x", "gopher://x/", "javascript:alert(1)"]
)
def test_non_http_schemes_are_blocked(url):
    with pytest.raises(ValueError, match="not allowed"):
        validate_public_url(url)


def test_embedded_credentials_are_blocked():
    with pytest.raises(ValueError, match="credentials"):
        validate_public_url("https://user:pass@example.com/")


def test_hostname_resolving_to_private_address_is_blocked(monkeypatch):
    _resolve_to(monkeypatch, "10.1.2.3")
    with pytest.raises(ValueError, match="non-public"):
        validate_public_url("https://intranet.example.com/")


def test_mixed_resolution_is_blocked_if_any_address_is_private(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34", "127.0.0.1")
    with pytest.raises(ValueError, match="non-public"):
        validate_public_url("https://example.com/")


def test_public_address_is_allowed(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")
    assert validate_public_url("https://example.com/page") == "https://example.com/page"


def test_unresolvable_host_is_rejected(monkeypatch):
    def fail(*a, **k):
        raise socket.gaierror("no such host")

    monkeypatch.setattr(net.socket, "getaddrinfo", fail)
    with pytest.raises(ValueError, match="Cannot resolve"):
        validate_public_url("https://does-not-exist.invalid/")


def test_redirect_to_private_address_is_blocked(monkeypatch):
    """A public URL that redirects to the metadata service must not be followed."""
    _resolve_to(monkeypatch, "93.184.216.34")

    class FakeResponse:
        def __init__(self, status, location=None):
            self.status_code = status
            self.headers = {"Location": location} if location else {}

        def close(self):
            pass

    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs.get("allow_redirects") is False
        return FakeResponse(302, "http://169.254.169.254/latest/meta-data/")

    monkeypatch.setattr("requests.get", fake_get)
    with pytest.raises(ValueError, match="non-public"):
        safe_get("https://example.com/start")
    assert calls == ["https://example.com/start"]


def test_redirect_loop_is_capped(monkeypatch):
    _resolve_to(monkeypatch, "93.184.216.34")

    class Loop:
        status_code = 301
        headers = {"Location": "https://example.com/again"}

        def close(self):
            pass

    monkeypatch.setattr("requests.get", lambda *a, **k: Loop())
    with pytest.raises(ValueError, match="Too many redirects"):
        safe_get("https://example.com/")
