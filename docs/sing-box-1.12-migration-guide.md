# sing-box 1.12+ 配置迁移指南

本文档总结了从 sing-box 1.11 迁移到 1.12+ 时的常见问题和解决方案。

## 主要变更

### 1. DNS 配置重构

#### 1.1 DNS 服务器格式变更

**旧格式（1.11及之前）：**
```json
{
  "tag": "proxyDns",
  "address": "tls://8.8.8.8",
  "detour": "Proxy"
}
```

**新格式（1.12+）：**
```json
{
  "tag": "google",
  "type": "tls",
  "server": "8.8.8.8",
  "detour": "Proxy"
}
```

**常见错误：**
- ❌ 继续使用 `address` 字段
- ❌ `type` 设置为 `udp` 而不是实际的协议类型

#### 1.2 fakeip 配置变更

**错误配置：**
```json
{
  "dns": {
    "fakeip": {              // ❌ 已废弃
      "enabled": true,
      "inet4_range": "198.18.0.0/15"
    },
    "servers": [
      {
        "tag": "fakeip",
        "type": "udp",       // ❌ 错误
        "server": "fakeip"   // ❌ 错误
      }
    ]
  }
}
```

**正确配置：**
```json
{
  "dns": {
    "servers": [
      {
        "tag": "fakeip",
        "type": "fakeip",
        "inet4_range": "198.18.0.0/15",
        "inet6_range": "fc00::/18"
      }
    ]
  }
}
```

#### 1.3 domain_resolver 和循环依赖

**问题场景：** DNS 服务器使用域名，但没有配置 `domain_resolver`。

**错误配置（循环依赖）：**
```json
{
  "tag": "local",
  "type": "https",
  "server": "223.5.5.5",      // 注意：这是 IP 地址
  "domain_resolver": "local"   // ❌ 错误：IP 地址不需要 domain_resolver
}
```

错误：`circular server dependency google -> local -> local`

**正确配置：**
```json
{
  "tag": "google",
  "type": "tls",
  "server": "8.8.8.8"        // ✅ IP 地址不需要 domain_resolver
}
```

**何时需要 `domain_resolver`：**

当 DNS 服务器使用**域名**而不是 IP 地址时：

```json
{
  "tag": "google-dot",
  "type": "tls",
  "server": "dns.google",        // 域名，需要 domain_resolver
  "domain_resolver": "local"       // 使用 local DNS 解析域名
}
```

#### 1.4 detour 配置问题

**错误：**
```json
{
  "tag": "local",
  "type": "https",
  "server": "223.5.5.5",
  "detour": "direct"   // ❌ 错误：detour 到 direct 没有意义
}
```

错误：`detour to an empty direct outbound make no sense`

**正确：**
```json
{
  "tag": "local",
  "type": "https",
  "server": "223.5.5.5"
  // 不需要 detour，DNS 查询直接通过本地网络
}
```

### 2. 废弃的配置项

#### 2.1 dns.strategy

**废弃：**
```json
{
  "dns": {
    "strategy": "prefer_ipv4"   // ❌ 已废弃
  }
}
```

**替代：**
```json
{
  "route": {
    "default_domain_resolver": {
      "server": "local",
      "strategy": "prefer_ipv4"
    }
  }
}
```

#### 2.2 dns.outbound 规则

**废弃：**
```json
{
  "dns": {
    "rules": [
      {
        "outbound": "any",   // ❌ 已废弃
        "server": "local"
      }
    ]
  }
}
```

## 完整修复示例

假设你有以下错误的 1.11 配置：

```json
{
  "dns": {
    "fakeip": {
      "enabled": true,
      "inet4_range": "198.18.0.0/15"
    },
    "servers": [
      {
        "tag": "proxyDns",
        "address": "tls://8.8.8.8",
        "detour": "Proxy"
      },
      {
        "tag": "localDns",
        "address": "https://223.5.5.5/dns-query",
        "detour": "direct"
      },
      {
        "tag": "fakeip",
        "type": "udp",
        "server": "fakeip"
      }
    ],
    "rules": [
      {
        "outbound": "any",
        "server": "localDns"
      }
    ],
    "strategy": "prefer_ipv4"
  }
}
```

修复后的 1.12 配置：

```json
{
  "dns": {
    "servers": [
      {
        "tag": "google",
        "type": "tls",
        "server": "8.8.8.8",
        "detour": "Proxy"
      },
      {
        "tag": "local",
        "type": "https",
        "server": "223.5.5.5"
      },
      {
        "tag": "fakeip",
        "type": "fakeip",
        "inet4_range": "198.18.0.0/15",
        "inet6_range": "fc00::/18"
      }
    ],
    "rules": [
      {
        "clash_mode": "direct",
        "server": "local"
      }
    ]
  },
  "route": {
    "default_domain_resolver": {
      "server": "local",
      "strategy": "prefer_ipv4"
    }
  }
}
```

## 总结

| 问题 | 错误信息 | 解决方案 |
|------|---------|---------|
| DNS 服务器格式错误 | - | `address` → `type` + `server` |
| fakeip 配置错误 | - | `type: fakeip` 而不是 `type: udp` |
| 循环依赖 | `circular server dependency` | IP 地址不需要 `domain_resolver` |
| detour 错误 | `detour to an empty direct outbound` | 移除不必要的 `detour` |
| 废弃配置 | - | 移除 `dns.strategy`, `dns.fakeip`, `dns.outbound` |

如有其他问题，请提供完整的错误信息以便进一步诊断。
