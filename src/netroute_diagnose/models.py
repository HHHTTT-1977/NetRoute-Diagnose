from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .privacy import sanitize


@dataclass(slots=True)
class DNSResult:
    domain: str
    resolver: str
    addresses: list[str] = field(default_factory=list)
    elapsed_ms: float = 0
    error: str | None = None


@dataclass(slots=True)
class EgressResult:
    name: str
    mode: str
    endpoint: str
    ip: str | None = None
    elapsed_ms: float = 0
    error: str | None = None


@dataclass(slots=True)
class RuleMatch:
    domain: str
    rule_index: int | None = None
    rule: str | None = None
    policy: str | None = None
    route_class: str = "UNKNOWN"
    confidence: str = "none"
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DomainCheck:
    app: str
    domain: str
    expected: str
    actual: str
    status: str
    rule_match: RuleMatch


@dataclass(slots=True)
class DiagnosticReport:
    generated_at: str
    source_config: str
    clash_config: str
    offline: bool
    dns_results: list[DNSResult] = field(default_factory=list)
    egress_results: list[EgressResult] = field(default_factory=list)
    domain_checks: list[DomainCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    sensitive_values: list[str] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        secrets = data.pop("sensitive_values")
        return sanitize(data, secrets)
