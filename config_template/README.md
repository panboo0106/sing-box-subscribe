# sing-box 配置模板

本目录包含兼容 sing-box v1.12+ 的配置模板，按使用场景分类整理。

## 目录结构

```
config_template/
├── 01-tun-ai/           # TUN 模式 + AI 专用路由（推荐）
│   ├── ai-universal.json          # Android 专用（内置 Tailscale endpoint）
│   └── ai-universal-no-ts.json   # macOS 专用（配合官方 Tailscale 客户端）
├── 02-notun-ai/         # NoTUN 模式 + AI 专用路由
│   ├── ai-universal.json          # 含 Tailscale endpoint
│   ├── ai-universal-no-ts.json   # 无 Tailscale
│   └── ai-global.json            # 多地区分组版（含 Tailscale endpoint）
├── 03-full-streaming/   # 完整流媒体分流
│   └── streaming-full.json
├── 04-minimal/          # 极简配置
│   └── minimal.json
└── README.md
```

---

## 平台推荐

| 平台 | 推荐模板 | Tailscale 方案 |
|------|---------|---------------|
| **Android** | `01-tun-ai/ai-universal.json` | sing-box 内置 endpoint，统一管理 |
| **macOS** | `01-tun-ai/ai-universal-no-ts.json` | 官方 Tailscale 客户端 + sing-box 共存 |
| **iPhone (iOS)** | `01-tun-ai/ai-universal-no-ts.json` | iOS 只能同时跑一个 VPN，用快捷指令切换 |
| **仅浏览器代理** | `02-notun-ai/ai-universal.json` | 含 Tailscale endpoint，无 TUN |
| **多地区节点** | `02-notun-ai/ai-global.json` | 含 Tailscale endpoint，按地区分组 |
| **流媒体解锁** | `03-full-streaming/streaming-full.json` | 无 Tailscale |
| **测试/低端设备** | `04-minimal/minimal.json` | 无 Tailscale |

### iOS 特别说明

iOS 系统限制：同时只允许一个活跃 VPN（NetworkExtension）。sing-box (SFI) 和官方 Tailscale App 无法共存，建议：
- 用 **iOS 快捷指令** 一键切换两个 App
- 或在 VPS 上部署 Tailscale Exit Node，iPhone 只跑 Tailscale

---

## 快速选择

| 你的需求 | 推荐模板 | 路径 |
|---------|---------|------|
| **Android 全局代理 + 访问家庭内网** | `ai-universal.json` | `01-tun-ai/` |
| **macOS 全局代理 + 官方 Tailscale** | `ai-universal-no-ts.json` | `01-tun-ai/` |
| **只代理浏览器/特定应用** | `ai-universal.json` | `02-notun-ai/` |
| **只代理浏览器，需要多地区分组** | `ai-global.json` | `02-notun-ai/` |
| **Netflix/Disney 等流媒体分流** | `streaming-full.json` | `03-full-streaming/` |
| **测试或低端设备** | `minimal.json` | `04-minimal/` |

---

## 模板详解

### 01. TUN 模式 - Android 专用（内置 Tailscale）

**文件**: `01-tun-ai/ai-universal.json`

**模式**: TUN + FakeIP + 内置 Tailscale endpoint

**适用平台**: Android

**Tailscale 方案**: sing-box 内置 endpoint，不需要安装官方 Tailscale App。Tailscale 流量通过路由规则 `100.64.0.0/10 → ts` 分流，**不加** `route_exclude_address` 排除 Tailscale 网段（Android 上加了会绕过 TUN，反而失效）。

**分组结构**:

| 分组名 | 类型 | 说明 |
|--------|------|------|
| `Proxy` | selector | 主选择器 |
| `AI` | selector | AI 服务专用，默认走自建节点 |
| `selfBuild` | selector | 手动选择自建节点 |
| `selfBuildAuto` | urltest | 自建节点自动测速 |
| `auto` | urltest | 全部节点自动测速 |
| `Global` | selector | 境外网站汇总 |
| `China` | selector | 中国网站（direct + Proxy） |

**已知问题**（sing-box 内置 Tailscale 的局限）:
- IPv4 NAT 下无法直连打洞，始终走 DERP 中继（延迟偏高）
- auth key 约 9 天后可能失效，需重新生成；建议在 Tailscale 控制台使用可复用 Key（Reusable + No expiry）
- 启动后需等待 `selfBuildAuto` 完成首次健康检查（约 5-15 秒），Tailscale 控制面才能正常连接

---

### 02. TUN 模式 - macOS 专用（配合官方 Tailscale）

**文件**: `01-tun-ai/ai-universal-no-ts.json`

**模式**: TUN + FakeIP，**无** Tailscale endpoint

**适用平台**: macOS、iOS（快捷指令切换场景）

**Tailscale 方案**: 使用官方 Tailscale 客户端独立运行。TUN inbound 的 `route_exclude_address` 排除了 Tailscale 网段，让两者互不干扰：

```json
"route_exclude_address": [
  "192.168.0.0/16",
  "100.64.0.0/10",
  "fd7a:115c:a1e0::/48"
]
```

**优势**: 官方客户端 NAT 穿透更强，IPv4 NAT 下可直连打洞，连接更稳定。

**分组结构**:

