from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import ConfigError, bundled_config_path
from .diagnose import run_diagnostics
from .privacy import sanitize_text
from .report import write_html


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse may echo user input, including credentials.
        self.print_usage(sys.stderr)
        self.exit(1, 'Error: invalid arguments; use --help for supported options\n')


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(prog='netroute-diagnose', description='Read-only static route diagnostics for Clash/Mihomo')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--demo', action='store_true', help='Run bundled synthetic demo, always offline')
    parser.add_argument('--config', help='Diagnostic YAML (default: bundled app expectations)')
    parser.add_argument('--clash-config', help='Clash/OpenClash YAML; required unless --demo')
    parser.add_argument('--output', default='netroute-report.html', help='HTML output path')
    parser.add_argument('--json-output', help='Optional sanitized JSON output path')
    parser.add_argument('--offline', action='store_true', help='Skip DNS and egress requests')
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.demo and (args.config or args.clash_config):
        parser.error('--demo cannot be combined with input configuration paths')
    if not args.demo and not args.clash_config:
        parser.error('--clash-config is required')
    config = args.config or bundled_config_path()
    clash = bundled_config_path('demo-clash.yaml') if args.demo else args.clash_config
    try:
        inputs = {Path(config).resolve(), Path(clash).resolve()}
        outputs = [Path(args.output).resolve()]
        if args.json_output:
            outputs.append(Path(args.json_output).resolve())
        if any(p in inputs for p in outputs) or len(set(outputs)) != len(outputs):
            raise ConfigError('Output paths must differ from inputs and from one another')
        report = run_diagnostics(config, clash, offline=args.offline or args.demo)
        output = write_html(report, args.output)
        if args.json_output:
            json_path = Path(args.json_output)
            json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')
        mismatches = sum(item.status == 'MISMATCH' for item in report.domain_checks)
        uncertain = sum(item.status in {'UNCERTAIN', 'UNKNOWN'} for item in report.domain_checks)
        print(f'Report written: {sanitize_text(output.name, report.sensitive_values)} (open the HTML file in your browser)')
        print(f'Checks: {len(report.domain_checks)}, mismatches: {mismatches}, uncertain/unknown: {uncertain}')
        return 2 if mismatches else 0
    except ConfigError as exc:
        print(f'Error: {sanitize_text(str(exc))}', file=sys.stderr)
        return 1
    except (OSError, ValueError, RecursionError) as exc:
        print(f'Error: operation failed ({type(exc).__name__}); check configuration and output permissions', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
