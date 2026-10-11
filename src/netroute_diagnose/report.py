from __future__ import annotations

import html
import json
from pathlib import Path
from types import SimpleNamespace

from .models import DiagnosticReport


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _badge(status: str) -> str:
    return f'<span class="badge {status.lower()}">{_e(status)}</span>'


def render_html(report: DiagnosticReport) -> str:
    data = report.to_dict()
    def view(value):
        if isinstance(value, dict):
            return SimpleNamespace(**{k: view(v) for k, v in value.items()})
        if isinstance(value, list):
            return [view(v) for v in value]
        return value
    report = view(data)
    counts = {
        status: sum(check.status == status for check in report.domain_checks)
        for status in ("PASS", "MISMATCH", "UNCERTAIN", "UNKNOWN")
    }
    route_rows = []
    for check in report.domain_checks:
        match = check.rule_match
        notes = "<br>".join(_e(note) for note in match.notes) or "—"
        rule_number = match.rule_index + 1 if match.rule_index is not None else "—"
        route_rows.append(
            "<tr>"
            f"<td>{_e(check.app)}</td><td><code>{_e(check.domain)}</code></td>"
            f"<td>{_e(check.expected)}</td><td>{_e(match.policy or '—')}</td><td>{_e(check.actual)}</td>"
            f"<td>{_badge(check.status)}</td><td>{_e(match.confidence)}</td>"
            f"<td>#{_e(rule_number)} <code>{_e(match.rule or 'No deterministic match')}</code></td>"
            f"<td>{notes}</td></tr>"
        )

    dns_rows = [
        "<tr>"
        f"<td><code>{_e(item.domain)}</code></td><td>{_e(item.resolver)}</td>"
        f"<td>{_e(', '.join(item.addresses) or '—')}</td>"
        f"<td>{item.elapsed_ms:.1f}</td><td>{_e(item.error or '—')}</td></tr>"
        for item in report.dns_results
    ]
    egress_rows = [
        "<tr>"
        f"<td>{_e(item.name)}</td><td>{_e(item.mode)}</td>"
        f"<td><code>{_e(item.ip or '—')}</code></td><td>{_e(item.endpoint)}</td>"
        f"<td>{item.elapsed_ms:.1f}</td><td>{_e(item.error or '—')}</td></tr>"
        for item in report.egress_results
    ]
    warning_items = "".join(f"<li>{_e(item)}</li>" for item in report.warnings)
    raw_json = html.escape(json.dumps(data, ensure_ascii=False, indent=2))

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NetRoute-Diagnose Report</title>
  <style>
    :root {{ color-scheme: light dark; --bg:#f4f7fb; --card:#fff; --text:#172033;
      --muted:#64748b; --line:#dbe3ef; --accent:#2563eb; }}
    @media (prefers-color-scheme:dark) {{ :root {{ --bg:#0f172a; --card:#172033;
      --text:#e5edf8; --muted:#9aabc2; --line:#334155; --accent:#60a5fa; }} }}
    * {{ box-sizing:border-box }} body {{ margin:0; background:var(--bg); color:var(--text);
      font:14px/1.55 system-ui,-apple-system,sans-serif }} main {{ max-width:1500px;
      margin:auto; padding:32px }} h1 {{ margin:0 }} h2 {{ margin-top:0 }}
    .sub {{ color:var(--muted); margin:6px 0 24px }} .grid {{ display:grid;
      grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
      padding:18px; margin-bottom:18px; box-shadow:0 4px 16px #0000000a }}
    .metric strong {{ display:block; font-size:28px }} .metric span {{ color:var(--muted) }}
    .table-wrap {{ overflow:auto }} table {{ border-collapse:collapse; width:100%;
      min-width:850px }} th,td {{ border-bottom:1px solid var(--line); padding:10px;
      text-align:left; vertical-align:top }} th {{ color:var(--muted) }}
    code {{ overflow-wrap:anywhere }} .badge {{ border-radius:999px; padding:3px 8px;
      font-size:12px; font-weight:700 }} .pass {{ background:#16a34a22; color:#16a34a }}
    .mismatch {{ background:#dc262622; color:#dc2626 }} .uncertain {{ background:#d9770622;
      color:#d97706 }} .unknown {{ background:#64748b22; color:#64748b }}
    details pre {{ max-height:500px; overflow:auto; white-space:pre-wrap }}
  </style>
</head>
<body><main>
  <h1>NetRoute-Diagnose</h1>
  <p class="sub">Generated {_e(report.generated_at)} · Static rule analysis is not proof of runtime routing.</p>
  <p>配置模式 / Configured mode: {_e(getattr(report.metadata, "mode", "unknown"))}. Runtime mode and group selection are not observed.
  UNKNOWN outbound means the target is known but its final route is not. PASS compares static evidence only.
  / 未观测运行态；命名目标不代表最终出站，PASS 仅表示静态证据符合预期。</p>
  <section class="grid">
    <div class="card metric"><strong>{counts['PASS']}</strong><span>PASS</span></div>
    <div class="card metric"><strong>{counts['MISMATCH']}</strong><span>MISMATCH</span></div>
    <div class="card metric"><strong>{counts['UNCERTAIN']}</strong><span>UNCERTAIN</span></div>
    <div class="card metric"><strong>{counts['UNKNOWN']}</strong><span>UNKNOWN</span></div>
  </section>
  <section class="card"><h2>Rule path checks / 规则路径检查</h2><div class="table-wrap">
    <table><thead><tr><th>App</th><th>Domain</th><th>Expected</th><th>Policy target</th><th>Static outbound</th>
    <th>Status</th><th>Confidence</th><th>Candidate rule</th><th>Notes</th></tr></thead>
    <tbody>{''.join(route_rows)}</tbody></table></div></section>
  <section class="card"><h2>DNS checks / DNS 检测</h2><div class="table-wrap">
    <table><thead><tr><th>Domain</th><th>Resolver</th><th>Addresses</th>
    <th>ms</th><th>Error</th></tr></thead><tbody>{''.join(dns_rows) or '<tr><td colspan="5">Skipped</td></tr>'}</tbody>
    </table></div></section>
  <section class="card"><h2>Egress checks / 出口检测</h2><div class="table-wrap">
    <table><thead><tr><th>Name</th><th>Mode</th><th>IP</th><th>Endpoint</th>
    <th>ms</th><th>Error</th></tr></thead><tbody>{''.join(egress_rows) or '<tr><td colspan="6">Skipped</td></tr>'}</tbody>
    </table></div></section>
  <section class="card"><h2>Warnings / 警告</h2><ul>{warning_items or '<li>None</li>'}</ul></section>
  <section class="card"><details><summary>Sanitized diagnostic data / 脱敏诊断数据</summary>
    <pre>{raw_json}</pre></details></section>
</main></body></html>"""


def write_html(report: DiagnosticReport, output: str | Path) -> Path:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_html(report), encoding="utf-8")
    return output_path.resolve()
