# NetRoute-Diagnose

[中文](README.zh-CN.md) · [Overview](README.md)

Read-only rule diagnostics for Clash, OpenClash and Mihomo. Compare domain routing
expectations against a local YAML configuration, locate candidate rules, and export
standalone HTML/JSON. Policy targets and static outbound conclusions are separate.
The tool does not observe app connections, switch groups, edit settings or restart services.

## Install and get your first report

Python 3.10+ is required. This branch prepares **0.1.3rc1, an unpublished candidate**.
PyPI 0.1.2 does not have `--demo`. To review the candidate, install its locally built
or CI-produced wheel; running it does not require a Git checkout:

```bash
python -m pip install /path/to/netroute_diagnose-0.1.3rc1-py3-none-any.whl
```

Replace the path with your downloaded wheel (also on Windows). After this feature
has been formally released on PyPI, installation will be:

```bash
python -m pip install --upgrade netroute-diagnose
```

From any new directory, run this cross-platform, single-line command:

```bash
netroute-diagnose --demo --output demo.html
```

Double-click `demo.html`, or use your browser's **Open File** command. All inputs
are bundled in the wheel; no `examples/` directory is needed. The demo is always
**offline**. Expect 10 checks: 5 PASS and 5 UNCERTAIN, because the named group's
runtime selection is unknown. Uncertainty is not an installation failure.
`--demo` cannot be combined with `--config` or `--clash-config`.

```bash
netroute-diagnose --demo --output demo.html --json-output demo.json
```

## Your own configuration

Run on your computer using a local copy of the **effective** Clash/OpenClash YAML.
OpenClash overrides may make it different from the original subscription. This
tool does not fetch router configuration or verify that the file matches runtime state.

```bash
netroute-diagnose --clash-config your-clash.yaml --offline --output report.html
```

The bundled WeChat, Apple, Google and OpenAI expectations are editable examples,
not comprehensive app health checks or universal routing recommendations.
Without `--offline`, DNS and configured egress checks run from **this device**.
The default profile uses system DNS and `https://api.ipify.org?format=json`.

## Report interpretation

| Field/status | Meaning |
|---|---|
| Policy target | Literal target of the candidate rule |
| Static outbound | DIRECT/REJECT when supported; UNKNOWN otherwise, never observed app traffic |
| PASS | Static evidence agrees with the expectation |
| MISMATCH | Static evidence conflicts with the expectation |
| UNCERTAIN | Earlier rules, branches or targets need unsupported/runtime information |
| UNKNOWN | No deterministic result, or expectation is UNKNOWN |

Rule numbers are 1-based original YAML list positions. Earlier uncertain rules may
intercept traffic before the displayed candidate.

- Configured `rule` mode checks supported rules in order. Main-list PASS/PASS-RULE continues.
- Configured `direct` mode bypasses rules and yields DIRECT; runtime mode is not observed.
- Configured `global` mode targets GLOBAL, whose selection is unknown (UNCERTAIN).
- Built-in DIRECT and COMPATIBLE classify as DIRECT; REJECT and REJECT-DROP as REJECT.
- Named groups/nodes retain their names but have unknown outbound, even a group listing only DIRECT.
- SUB-RULE stays uncertain and is never flattened: PASS has different branch-exit semantics inside it.

Exit codes: **0** no deterministic mismatch (uncertainty/network warnings may remain),
**1** argument/configuration/read/write error, **2** deterministic mismatch.
Inspect JSON statuses and warnings for the full result.

## Custom expectations and online checks

Save this as `diagnosis.yaml`; no repository example file is required:

```yaml
dns:
  nameservers: []
  timeout: 3
egress:
  endpoint: https://api.ipify.org?format=json
  timeout: 5
  checks:
    - name: system-route
      mode: system
      enabled: true
apps:
  - name: My App
    domains:
      - domain: example.com
        expected: DIRECT
```

```bash
netroute-diagnose --config diagnosis.yaml --clash-config your-clash.yaml --offline --output report.html
```

Expectations accept DIRECT, PROXY, REJECT or UNKNOWN. This version cannot confirm
PROXY from a named target alone. Domains must be strings, timeouts positive finite
numbers, and nameservers a list of IP address strings.

Egress `system` follows process-visible proxy settings; `direct` disables HTTP(S)
proxy settings but does not bypass TUN, transparent interception or upstream routing;
`proxy` uses an explicit HTTP(S) `proxy_url`. Endpoints and redirects must use HTTP(S).

System DNS uses OS resolver deadlines: **dns.timeout does not bound getaddrinfo**.
With an explicit resolver, the timeout applies separately to sequential A and AAAA
queries. Partial failures remain visible alongside successful addresses. DNS and
public-IP results are independent observations; neither proves an app's route.

## Limits and privacy

Limited static support covers DOMAIN, DOMAIN-SUFFIX, DOMAIN-KEYWORD, MATCH and FINAL.
All DOMAIN-REGEX rules are **not executed, compiled or rewritten**: without a bounded,
Mihomo-compatible evaluator they stay uncertain, including `\D`, invalid expressions
and backtracking hazards. DOMAIN-WILDCARD, DST-PORT, IP/process conditions, rule sets,
logical rules and subrules are not simulated. Unsupported/malformed earlier rules
cannot silently produce a high-confidence result. No controller or remote providers are queried.

There is no telemetry, upload or hosted backend. Online DNS sends domain names to
the selected resolver; egress requests expose normal metadata/source IP to the chosen
HTTP(S) endpoint. `--offline` and `--demo` skip both.

HTML, JSON and embedded diagnostic data use the same redaction boundary: URL
userinfo, query values (except safe format values), nonstandard URL paths/fragments,
recognized credentials and local paths are removed. Backend errors and response
bodies are not copied to reports. Domains, IPs, rule numbers and policy labels remain
useful evidence. **Review these before sharing**; arbitrary personal labels cannot
be automatically anonymized.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip install build
python -m build
python scripts/check_wheel.py
```

Final-wheel validation creates a fresh venv and empty directory, runs the README
Demo, checks HTML/JSON, and runs tests against the installed wheel.
[Changelog](CHANGELOG.md) · [Security](SECURITY.md) · [MIT](LICENSE)
