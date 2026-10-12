from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .clash import load_clash_rules, match_domain
from .config import load_diagnostic_config
from .dns import resolve_domain
from .egress import detect_egress
from .models import DiagnosticReport, DomainCheck
from .privacy import collect_secrets


def _domain_inventory(config: dict[str, Any]) -> list[str]:
    return list(
        dict.fromkeys(
            str(item["domain"]).lower().rstrip(".")
            for app in config["apps"]
            for item in app["domains"]
        )
    )


def run_diagnostics(
    diagnostic_config: str | Path,
    clash_config: str | Path,
    offline: bool = False,
) -> DiagnosticReport:
    config = load_diagnostic_config(diagnostic_config)
    rules, clash_metadata = load_clash_rules(clash_config)
    domains = _domain_inventory(config)
    report = DiagnosticReport(
        generated_at=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        # Reports may be shared publicly. Keep filenames for traceability without
        # exposing a user's home directory or local folder layout.
        source_config=Path(diagnostic_config).name,
        clash_config=Path(clash_config).name,
        offline=offline,
        sensitive_values=clash_metadata.pop("_secrets") + collect_secrets(config),
        metadata=clash_metadata,
    )

    for app in config["apps"]:
        for item in app["domains"]:
            rule_match = match_domain(item["domain"], rules, mode=clash_metadata["mode"])
            expected = item["expected"]
            actual = rule_match.route_class
            if rule_match.confidence == "limited":
                status = "UNCERTAIN"
            elif actual == "UNKNOWN" or expected == "UNKNOWN":
                status = "UNKNOWN"
            elif actual == expected:
                status = "PASS"
            else:
                status = "MISMATCH"
            report.domain_checks.append(
                DomainCheck(
                    app=str(app["name"]),
                    domain=str(item["domain"]),
                    expected=expected,
                    actual=actual,
                    status=status,
                    rule_match=rule_match,
                )
            )

    if offline:
        report.warnings.append(
            "Offline mode: DNS and egress checks were skipped; route results are static rule analysis only."
        )
        return report

    report.warnings.append(
        "DNS and egress are independent observations from this device. An IP-service request "
        "does not establish an app domain route; direct HTTP mode does not bypass TUN or transparent proxies."
    )
    dns_config = config.get("dns", {})
    nameservers = dns_config.get("nameservers") or [None]
    timeout = float(dns_config.get("timeout", 3))
    if nameservers == [None]:
        report.warnings.append("System DNS uses OS resolver timeouts; dns.timeout does not bound getaddrinfo.")
    for domain in domains:
        for nameserver in nameservers:
            report.dns_results.append(
                resolve_domain(domain, nameserver=nameserver, timeout=timeout)
            )

    egress_config = config.get("egress", {})
    endpoint = str(egress_config.get("endpoint", "https://api.ipify.org?format=json"))
    egress_timeout = float(egress_config.get("timeout", 5))
    for check in egress_config.get("checks", []):
        if not check.get("enabled", True):
            continue
        report.egress_results.append(
            detect_egress(
                name=str(check.get("name", check.get("mode", "egress"))),
                endpoint=str(check.get("endpoint", endpoint)),
                mode=str(check.get("mode", "system")),
                proxy_url=check.get("proxy_url"),
                timeout=egress_timeout,
            )
        )

    if any(result.error for result in report.dns_results):
        report.warnings.append("One or more DNS queries failed; inspect the DNS table.")
    if any(result.error for result in report.egress_results):
        report.warnings.append("One or more egress checks failed; inspect the egress table.")
    return report
