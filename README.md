# NetRoute-Diagnose

[中文文档](https://github.com/HHHTTT-1977/NetRoute-Diagnose/blob/main/README.zh-CN.md) · [English documentation](https://github.com/HHHTTT-1977/NetRoute-Diagnose/blob/main/README.en.md)

**Read-only, offline-first rule diagnosis for Clash, OpenClash and Mihomo.**
**只读分析域名的候选命中规则、策略目标及不确定性，生成独立 HTML 报告。**

Use it to compare domain routing expectations with a local YAML configuration.
It does not observe app connections, select proxy groups, modify settings, or restart services.
DNS and egress checks are optional, independent observations from the device running this tool.

适合排查“这个域名的规则目标是否符合预期”，无需开放控制器或提供路由器密码。
静态配置不能证明 App 的实时路径；命名策略组不会被直接当作最终 PROXY 出站。

## Quick Start / 快速开始

Python 3.10+ is required. For **v0.1.3**, install from PyPI after the GitHub
Release has published and its PyPI upload has completed:

```bash
python -m pip install netroute-diagnose==0.1.3
```

需要 Python 3.10+。**v0.1.3** 的 GitHub Release 发布且 PyPI 上传完成后，
可直接使用上述命令安装，无需克隆仓库。

From any new directory, run this **fully offline** example; all inputs are bundled:
在任意新目录执行下列命令；示例随包安装，不需要 `examples/`，不会发送网络请求：

```bash
netroute-diagnose --demo --output demo.html
```

Double-click `demo.html` or open it with your browser's **Open File** command.
双击 `demo.html` 或在浏览器中选择“打开文件”。预期为 **5 PASS、5 UNCERTAIN**：
示例中的命名代理组选择未知；不确定性是正确结果，不是安装失败。

For JSON as well / 同时导出 JSON：

```bash
netroute-diagnose --demo --output demo.html --json-output demo.json
```

## Your configuration / 使用自己的配置

Requires Python 3.10+. Run on your computer with a local copy of the **effective**
Clash/OpenClash YAML, including applied overrides. An original subscription may
not match the configuration the router actually uses. No router access is performed by this tool.

需要 Python 3.10+。将你自行取得的实际生效 YAML 放在电脑上；注意 OpenClash 覆写后的
配置可能不同于订阅原文。工具不负责连接路由器或取得配置。

```bash
netroute-diagnose --clash-config your-clash.yaml --offline --output report.html
```

Omitting `--offline` enables DNS and configured egress checks from **this device**.
默认 profile 使用系统 DNS 和 `https://api.ipify.org?format=json`；取消 `--offline`
会从运行工具的设备发出请求，不代表路由器或所有 App 的出口。

## Reading the report / 解读报告

- **Policy target**: literal target of the candidate rule / 候选规则的策略目标。
- **Static outbound**: DIRECT/REJECT only when supported by static evidence;
  named targets remain UNKNOWN / 命名目标的最终出站未知。
- **PASS / MISMATCH**: static evidence agrees/disagrees with the expectation;
  neither proves runtime traffic / 仅对比静态证据与预期。
- **UNCERTAIN**: earlier rules or a target require unsupported/runtime information.
- **UNKNOWN**: no deterministic result, or no configured expectation.

`DOMAIN`, `DOMAIN-SUFFIX`, `DOMAIN-KEYWORD`, `MATCH` and `FINAL` have limited static
support. All regex rules are **not executed**, preventing regex backtracking hangs.
Other unsupported/malformed rules, rule providers, port/IP/process conditions and
SUB-RULE branches conservatively reduce confidence. Main-list PASS continues;
SUB-RULE is never flattened or simulated. Configured direct/global/rule modes are
respected, but runtime mode changes and group selections are not observed.

正则、通配符、端口、规则集及子规则等未支持条件明确降级，不会跳过后报高置信度 PASS。
内置 `COMPATIBLE` 按 DIRECT 解释。命名组即使只列有 DIRECT，也不推断运行态。

Exit codes / 退出码：**0** no deterministic mismatch (may include uncertainty or
network warnings), **1** argument/configuration/output error, **2** deterministic mismatch.

## Privacy / 隐私

No telemetry or uploads. Configuration and reports stay local. Online DNS queries
send domain names to the selected resolver; HTTP(S) egress requests reveal normal
request metadata and source IP to the chosen endpoint. `--offline` and `--demo`
skip both. HTTP `direct` only disables application proxy settings, not TUN or transparent routing.

HTML and JSON share a redaction boundary: URL credentials, query values (except
safe `format` values), nonstandard URL paths/fragments, recognized secrets and local
paths are removed. Backend response/error bodies are not copied into reports.
Domains, IPs and policy labels remain visible because they are diagnostic evidence;
**review these before sharing**. Arbitrary personal labels cannot be automatically anonymized.

无遥测、无上传。HTML/JSON 使用同一脱敏出口；脱敏不等于匿名化，分享前仍需检查域名、
IP 和自定义名称。在线检查仅接受 HTTP(S) endpoint，重定向也检查协议。

## Development / 开发

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip install build
python -m build
python scripts/check_wheel.py
```

[Changelog](https://github.com/HHHTTT-1977/NetRoute-Diagnose/blob/main/CHANGELOG.md) · [MIT License](https://github.com/HHHTTT-1977/NetRoute-Diagnose/blob/main/LICENSE)
