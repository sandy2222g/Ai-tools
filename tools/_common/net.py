"""Outbound HTTP guard: blocks requests to private, loopback, and metadata addresses.

Agents that fetch URLs chosen by a model are a classic server-side request forgery
(SSRF) vector: the model can be steered to ``http://169.254.169.254/`` (cloud
metadata), ``http://localhost:…`` or internal services. ``safe_get`` rejects those
targets before connecting and re-validates every redirect hop.

Known limitation: the address is validated before the connection is made, so a
DNS rebinding attack that changes the record between the check and the connect is
not fully prevented. Deployments should also enforce egress rules at the network
layer (see SECURITY.md).
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

ALLOWED_SCHEMES = frozenset({"http", "https"})
MAX_REDIRECTS = 3
REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})


def _is_public(ip: ipaddress._BaseAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_url(url: str) -> str:
    """Return ``url`` if it is an http(s) URL whose host resolves only to public addresses."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError(f"Scheme '{parts.scheme or '(none)'}' is not allowed; use http or https.")
    if not parts.hostname:
        raise ValueError("URL has no host.")
    if parts.username or parts.password:
        raise ValueError("URLs with embedded credentials are not allowed.")
    try:
        port = parts.port or (443 if parts.scheme.lower() == "https" else 80)
    except ValueError as exc:
        raise ValueError(f"Invalid port in URL: {exc}") from exc

    try:
        infos = socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve host '{parts.hostname}': {exc}") from exc

    for info in infos:
        raw = info[4][0].split("%", 1)[0]  # strip IPv6 zone id
        if not _is_public(ipaddress.ip_address(raw)):
            raise ValueError(
                f"Host '{parts.hostname}' resolves to a non-public address; request blocked."
            )
    return url


def safe_get(url: str, *, timeout: float = 10, headers: dict | None = None):
    """GET ``url`` with SSRF protection on the initial URL and on every redirect."""
    import requests  # imported lazily so the guard is usable without the research extras

    current = url
    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(current)
        resp = requests.get(current, headers=headers, timeout=timeout, allow_redirects=False)
        location = resp.headers.get("Location")
        if resp.status_code in REDIRECT_CODES and location:
            resp.close()
            current = urljoin(current, location)
            continue
        return resp
    raise ValueError(f"Too many redirects (limit {MAX_REDIRECTS}).")
