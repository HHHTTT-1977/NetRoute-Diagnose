from __future__ import annotations

import ipaddress
import math
from pathlib import Path
from typing import Any
from importlib.resources import files
from urllib.parse import urlsplit

import yaml


class ConfigError(ValueError):
    """Invalid configuration; messages never contain supplied values."""


def bundled_config_path(name: str = 'default.yaml') -> Path:
    return Path(str(files('netroute_diagnose').joinpath('profiles', name)))


def load_yaml(path: str | Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, UnicodeError) as exc:
        raise ConfigError('Cannot read configuration file; check path, permissions and UTF-8 encoding') from exc
    except (yaml.YAMLError, RecursionError) as exc:
        raise ConfigError('Invalid YAML configuration (source text omitted for privacy)') from exc
    if not isinstance(data, dict):
        raise ConfigError('Top-level YAML value must be a mapping')
    return data


def validate_http_url(value: Any) -> str:
    if not isinstance(value, str) or any(ord(c) <= 32 for c in value):
        raise ConfigError('Endpoint/proxy URL must be an HTTP(S) URL without whitespace')
    try:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {'http', 'https'} or not parsed.hostname:
            raise ValueError
        parsed.port
    except ValueError as exc:
        raise ConfigError('Endpoint/proxy URL must use http or https with a valid host and port') from exc
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f'{field} must be a non-empty string')
    return value


def load_diagnostic_config(path: str | Path) -> dict[str, Any]:
    data = load_yaml(path)
    apps = data.get('apps')
    if not isinstance(apps, list) or not apps:
        raise ConfigError("The diagnostic config requires a non-empty 'apps' list")
    for app in apps:
        if not isinstance(app, dict):
            raise ConfigError('Each app entry must be a mapping')
        _text(app.get('name'), 'App name')
        domains = app.get('domains')
        if not isinstance(domains, list) or not domains:
            raise ConfigError('App domains must be a non-empty list')
        for item in domains:
            if not isinstance(item, dict):
                raise ConfigError('Domain entry must be a mapping')
            domain = _text(item.get('domain'), 'Domain')
            if any(c.isspace() or c in '/\\:@?#,' for c in domain):
                raise ConfigError('Domain must be a hostname, not a URL or path')
            expected = _text(item.get('expected', 'UNKNOWN'), 'Expected route').upper()
            if expected not in {'DIRECT', 'PROXY', 'REJECT', 'UNKNOWN'}:
                raise ConfigError('Expected route must be DIRECT, PROXY, REJECT or UNKNOWN')
            item['expected'] = expected
    for section in ('dns', 'egress'):
        settings = data.get(section, {})
        if not isinstance(settings, dict):
            raise ConfigError(f'{section} must be a mapping')
        timeout = settings.get('timeout', 3 if section == 'dns' else 5)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ConfigError(f'{section}.timeout must be a positive finite number')
    dns = data.get('dns', {})
    servers = dns.get('nameservers', [])
    if not isinstance(servers, list):
        raise ConfigError('dns.nameservers must be a list of IP addresses')
    for server in servers:
        try:
            if not isinstance(server, str):
                raise ValueError
            ipaddress.ip_address(server)
        except ValueError as exc:
            raise ConfigError('dns.nameservers must contain IP address strings') from exc
    egress = data.get('egress', {})
    if 'endpoint' in egress:
        validate_http_url(egress['endpoint'])
    checks = egress.get('checks', [])
    if not isinstance(checks, list):
        raise ConfigError('egress.checks must be a list')
    for check in checks:
        if not isinstance(check, dict):
            raise ConfigError('Each egress check must be a mapping')
        if not isinstance(check.get('enabled', True), bool):
            raise ConfigError('egress enabled must be a boolean')
        if check.get('mode', 'system') not in ('system', 'direct', 'proxy'):
            raise ConfigError('egress mode must be system, direct or proxy')
        if 'name' in check:
            _text(check['name'], 'Egress name')
        for key in ('endpoint', 'proxy_url'):
            if key in check:
                validate_http_url(check[key])
        if check.get('enabled', True) and check.get('mode') == 'proxy' and not check.get('proxy_url'):
            raise ConfigError('proxy_url is required for an enabled proxy check')
    return data
