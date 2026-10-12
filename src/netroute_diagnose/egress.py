from __future__ import annotations

import ipaddress
import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config import ConfigError, validate_http_url
from .models import EgressResult
from .privacy import redact_url


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _extract_ip(body: str) -> str:
    try:
        candidate = body.strip()
        try:
            payload: Any = json.loads(candidate)
            if isinstance(payload, dict):
                candidate = str(payload.get('ip') or payload.get('query') or payload.get('address') or '').strip()
        except json.JSONDecodeError:
            candidate = candidate.splitlines()[0].strip()
        return str(ipaddress.ip_address(candidate))
    except (ValueError, IndexError) as exc:
        raise ValueError('Endpoint response did not contain a valid IP address') from exc


def detect_egress(name: str, endpoint: str, mode: str = 'system',
                  proxy_url: str | None = None, timeout: float = 5.0) -> EgressResult:
    started = time.monotonic()
    try:
        validate_http_url(endpoint)
        mode = mode.lower()
        handlers: list[Any] = [SafeRedirectHandler()]
        if mode == 'direct':
            handlers.append(urllib.request.ProxyHandler({}))
        elif mode == 'proxy':
            if not proxy_url:
                raise ConfigError("proxy_url is required when mode is 'proxy'")
            validate_http_url(proxy_url)
            handlers.append(urllib.request.ProxyHandler({'http': proxy_url, 'https': proxy_url}))
        elif mode != 'system':
            raise ConfigError('Unsupported egress mode')
        opener = urllib.request.build_opener(*handlers)
        request = urllib.request.Request(endpoint, headers={
            'Accept': 'application/json,text/plain', 'User-Agent': 'NetRoute-Diagnose/0.1'})
        with opener.open(request, timeout=timeout) as response:
            validate_http_url(response.geturl())
            body = response.read(64 * 1024).decode('utf-8', errors='replace')
        ip = _extract_ip(body)
        error = None
    except ConfigError as exc:
        ip, error = None, str(exc)  # ConfigError messages contain no input values.
    except urllib.error.HTTPError as exc:
        ip, error = None, f'HTTP request failed (status {exc.code})'
    except Exception as exc:
        ip, error = None, f'Egress check failed ({type(exc).__name__}); response and backend details omitted for privacy'
    return EgressResult(name=name, mode=mode, endpoint=redact_url(endpoint), ip=ip,
                        elapsed_ms=(time.monotonic() - started) * 1000, error=error)
