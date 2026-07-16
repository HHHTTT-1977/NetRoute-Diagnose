# NetRoute-Diagnose

[中文](README.zh-CN.md) · [Short overview](README.md)

NetRoute-Diagnose is a read-only Python network path diagnostic tool for Clash
and OpenClash users. It combines DNS results, observed egress IPs, first-match
Clash rule analysis, and per-app routing expectations in one standalone HTML
report.

## Who it is for

- Clash, Mihomo, and OpenClash users who do not want to inspect long rule lists
- Users troubleshooting cases such as "WeChat works, but Google does not" or
  an Apple service taking the wrong route
- Anyone who wants a read-only summary of DNS, egress, and rule matches

You only need a Clash/OpenClash YAML file. The tool does not ask for router
credentials or change network state. Start with the offline demo below.

## View the demo first

The repository includes a [sanitized HTML demo report](docs/demo-report.html)
generated entirely from synthetic configuration. It contains no real proxies,
home-network addresses, usernames, or personal paths.

![NetRoute-Diagnose demo report preview](docs/demo-preview.svg)

Generate it locally:

```bash
python -m pip install -e .
netroute-diagnose \
  --config examples/diagnosis.yaml \
  --clash-config examples/clash-config.yaml \
  --offline \
  --output reports/demo.html
```

## Features

- Query A and AAAA records through the system resolver or explicit DNS servers
- Observe public egress IPs through the system path, a proxy-free direct path,
  or an explicit HTTP proxy
- Parse `rules` from Clash/OpenClash YAML configurations
- Deterministically analyze `DOMAIN`, `DOMAIN-SUFFIX`, `DOMAIN-KEYWORD`,
  `DOMAIN-REGEX`, `MATCH`, and `FINAL`
- Flag uncertainty introduced by `RULE-SET`, `GEOSITE`, `GEOIP`, IP, process,
  and logical rules
- Compare each app domain with its expected route and report `PASS`,
  `MISMATCH`, `UNCERTAIN`, or `UNKNOWN`
- Include built-in WeChat, Apple, Google, and OpenAI diagnostic profiles
- Generate a standalone HTML report and optional JSON output

## Safety boundary

Phase one performs reads and network queries only:

- It does not edit Clash/OpenClash YAML.
- It does not change subscriptions, proxies, rules, DNS, or system proxy state.
- It does not call controller APIs to switch policies.
- It does not restart Clash/OpenClash or system services.
- It does not write to a router.

The rule path is a static inference from YAML. Egress IPs are observations from
separate HTTP requests. They are different evidence, and the tool does not use
DNS results or proxy names alone as proof of the actual runtime route.

## Requirements

- Python 3.10 or newer
- A readable Clash/OpenClash YAML configuration
- Network access for online checks

## Installation

Download the repository, open its directory, and run:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Quick start

Analyze the included example without making DNS or egress requests:

```bash
netroute-diagnose \
  --config examples/diagnosis.yaml \
  --clash-config examples/clash-config.yaml \
  --offline \
  --output reports/demo.html
```

Use the built-in app profile and run online checks:

```bash
netroute-diagnose \
  --clash-config your-clash.yaml \
  --output reports/network-report.html
```

Add machine-readable output:

```bash
netroute-diagnose \
  --clash-config your-clash.yaml \
  --output reports/network-report.html \
  --json-output reports/network-report.json
```

The command exits with status `2` when deterministic mismatches exist, `1` for
configuration or runtime errors, and `0` otherwise.

### Three useful terms

- `DIRECT`: the request is not sent to a proxy policy group.
- `PROXY`: the request is sent to a named policy group; that group may still
  select `DIRECT` at runtime.
- Static analysis: the tool follows YAML rule order but does not observe the
  app's live connection.

## Custom profile

Copy `examples/diagnosis.yaml` and adapt domains and expectations:

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
    - name: clash-http-proxy
      mode: proxy
      proxy_url: http://127.0.0.1:7890
      enabled: true

apps:
  - name: My App
    domains:
      - domain: example.com
        expected: DIRECT
      - domain: api.example.net
        expected: PROXY
```

Allowed `expected` values are `DIRECT`, `PROXY`, `REJECT`, and `UNKNOWN`. A
named policy group such as `Proxy`, `Auto Select`, or `Apple` is statically
classified as `PROXY`. The analyzer cannot know whether that group currently
selects `DIRECT`, so combine the report with egress observations and runtime
Clash/OpenClash logs.

Egress modes:

- `system` honors proxy settings visible to the Python process.
- `direct` disables HTTP(S) proxy handling for the request.
- `proxy` uses the HTTP proxy specified by `proxy_url`.

## Reading the report

- `PASS`: the deterministic first match agrees with the expectation.
- `MISMATCH`: the deterministic first match conflicts with the expectation.
- `UNCERTAIN`: a later match was found, but an earlier rule needs provider,
  IP, process, or other runtime context.
- `UNKNOWN`: no deterministic match exists, or the expectation is unknown.

The report includes the one-based rule number, complete rule text, policy
target, and confidence.

## Known limitations

- Remote `rule-providers` are not downloaded or expanded.
- DNS-to-`IP-CIDR`/`GEOIP` matching is not simulated.
- Live controller connections, policy selections, and script results are not
  inspected.
- A named proxy group can select `DIRECT` at runtime.
- A successful DNS query does not prove application traffic uses that path.
- An egress service only proves the route of that individual request.

These cases produce limited confidence or uncertainty instead of being
presented as confirmed runtime routing.

## Privacy

- HTML and JSON reports record configuration filenames, not absolute paths.
- `127.0.0.1` in examples is the standard loopback address.
- Tests use the documentation-only ranges `192.0.2.0/24`, `203.0.113.0/24`,
  and `2001:db8::/32`.
- Before publishing an issue, still review domains, rule names, and observed
  egress IPs in your own report.

## Development

```bash
python -m unittest discover -s tests -v
```

The project uses a `src` layout. Configuration, DNS, egress observation, rule
analysis, orchestration, and HTML rendering are separated into focused modules.
Issues and pull requests are welcome.

## License

[MIT License](LICENSE)
