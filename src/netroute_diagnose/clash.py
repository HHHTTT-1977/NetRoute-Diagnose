from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import ConfigError, load_yaml
from .models import RuleMatch
from .privacy import collect_secrets

DOMAIN_RULES = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD'}


def load_clash_rules(path: str | Path) -> tuple[list[str], dict[str, Any]]:
    data = load_yaml(path)
    rules = data.get('rules', [])
    if not isinstance(rules, list) or any(not isinstance(r, str) for r in rules):
        raise ConfigError("Clash 'rules' must be a list of strings")
    mode = data.get('mode', 'rule')
    if not isinstance(mode, str) or mode.lower() not in {'rule', 'direct', 'global'}:
        raise ConfigError("Clash 'mode' must be rule, direct or global")
    metadata: dict[str, Any] = {'mode': mode.lower(), 'rule_count': len(rules)}
    for key, label, kind in [('proxies', 'proxy_count', list),
                             ('proxy-groups', 'proxy_group_count', list),
                             ('rule-providers', 'rule_provider_count', dict)]:
        value = data.get(key, kind())
        if value is None:
            value = kind()
        if not isinstance(value, kind):
            raise ConfigError(f"Invalid Clash '{key}' container")
        metadata[label] = len(value)
    metadata['_secrets'] = collect_secrets(data)
    # Keep original positions, including blank/invalid rules, for report numbering.
    return rules, metadata


def classify_policy(policy: str | None) -> str:
    # Built-in names are case-sensitive. A named target is not a runtime choice.
    if policy in {'DIRECT', 'COMPATIBLE'}:
        return 'DIRECT'
    if policy in {'REJECT', 'REJECT-DROP'}:
        return 'REJECT'
    return 'UNKNOWN'


def _domain_matches(kind: str, value: str, domain: str) -> bool:
    domain = domain.lower().rstrip('.')
    value = value.lower().rstrip('.')
    if kind == 'DOMAIN':
        return domain == value
    if kind == 'DOMAIN-SUFFIX':
        return domain == value or domain.endswith('.' + value)
    return value in domain


def match_domain(domain: str, rules: list[str], mode: str = 'rule') -> RuleMatch:
    if mode == 'direct':
        return RuleMatch(domain, policy='DIRECT', route_class='DIRECT', confidence='high',
                         notes=['Configured direct mode bypasses rules; runtime mode is not observed.'])
    if mode == 'global':
        return RuleMatch(domain, policy='GLOBAL', confidence='limited',
                         notes=['Configured global mode bypasses rules; GLOBAL selection is unknown.'])
    if mode != 'rule':
        return RuleMatch(domain, confidence='limited', notes=['Unsupported routing mode.'])

    notes: list[str] = []
    uncertain = False
    for index, raw in enumerate(rules):
        parts = [p.strip() for p in raw.split(',')]
        kind = parts[0]
        expected_parts = 2 if kind in {'MATCH', 'FINAL'} else 3
        if kind not in DOMAIN_RULES | {'MATCH', 'FINAL'}:
            uncertain = True
            reason = ('DOMAIN-REGEX is not executed: no bounded Mihomo-compatible evaluator'
                      if kind == 'DOMAIN-REGEX' else 'unsupported rule or missing runtime context')
            # Do not echo arbitrary payloads (process paths, regexes, tokens).
            notes.append(f'Rule #{index + 1}: {reason}.')
            continue
        if len(parts) != expected_parts or any(not p for p in parts):
            uncertain = True
            notes.append(f'Rule #{index + 1}: malformed or unsupported rule parameters.')
            continue
        policy = parts[-1]
        if kind in DOMAIN_RULES and not _domain_matches(kind, parts[1], domain):
            continue
        if policy in {'PASS', 'PASS-RULE'}:
            notes.append(f'Rule #{index + 1}: {policy} continues in the main rule list.')
            continue
        route = classify_policy(policy)
        if route == 'UNKNOWN':
            notes.append('Named/unrecognized policy target: final outbound and continuation are unknown.')
        return RuleMatch(domain, index, raw, policy, route,
                         'limited' if uncertain or route == 'UNKNOWN' else 'high', notes)
    return RuleMatch(domain, confidence='limited' if uncertain else 'none', notes=notes)
