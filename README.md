# NetRoute-Diagnose

[中文文档](README.zh-CN.md) · [English documentation](README.en.md)

**Find out why an app domain goes DIRECT or through a proxy—without changing
your network.**

**查清 App 域名为什么直连或走代理，全程不修改你的网络。**

NetRoute-Diagnose is a read-only network path diagnostic tool for Clash and
OpenClash users. NetRoute-Diagnose 是面向 Clash/OpenClash 用户的只读网络路径诊断
工具，内置微信、Apple、Google 和 OpenAI 示例。

![NetRoute-Diagnose demo report preview](docs/demo-preview.svg)

## 30-second demo / 30 秒演示

```bash
python -m pip install -e .
netroute-diagnose \
  --clash-config examples/clash-config.yaml \
  --offline \
  --output reports/demo.html
```

Open `reports/demo.html` in any browser, or view the repository's
[sanitized demo report](docs/demo-report.html).

随后用浏览器打开 `reports/demo.html`，也可以直接查看仓库中的
[脱敏 Demo 报告](docs/demo-report.html)。

The tool does not edit Clash/OpenClash configuration, restart services, change
DNS settings, or modify system proxy settings.

本工具不会修改 Clash/OpenClash 配置、重启服务、更改 DNS 或修改系统代理设置。

Documentation: [中文](README.zh-CN.md) · [English](README.en.md) ·
[Changelog](CHANGELOG.md) · License: [MIT](LICENSE)