| 分组名 | 类型 | 说明 |
|--------|------|------|
| `Proxy` | selector | 主选择器 |
| `AI` | selector | AI 服务专用，默认走自建节点 |
| `selfBuild` | selector | 手动选择自建节点 |
| `selfBuildAuto` | urltest | 自建节点自动测速 |
| `auto` | urltest | 全部节点自动测速 |
| `Global` | selector | 境外网站汇总 |
| `China` | selector | 中国网站（direct + Proxy） |

---

### 03. NoTUN 模式 - AI 通用（含 Tailscale）

**文件**: `02-notun-ai/ai-universal.json`

**模式**: Mixed Inbound (HTTP/SOCKS5)，无 FakeIP，内置 Tailscale endpoint

**适用场景**: 只需代理浏览器，配合 SwitchyOmega 等插件

**监听端口**: `7890`

---

### 04. NoTUN 模式 - AI 全球多地区（含 Tailscale）

**文件**: `02-notun-ai/ai-global.json`

**模式**: Mixed Inbound (HTTP/SOCKS5)，无 FakeIP，内置 Tailscale endpoint

**适用场景**: 节点较多，需要按地区手动选择

**监听端口**: `7890`

**额外分组**: `HK`, `TW`, `SG`, `JP`, `US`, `Others`, `China`

> 与 `02-notun-ai/ai-universal.json` 一致，`China` 默认 `direct`，可在 Clash 面板手动切到 `Proxy`（临时全代理国内站时有用）。

---

### 05. 完整流媒体分流

**文件**: `03-full-streaming/streaming-full.json`

**模式**: TUN + FakeIP

**分组** (26个): Netflix, Disney+, YouTube, Spotify, TikTok, Telegram, Twitter, Facebook, Google, Apple, Microsoft, Games...

---

### 06. 极简配置

**文件**: `04-minimal/minimal.json`

**模式**: Mixed（仅 HTTP/SOCKS5，无 TUN），3 个分组（`Proxy` / `auto` / `direct`）

> 命名与其他模板对齐：DNS 服务器为 `remote`/`local`，主选择器为 `Proxy`。跨模板切换时面板内选择器状态可复用。

---

## AI 路由规则

所有 AI 相关模板都包含以下服务的路由（优先走自建节点）：

| 服务 | 域名 |
|------|------|
| **Anthropic/Claude** | claude.ai, api.claude.ai, anthropic.com, api.anthropic.com, statsig.anthropic.com |
| **OpenAI** | openai.com, api.openai.com, chat.openai.com, platform.openai.com |
| **Google Gemini** | gemini.google.com, generativelanguage.googleapis.com, aistudio.google.com |
| **Perplexity** | perplexity.ai |
| **Microsoft Copilot** | copilot.microsoft.com |
| **Cloudflare AI Gateway** | gateway.ai.cloudflare.com |

> **DeepSeek 说明**: DeepSeek 服务器托管在中国大陆，命中 `geosite-cn` 规则后走 `China → direct`，无需加入 AI 分组。如需通过代理访问，可在 Clash 面板将 `China` 分组手动切换到 `Proxy`。

**流量走向**:
```
AI 域名 → AI selector → selfBuild (优先) → selfBuildAuto (自动) → direct (兜底)
```

> 注：在含 Tailscale endpoint 的模板里，`ts` endpoint 的 `detour` 指向 `selfBuild`（手动选择器，立即可用），而非 `selfBuildAuto`（urltest，需等待健康检查）。这避免了"selfBuild 节点全挂时 Tailscale 也连不上"的连锁失败，控制面也无需等待 5-15 秒首测。

---

## FakeIP 说明

| 模板 | FakeIP |
|------|--------|
| `01-tun-ai/ai-universal.json` | ✅ |
| `01-tun-ai/ai-universal-no-ts.json` | ✅ |
| `02-notun-ai/` 全部 | ❌ |
| `03-full-streaming/streaming-full.json` | ✅ |
| `04-minimal/minimal.json` | ❌ |

---

## sing-box 版本兼容性

- **最低版本**: v1.12.0
- **推荐版本**: v1.13.x（最新稳定版）

---

## 性能调优默认值

所有模板已应用下列经验值（可按需在生成后覆盖）：

| 项 | 值 | 说明 |
|---|---|---|
| `dns.cache_capacity` | 4096 | DNS LRU 缓存，<1024 会被忽略 |
| `dns.independent_cache` | true | 不同 server 之间缓存隔离 |
| `urltest.interval` | 10m (ai-global 5m) | 自动测速周期 |
| `urltest.tolerance` | 100 ms | 抖动门槛，避免频繁切换影响长连接 |
| `cache_file.store_rdrc` | true | 持久化路由结果集 |
| `cache_file.store_fakeip` | true (开启 fakeip 时) | 持久化 fakeip 映射 |

---

## 验证配置

```bash
sing-box check -c config_template/01-tun-ai/ai-universal.json
```

---

## 订阅转换示例

```bash
# Android（内置 Tailscale）
python3 main.py -u "你的订阅链接" -t 01-tun-ai/ai-universal

# macOS（配合官方 Tailscale 客户端）
python3 main.py -u "你的订阅链接" -t 01-tun-ai/ai-universal-no-ts

# 仅浏览器代理
python3 main.py -u "你的订阅链接" -t 02-notun-ai/ai-universal

# 多地区分组
python3 main.py -u "你的订阅链接" -t 02-notun-ai/ai-global
```
