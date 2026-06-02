# 与 sing-box-yg 脚本配合使用 Hysteria2 的兼容性说明

记录两个使用 [yonggekkk/sing-box-yg](https://github.com/yonggekkk/sing-box-yg) 一键脚本搭建 hy2 服务端、再用本工具生成 sing-box 客户端配置时容易踩到的坑。

## 1. 端口跳跃参数 `mport`（已修复）

### 现象

yg / v2rayN 生成的 hy2 订阅 URI 用非标准参数 `mport=1000-2000` 表达端口跳跃范围：

```
hysteria2://...@server:27222?...&mport=1000-2000&...
```

而 sing-box 官方协议规范的端口范围写法是 `IP:port,start-end`：

```
hysteria2://...@server:27222,1000-2000?...
```

`parsers/hysteria2.py` 早期只识别后者，会导致：

- 服务端 iptables 把 `1000-2000` REDIRECT 到 hy2 监听端口（yg 默认行为）
- 但生成的 sing-box 客户端 config 只有 `server_port: 27222`，没有 `server_ports`
- 客户端只往单端口发包，端口跳跃完全没生效
- 现象：hy2 长时间运行后被 GFW 按 IP-port 节流，过夜挂

### 修复

`parsers/hysteria2.py` 在标准格式不匹配时，回退识别 `mport` query 参数，转成标准 `server_ports`：

```python
if ports_match:
    node['server_ports'] = [ports_match.group(1).replace('-', ':')]
elif re.match(r'^\d+-\d+$', netquery.get('mport', '')):
    node['server_ports'] = [netquery['mport'].replace('-', ':')]
```

## 2. yg 自签 bing.com 证书不符合 X.509 标准

### 现象

sing-box DEBUG 日志：

```
clash-api: outbound hy2-xxx unavailable: CRYPTO_ERROR 0x12a (local):
tls: failed to verify certificate: x509: "www.bing.com" certificate is not standards compliant
```

metacubexd 面板上 hy2 节点测试 Timeout，sing-box 内部 urltest 也跳过 hy2 节点。

### 原因

yg 脚本默认生成的自签 bing.com 证书**缺少 SAN（Subject Alternative Name）字段**。Go 1.15+ 的 `crypto/tls` 要求服务器证书必须有 SAN，CN 字段已不被信任。sing-box 在 `insecure=false` 时使用严格校验，直接拒绝。

### 解决方案

**短期（治标）**：订阅 URI 加 `insecure=1&allowInsecure=1`，让客户端跳过证书校验。本工具 parser 已支持识别这两个参数：

```
hysteria2://...@server:port?...&insecure=1&allowInsecure=1&...
```

**长期（治本）**：

- 服务端 openssl 重新生成带 SAN 字段的自签证书，或
- 用真实域名 + Let's Encrypt 真实证书（顺便摆脱自签 bing.com 被 CT log 标记的风险）

### 排查这类问题的关键

服务端日志看不到 TLS 握手失败（拒绝发生在客户端）。客户端 sing-box 默认 INFO 级别只记录 "outbound connection to xxx"，不记 TLS 校验失败。**必须开 DEBUG 级别**才能看到 `CRYPTO_ERROR` 详细原因：

```json
{
  "log": { "level": "debug", "output": "/tmp/sing-box.log" }
}
```
