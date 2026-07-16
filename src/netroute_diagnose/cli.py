from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, bundled_config_path
from .diagnose import run_diagnostics
from .report import write_html


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netroute-diagnose",
        description="Read-only network path diagnostics for Clash/OpenClash",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--config",
        default=str(bundled_config_path()),
        help="Diagnostic profile YAML (default: bundled WeChat/Apple/Google/OpenAI profile)",
    )
    parser.add_argument("--clash-config", required=True, help="Clash/OpenClash YAML")
    parser.add_argument("--output", default="netroute-report.html", help="HTML output path")
    parser.add_argument("--json-output", help="Optional JSON output path")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Skip DNS and egress requests; analyze YAML rules only",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_diagnostics(
            diagnostic_config=args.config,
            clash_config=args.clash_config,
            offline=args.offline,
        )
        output = write_html(report, args.output)
        if args.json_output:
            json_path = Path(args.json_output)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        mismatches = sum(item.status == "MISMATCH" for item in report.domain_checks)
        print(f"Report written: {output}")
        print(f"Checks: {len(report.domain_checks)}, mismatches: {mismatches}")
        return 2 if mismatches else 0
    except (ConfigError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
