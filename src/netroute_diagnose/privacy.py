"""One serialization boundary for HTML, JSON and diagnostic text.

Domains, IPs and policy labels remain useful diagnostic data, not anonymous data.
"""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from typing import Any

_SECRET_KEY = re.compile(r'password|passwd|token|secret|authorization|api[-_]?key|credential', re.I)
_URL = re.compile(r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>\"\']+')
_PATH = re.compile(r'(?<![\w:])(?:[A-Za-z]:[\\/]|\\\\|/)[^\r\n<>\"\',;]+')
_ASSIGNMENT = re.compile(r'(?i)((?:password|passwd|token|secret|api[-_]?key|authorization)\s*[:=]\s*)(?:\"[^\"]*\"|\'[^\']*\'|[^\s,;]+)')


def collect_secrets(value: Any) -> list[str]:
    found: set[str] = set()
    seen: set[int] = set()
    def visit(item: Any) -> None:
        if isinstance(item, (dict, list)):
            if id(item) in seen:
                return
            seen.add(id(item))
        if isinstance(item, dict):
            for key, val in item.items():
                if _SECRET_KEY.search(str(key)) and isinstance(val, (str, int)):
                    found.add(str(val))
                else:
                    visit(val)
        elif isinstance(item, list):
            for val in item:
                visit(val)
        elif isinstance(item, str):
            for match in _URL.finditer(item):
                try:
                    url = urlsplit(match.group())
                    found.update(unquote(v) for v in (url.username, url.password) if v)
                    found.update(v for k, v in parse_qsl(url.query) if _SECRET_KEY.search(k))
                except ValueError:
                    pass
    visit(value)
    return sorted((s for s in found if s), key=len, reverse=True)


def redact_url(url: str) -> str:
    if not isinstance(url, str):
        return '[invalid URL]'
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname:
            return '[redacted URL]'
        host = parsed.hostname
        if ':' in host:
            host = '[' + host + ']'
        if parsed.port is not None:
            host += ':' + str(parsed.port)
        # Paths and fragments can contain bearer credentials, too.
        path = parsed.path if parsed.path in {'', '/', '/ip', '/json', '/ip.json'} else '/[redacted-path]'
        query = urlencode([(k, v if k == 'format' and v in {'json', 'text'} else '[redacted]')
                           for k, v in parse_qsl(parsed.query, keep_blank_values=True)])
        return urlunsplit((parsed.scheme.lower(), host, path, query, ''))
    except ValueError:
        return '[redacted URL]'


def sanitize_text(value: str, secrets: list[str] | tuple[str, ...] = ()) -> str:
    # Protect URL syntax from path redaction; never reintroduce unsanitized URLs.
    urls: list[str] = []
    def replace_url(match: re.Match[str]) -> str:
        urls.append(redact_url(match.group()))
        return f'\x00URL{len(urls)-1}\x00'
    value = _URL.sub(replace_url, value)
    value = _PATH.sub('[redacted-path]', value)
    value = re.sub(r'(?i)\bBearer\s+[^\s,;]+', 'Bearer [redacted]', value)
    value = _ASSIGNMENT.sub(lambda m: m.group(1) + '[redacted]', value)
    for index, url in enumerate(urls):
        value = value.replace(f'\x00URL{index}\x00', url)
    for secret in secrets:
        if len(secret) < 4:
            value = re.sub(r'(?<!\w)' + re.escape(secret) + r'(?!\w)', '[redacted]', value)
        else:
            value = value.replace(secret, '[redacted]')
    return value


def sanitize(value: Any, secrets: list[str] | tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        return {sanitize_text(str(k), secrets): '[redacted]' if _SECRET_KEY.search(str(k))
                else sanitize(v, secrets) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v, secrets) for v in value]
    if isinstance(value, str):
        return sanitize_text(value, secrets)
    return value
