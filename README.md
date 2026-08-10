# NetRoute-Diagnose

[中文文档](README.zh-CN.md) · [English documentation](README.en.md)

**Find out why an app domain goes DIRECT or through a proxy—without changing
your network.**

**查清 App 域名为什么直连或走代理，全程不修改你的网络。**

NetRoute-Diagnose is a read-only network path diagnostic tool for Clash and
OpenClash users. NetRoute-Diagnose 是面向 Clash/OpenClash 用户的只读网络路径诊断
工具，内置微信、Apple、Google 和 OpenAI 示例。

![NetRoute-Diagnose demo report preview](docs/demo-preview.svg)

![NetRoute-Diagnose sanitized CLI demo](docs/cli-demo.svg)

## Typical scenarios / 三个典型场景

1. **WeChat unexpectedly uses a proxy / 微信意外走代理** — compare the expected
   `DIRECT` route with the first matching Clash/OpenClash rule.
2. **Apple, Google, or OpenAI takes the wrong route / Apple、Google 或 OpenAI
   路径异常** — use the built-in profiles to see which rule is responsible and
   whether static analysis is certain.
3. **Compare egress observations / 比较出口观测** — compare system, direct, or an
   explicit HTTP-proxy request to help distinguish a route assumption from an
   observed public egress result.

## Quick Start / 快速开始

For ordinary users, install the released source package—no Git knowledge or
development setup is required. 普通用户可以直接安装发布源码包，无需了解 Git 或开发环境：

```bash
python -m pip install "https://github.com/HHHTTT-1977/NetRoute-Diagnose/archive/refs/tags/v0.1.1.zip"
```

Then run the built-in, fully offline example. 下面的示例完全离线，不会执行 DNS 或出口 IP
请求：

## 30-second demo / 30 秒演示

```bash
netroute-diagnose \
  --config examples/diagnosis.yaml \
  --clash-config examples/clash-config.yaml \
  --offline \
  --output reports/demo.html
```

Open `reports/demo.html` in any browser, or view the repository's
[sanitized demo report](docs/demo-report.html).

随后用浏览器打开 `reports/demo.html`，也可以直接查看仓库中的
[脱敏 Demo 报告](docs/demo-report.html)。

PyPI has not been published for this release. Do not use `pip install
netroute-diagnose` until a PyPI release is announced. 本版本尚未发布到 PyPI；在项目
公告前请勿使用 `pip install netroute-diagnose`。

For source development, clone the repository and use `python -m pip install -e .`.
开发安装请克隆仓库后使用 `python -m pip install -e .`。

The tool does not edit Clash/OpenClash configuration, restart services, change
DNS settings, or modify system proxy settings.

本工具不会修改 Clash/OpenClash 配置、重启服务、更改 DNS 或修改系统代理设置。

## Privacy and data flow / 隐私与数据流

Clash/OpenClash rule parsing and report generation run locally. Configuration
files and report contents are not uploaded, and NetRoute-Diagnose does not
collect users' network configurations or provide a telemetry service.

Clash/OpenClash 规则解析和报告生成在本地执行。配置文件及报告内容不会上传，
NetRoute-Diagnose 不收集用户网络配置，也不提供遥测服务。

Online checks are optional and are skipped with `--offline`:

- DNS checks send configured domain names to the system or explicitly
  configured DNS resolver.
- Egress IP checks make an HTTP(S) request to the configured public-IP service;
  the default endpoint is `api.ipify.org`, which necessarily sees the request's
  source IP and normal connection metadata.
- These requests are used only to produce the diagnostic result. The tool does
  not transmit configuration files or report contents. Results are written only
  to the local output files selected by the user.

在线检查是可选的，使用 `--offline` 时会跳过：

- DNS 检测会把配置中的域名发送给系统 DNS 或用户明确指定的 DNS 解析器。
- 出口 IP 检测会向配置的公网 IP 服务发起 HTTP(S) 请求；默认端点为
  `api.ipify.org`，该服务必然能够看到请求源 IP 和常规连接元数据。
- 这些请求仅用于生成诊断结果。工具不会传输配置文件或报告内容，结果只写入用户
  指定的本地输出文件。

| Operation / 操作 | Leaves the device / 离开本机的数据 | Destination / 目标 |
|---|---|---|
| Rule parsing / 规则解析 | None / 无 | Local only / 仅本地 |
| DNS check / DNS 检测 | Domain name / 域名 | Configured DNS resolver / 配置的 DNS 解析器 |
| Egress check / 出口检测 | Public-IP request metadata / 公网 IP 请求元数据 | Configured IP service / 配置的 IP 服务 |
| HTML/JSON report / 报告 | None / 无 | User-selected local file / 用户指定的本地文件 |

Documentation: [中文](README.zh-CN.md) · [English](README.en.md) ·
[Changelog](CHANGELOG.md) · License: [MIT](LICENSE)
