from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .config import ConfigError, load_yaml
from .models import RuleMatch

DOMAIN_RULES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX"}
UNCERTAIN_RULES = {
    "RULE-SET",
    "GEOSITE",
    "GEOIP",
    "IP-CIDR",
    "IP-CIDR6",
    "SRC-IP-CIDR",
    "PROCESS-NAME",
    "PROCESS-PATH",
    "NETWORK",
    "AND",
    "OR",
    "NOT",
    "SUB-RULE",
}


def load_clash_rules(path: str | Path) -> tuple[list[str], dict[str, Any]]:
    data = load_yaml(path)
    rules = data.get("rules", [])
    if not isinstance(rules, list):
        raise ConfigError(f"'rules' must be a list in {path}")
    cleaned = [str(rule).strip() for rule in rules if str(rule).strip()]
    metadata = {
        "proxy_count": len(data.get("proxies", []) or []),
        "proxy_group_count": len(data.get("proxy-groups", []) or []),
        "rule_count": len(cleaned),
        "rule_provider_count": len(data.get("rule-providers", {}) or {}),
    }
    return cleaned, metadata


def classify_policy(policy: str | None) -> str:
    if not policy:
        return "UNKNOWN"
    normalized = policy.strip().upper()
    if normalized == "DIRECT":
        return "DIRECT"
    if normalized in {"REJECT", "REJECT-DROP"}:
        return "REJECT"
    if normalized in {"PASS", "COMPATIBLE"}:
        return "UNKNOWN"
    return "PROXY"


def _parse_rule(rule: str) -> tuple[str, str | None, str | None]:
    parts = [part.strip() for part in rule.split(",")]
    kind = parts[0].upper() if parts else ""
    if kind in {"MATCH", "FINAL"}:
        return kind, None, parts[1] if len(parts) > 1 else None
    value = parts[1] if len(parts) > 1 else None
    policy = parts[2] if len(parts) > 2 else None
    return kind, value, policy


def _domain_matches(kind: str, value: str, domain: str) -> bool:
    domain = domain.lower().rstrip(".")
    value = value.lower().lstrip("+.").rstrip(".")
    if kind == "DOMAIN":
        return domain == value
    if kind == "DOMAIN-SUFFIX":
        return domain == value or domain.endswith(f".{value}")
    if kind == "DOMAIN-KEYWORD":
        return value in domain
    if kind == "DOMAIN-REGEX":
        try:
            return re.search(value, domain, flags=re.IGNORECASE) is not None
        except re.error:
            return False
    return False


def match_domain(domain: str, rules: list[str]) -> RuleMatch:
    uncertain_before_match: list[str] = []
    invalid_rules: list[str] = []

    for index, raw_rule in enumerate(rules):
        kind, value, policy = _parse_rule(raw_rule)
        matched = False

        if kind in DOMAIN_RULES:
            if value is None or policy is None:
                invalid_rules.append(f"Rule #{index + 1} is incomplete")
                continue
            matched = _domain_matches(kind, value, domain)
        elif kind in {"MATCH", "FINAL"}:
            matched = policy is not None
        elif kind in UNCERTAIN_RULES:
            uncertain_before_match.append(f"#{index + 1} {raw_rule}")
            continue
        else:
            invalid_rules.append(f"Rule #{index + 1} uses unsupported type '{kind}'")
            continue

        if matched:
            notes = invalid_rules.copy()
            confidence = "high"
            if uncertain_before_match:
                confidence = "limited"
                notes.append(
                    "Earlier rules require runtime context or rule-provider data and "
                    "could take precedence: " + "; ".join(uncertain_before_match[:5])
                )
            return RuleMatch(
                domain=domain,
                rule_index=index,
                rule=raw_rule,
                policy=policy,
                route_class=classify_policy(policy),
                confidence=confidence,
                notes=notes,
            )

    notes = invalid_rules
    if uncertain_before_match:
        notes.append(
            "No deterministic domain rule matched; runtime-dependent candidates: "
            + "; ".join(uncertain_before_match[:5])
        )
    return RuleMatch(domain=domain, notes=notes)
