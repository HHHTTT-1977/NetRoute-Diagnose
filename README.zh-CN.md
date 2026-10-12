# NetRoute-Diagnose

[English](README.en.md) · [简要首页](README.md)

面向 Clash、OpenClash、Mihomo 的只读规则诊断工具。根据本地 YAML 查找域名的候选
命中规则，分开显示策略目标与静态出站结论，对无法判断的情况明确标为不确定。
可用于检查直连期望与规则冲突、定位规则序号、生成独立 HTML/JSON 供排查。
它不观察 App 实时连接，不切换策略，不修改配置、DNS、系统代理或服务。

## 安装与第一个报告

需要 Python 3.10+。**v0.1.3** 的 GitHub Release 发布且 PyPI 上传完成后，
可安装正式发行包，无需克隆仓库：

```bash
python -m pip install netroute-diagnose==0.1.3
```

进入任意新目录，执行这个跨平台单行命令：

```bash
netroute-diagnose --demo --output demo.html
```

双击 `demo.html` 或使用浏览器“打开文件”。示例随 wheel 安装，**完全离线**，不需要
`examples/`。应得到 10 项检查：5 PASS、5 UNCERTAIN；后者来自运行态选择未知的命名
策略组，不是安装失败。`--demo` 不能与 `--config`、`--clash-config` 混用。

```bash
netroute-diagnose --demo --output demo.html --json-output demo.json
```

## 检查自己的 OpenClash 配置

建议在电脑运行，准备你自行取得的**实际生效 YAML**。OpenClash 的覆写可能使其与订阅
原文不同。工具不连接路由器，不索要管理密码，也不检查文件是否与运行态同步。

```bash
netroute-diagnose --clash-config your-clash.yaml --offline --output report.html
```

默认使用随包附带的微信、Apple、Google、OpenAI 域名期望，它们只是可修改的样例，
不是完整的 App 连通性检查，也不是通用的正确分流政策。

取消 `--offline` 将执行在线检测。DNS 和出口属于**运行工具的设备**，不自动代表
路由器或 App：默认发送域名到系统 DNS，并请求 `https://api.ipify.org?format=json`。

## 策略与状态

| 字段/状态 | 含义 |
|---|---|
| Policy target | 候选规则的原始策略目标名称 |
| Static outbound | 有静态证据时为 DIRECT/REJECT，否则 UNKNOWN；不是观察到的实际出站 |
| PASS | 静态证据符合期望 |
| MISMATCH | 静态证据与期望冲突 |
| UNCERTAIN | 前置规则、分支或策略目标需要未支持的信息/运行态 |
| UNKNOWN | 无确定结果，或期望为 UNKNOWN |

规则序号保持 YAML 列表顺序，从 1 开始。后续候选规则可能被前置未知条件截获。

- `rule` 模式按顺序分析支持的规则；主列表命中 `PASS`/`PASS-RULE` 后继续。
- `direct` 模式按配置给出 DIRECT，跳过规则；不证明当前运行模式仍然如此。
- `global` 模式目标为 GLOBAL，组选择未知，输出 UNCERTAIN。
- 内置 `DIRECT`、`COMPATIBLE` 按 DIRECT 解释；`REJECT`、`REJECT-DROP` 按 REJECT。
- 命名组和节点仅展示目标名称，最终出站未知。即使组中只写 DIRECT，也不假设运行态。
- SUB-RULE 整体降级为不确定，绝不展开成普通列表；子规则中的 PASS 有不同跳出语义。

退出码：**0** 没有确定性冲突（仍可能有不确定结果或网络警告）；**1** 参数、配置、
文件读取/输出错误；**2** 存在确定性 MISMATCH。请结合 JSON 状态和 warnings 判断完整结果。

## 自定义期望与在线检查

无需复制仓库文件，将以下内容保存为 `diagnosis.yaml`：

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

`expected` 可为 DIRECT、PROXY、REJECT、UNKNOWN；当前版本不会仅凭命名目标确认 PROXY。
域名须为字符串，超时须为正有限数，nameservers 须为 IP 字符串列表。

出口 `system` 遵循当前进程可见的代理设置；`direct` 禁用应用层 HTTP(S) 代理，但不能
绕过 TUN、透明代理或上游网关；`proxy` 使用显式 `proxy_url`，例如本机 HTTP 代理。
endpoint 和 proxy_url 只接受 HTTP(S)，重定向也验证协议。

系统 DNS 的 getaddrinfo 遵循操作系统超时，**dns.timeout 无法限制其总耗时**。
指定 DNS 时，该超时分别应用于顺序执行的 A、AAAA 查询；局部失败保留在 Error 栏，
同时保留成功取得的地址。DNS 成功不证明业务流量走了该路径；一个 IP 网站只反映该次请求。

## 限制与分享安全

支持 DOMAIN、DOMAIN-SUFFIX、DOMAIN-KEYWORD、MATCH、FINAL 的有限静态分析。
所有 DOMAIN-REGEX **均不执行、不编译、不改写表达式**：没有可靠的兼容性和时间界限时，
统一降级为不确定，包括 `\D`、非法正则和有回溯风险的正则。
DOMAIN-WILDCARD、DST-PORT、IP/进程条件、规则集、逻辑规则和子规则等均不模拟；
未知/异常前置规则不会被当作确定未命中。工具不下载远程规则集，也不读取控制器。

HTML、JSON 和 HTML 中的展开数据共用脱敏出口：移除 URL userinfo、敏感查询值、
非标准 URL 路径/fragment、已识别凭据和本地路径；网络异常不回显响应正文或底层消息。
保留域名、IP、策略名、规则序号等诊断证据。**分享前仍需检查这些数据和自定义名称**，
脱敏并非完整匿名化。无遥测、自动上传或托管后端。

## 开发

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m pip install build
python -m build
python scripts/check_wheel.py
```

最终 wheel 验收会在新虚拟环境和空目录执行 README Demo、检查 HTML/JSON，并运行测试。
[更新日志](CHANGELOG.md) · [安全政策](SECURITY.md) · [MIT](LICENSE)
