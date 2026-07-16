from __future__ import annotations

import socket
import time

from .models import DNSResult


def resolve_domain(
    domain: str, nameserver: str | None = None, timeout: float = 3.0
) -> DNSResult:
    started = time.monotonic()
    resolver_name = nameserver or "system"
    try:
        if nameserver:
            try:
                import dns.resolver
            except ImportError as exc:
                raise RuntimeError(
                    "Custom DNS checks require the optional dnspython dependency"
                ) from exc
            resolver = dns.resolver.Resolver(configure=False)
            resolver.nameservers = [nameserver]
            resolver.timeout = timeout
            resolver.lifetime = timeout
            addresses: set[str] = set()
            errors: list[str] = []
            for record_type in ("A", "AAAA"):
                try:
                    answer = resolver.resolve(domain, record_type)
                    addresses.update(str(record) for record in answer)
                except Exception as exc:  # DNS backends expose several exception types
                    errors.append(f"{record_type}: {exc}")
            if not addresses:
                raise RuntimeError("; ".join(errors))
        else:
            previous_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(timeout)
            try:
                info = socket.getaddrinfo(domain, None, type=socket.SOCK_STREAM)
            finally:
                socket.setdefaulttimeout(previous_timeout)
            addresses = {item[4][0] for item in info}
        return DNSResult(
            domain=domain,
            resolver=resolver_name,
            addresses=sorted(addresses),
            elapsed_ms=(time.monotonic() - started) * 1000,
        )
    except Exception as exc:
        return DNSResult(
            domain=domain,
            resolver=resolver_name,
            elapsed_ms=(time.monotonic() - started) * 1000,
            error=str(exc),
        )
