from __future__ import annotations

import ipaddress
import json
import time
import urllib.request
from typing import Any

from .models import EgressResult


def _extract_ip(body: str) -> str:
    candidate = body.strip()
    try:
        payload: Any = json.loads(candidate)
        if isinstance(payload, dict):
            candidate = str(
                payload.get("ip")
                or payload.get("query")
                or payload.get("address")
                or ""
            ).strip()
    except json.JSONDecodeError:
        candidate = candidate.splitlines()[0].strip()
    return str(ipaddress.ip_address(candidate))


def detect_egress(
    name: str,
    endpoint: str,
    mode: str = "system",
    proxy_url: str | None = None,
    timeout: float = 5.0,
) -> EgressResult:
    started = time.monotonic()
    mode = mode.lower()
    try:
        if mode == "direct":
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        elif mode == "proxy":
            if not proxy_url:
                raise ValueError("proxy_url is required when mode is 'proxy'")
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler(
                    {"http": proxy_url, "https": proxy_url}
                )
            )
        elif mode == "system":
            opener = urllib.request.build_opener()
        else:
            raise ValueError(f"Unsupported egress mode: {mode}")

        request = urllib.request.Request(
            endpoint,
            headers={"Accept": "application/json,text/plain", "User-Agent": "NetRoute-Diagnose/0.1"},
        )
        with opener.open(request, timeout=timeout) as response:
            body = response.read(64 * 1024).decode("utf-8", errors="replace")
        return EgressResult(
            name=name,
            mode=mode,
            endpoint=endpoint,
            ip=_extract_ip(body),
            elapsed_ms=(time.monotonic() - started) * 1000,
        )
    except Exception as exc:
        return EgressResult(
            name=name,
            mode=mode,
            endpoint=endpoint,
            elapsed_ms=(time.monotonic() - started) * 1000,
            error=str(exc),
        )
