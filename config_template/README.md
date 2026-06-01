# sing-box 配置模板

兼容 sing-box **v1.12+** 的配置模板，按"路由风味（routing flavor）"分层，文件名表达 inbound 类型和平台。

---

## 目录布局

```
config_template/
├── ai/                      # AI 服务优先路由（Claude / OpenAI / Gemini / Perplexity / Copilot）
│   ├── tun-android.json     # TUN + 内置 Tailscale endpoint
│   ├── tun-macos.json       # TUN + 外部 Tailscale 客户端共存
│   ├── tun-linux.json       # TUN + auto_redirect + system stack（Linux 桌面/服务器最佳性能）
│   ├── mixed.json           # Mixed inbound（HTTP/SOCKS5），无 Tailscale
│   ├── mixed-ts.json        # Mixed inbound + 内置 Tailscale endpoint
│   └── mixed-global.json    # Mixed inbound + 多地区分组（HK/TW/SG/JP/US/Others）+ 内置 Tailscale
├── streaming/               # 完整流媒体分流（Netflix/Disney+/YouTube/...）
│   ├── tun.json             # TUN + FakeIP，通用
│   └── tun-linux.json       # 同上 + auto_redirect + system stack
├── minimal/                 # 极简（仅 Proxy / auto / direct）
│   └── mixed.json           # Mixed inbound
└── README.md
```

> ⚠️ **路径迁移**：旧的 `01-tun-ai/` `02-notun-ai/` `03-full-streaming/` `04-minimal/` 目录已经统一重组。若旧 URL 仍被引用，请按下表更新。

| 旧路径 | 新路径 |
|---|---|
| `01-tun-ai/ai-universal.json` | `ai/tun-android.json` |
| `01-tun-ai/ai-universal-no-ts.json` | `ai/tun-macos.json` |
| `02-notun-ai/ai-universal.json` | `ai/mixed-ts.json` |
| `02-notun-ai/ai-universal-no-ts.json` | `ai/mixed.json` |
| `02-notun-ai/ai-global.json` | `ai/mixed-global.json` |
| `03-full-streaming/streaming-full.json` | `streaming/tun.json` |
| `04-minimal/minimal.json` | `minimal/mixed.json` |

---

## 命名约定

文件名 = `<inbound>-<平台>` 或单 `<inbound>`：

- **inbound 维度**：`tun`（TUN+Mixed 双入站）/ `mixed`（仅 HTTP/SOCKS5）
- **平台后缀**：
  - `tun-android.json` — Android（含内置 TS endpoint）
  - `tun-macos.json` — macOS / iOS / Windows（外部 Tailscale，gvisor）
  - `tun-linux.json` — Linux 桌面/服务器（`auto_redirect: true` + `stack: system`）
  - 无后缀（如 `mixed.json`）= 跨平台通用
- **Tailscale 标记**：`-ts` 后缀代表内置 sing-box Tailscale endpoint；无 `-ts` 代表用外部 Tailscale 客户端或不使用 Tailscale
- **特殊用途**：`mixed-global` 代表多地区分组

---

## 平台 → 模板速查

| 平台 | 推荐 | 备注 |
|------|------|------|
| **Android** | `ai/tun-android.json` | 内置 Tailscale endpoint，统一管理 |
| **macOS** | `ai/tun-macos.json` | 配合官方 Tailscale 客户端，NAT 穿透更稳 |
| **iOS** | `ai/tun-macos.json` | iOS 同时只能跑一个 VPN，用快捷指令切换 |
| **Windows** | `ai/tun-macos.json` | 同 macOS 逻辑（不依赖 macOS 特有字段） |
| **Linux 桌面/服务器** | `ai/tun-linux.json` | `auto_redirect` + nftables 高性能转发 |
| **仅浏览器代理** | `ai/mixed.json` 或 `ai/mixed-ts.json` | 配合 SwitchyOmega 等插件 |
| **多地区分组** | `ai/mixed-global.json` | 节点多、需手动按地区选 |
| **流媒体精细分流** | `streaming/tun.json` 或 `streaming/tun-linux.json` | ⚠️ 不含 AI 分流 |
| **测试 / 低端设备** | `minimal/mixed.json` | 仅 Proxy/auto/direct |

### iOS 特别说明

iOS 系统限制：同时只允许一个活跃 VPN。sing-box (SFI) 和官方 Tailscale App 无法共存：
- 用 **iOS 快捷指令** 一键切换两个 App；或
- 在 VPS 部署 Tailscale Exit Node，iPhone 只跑 Tailscale。

### Linux 模板的取舍

`tun-linux.json` 与 `tun-macos.json` 的区别只有 3 个字段：
```json
"strict_route": true,         // Linux 上推荐启用，防 DNS 泄露
"auto_redirect": true,        // 启用 nftables 重定向，绕过 gvisor 性能瓶颈
"stack": "system"             // 配合 auto_redirect 用 system stack
```
未指定 `auto_redirect_input_mark` / `auto_redirect_output_mark`，sing-box 用内置默认值。如果系统已有 iptables/nft 规则需要协调，可手动加：
```json
"auto_redirect_input_mark": "0x2023",
"auto_redirect_output_mark": "0x2024"
```

---

## AI 路由规则

`ai/*.json` 全部覆盖以下服务（优先走自建节点）：

| 服务 | 域名 |
|------|------|
| **Anthropic / Claude** | claude.ai, api.claude.ai, anthropic.com, api.anthropic.com, statsig.anthropic.com, console.anthropic.com |
| **OpenAI** | openai.com, api.openai.com, chat.openai.com, platform.openai.com, auth.openai.com, cdn.openai.com, files.oaiusercontent.com |
| **Google Gemini** | gemini.google.com, generativelanguage.googleapis.com, aistudio.google.com, aiplatform.googleapis.com, makersuite.google.com |
| **Perplexity** | perplexity.ai |
| **Microsoft Copilot** | copilot.microsoft.com, sydney.bing.com |
| **Cloudflare AI Gateway** | gateway.ai.cloudflare.com |

> **DeepSeek 说明**：DeepSeek 服务器托管在中国大陆，命中 `geosite-cn` 后走 `China → direct`，无需加入 AI 分组。如需通过代理访问，在 Clash 面板将 `China` 切到 `Proxy`。

**流量走向**：
```
AI 域名 → AI selector → selfBuild (优先) → selfBuildAuto (自动) → direct (兜底)
```

> 含 Tailscale endpoint 的模板里，`ts.detour` 指向 `selfBuild`（手动选择器，立即可用），而非 `selfBuildAuto`（urltest，需等待健康检查）。这避免了"selfBuild 节点全挂时 Tailscale 也连不上"的连锁失败。

---

## FakeIP

| 模板 | FakeIP |
|------|--------|
| `ai/tun-*.json` | ✅ |
| `ai/mixed*.json` | ❌（NoTUN 不需要） |
| `streaming/tun*.json` | ✅ |
| `minimal/mixed.json` | ❌ |

---

## streaming/* 与 ai/* 的差异

`streaming/tun*.json` 是**完整流媒体分流**模板（26 个分组：Netflix、Disney+、YouTube、Spotify、TikTok、Telegram、Twitter、Facebook、Google、Apple、Microsoft、Games、HBO、Prime Video…），**不含** Claude / Gemini / Perplexity / Copilot 路由。这些站点会落到 `geosite-geolocation-!cn` → `Global` 分组（按地区手动选）。

如需精细 AI 分流，请改用 `ai/*` 模板，或在 `streaming/tun.json` 里把 AI 服务的 rule_set 和 outbound 手动并入。

---

## 性能调优默认值

所有模板已应用下列经验值：

| 项 | 值 | 说明 |
|---|---|---|
| `dns.cache_capacity` | 4096 | DNS LRU 缓存，<1024 会被忽略 |
| `dns.independent_cache` | true | 不同 server 之间缓存隔离 |
| `urltest.interval` | 10m | 自动测速周期 |
| `urltest.idle_timeout` | 30m | 30 分钟无流量停止测速，省电 |
| `urltest.tolerance` | 100 ms | 抖动门槛，避免频繁切换 |
| `tun.route_exclude_address` | RFC1918 + Tailscale + IPv6 link-local | 私有网段不进 TUN |
| `tun-linux 专用`：`auto_redirect: true` + `stack: system` | — | Linux nftables 转发，避开 gvisor 性能瓶颈 |
| `cache_file.store_rdrc` | true | 持久化路由结果集 |
| `cache_file.store_fakeip` | true（仅启用 fakeip 时） | 持久化 fakeip 映射 |

---

## 已知风险与可选加固

### Clash 控制面安全（`clash_api.secret`）

所有模板 `clash_api.external_controller` 绑在 `127.0.0.1:9090`，仅本机可访问；`secret` 默认为空。

- **风险**：同机内任何进程都能调用 Clash API 切换出站。
- **加固**：填随机字符串：
  ```json
  "clash_api": { "secret": "随机字符串", "..." }
  ```

### `external_ui_download_url` 的 gh-proxy 依赖

- gh-proxy 历史上多次域名变更/宕机；首次启动若 gh-proxy 不可用，控制面 404。
- **Fallback**：
  1. 手动下载 metacubexd 到 `external_ui` 路径，避免运行时拉取。
  2. 改 jsdelivr 直拉（须客户端整仓克隆，配置稍复杂）。
  3. 待 `main.py` 集成仓库已有的 `gh_proxy_helper.py`。

---

## sing-box 版本兼容性

- **最低版本**：v1.12.0（DNS 新格式、`action` 字段）
- **推荐版本**：v1.13.x（最新稳定，`auto_redirect` 已成熟）
- `tun-linux.json` 的 `auto_redirect` 需 v1.10+

---

## 验证配置

```bash
sing-box check -c config_template/ai/tun-android.json
```

---

## 订阅转换示例

```bash
# Android（内置 Tailscale）
python3 main.py -u "你的订阅链接" -t ai/tun-android

# macOS / iOS / Windows（配合外部 Tailscale 客户端）
python3 main.py -u "你的订阅链接" -t ai/tun-macos

# Linux 桌面/服务器（高性能）
python3 main.py -u "你的订阅链接" -t ai/tun-linux

# 仅浏览器代理
python3 main.py -u "你的订阅链接" -t ai/mixed

# 多地区分组
python3 main.py -u "你的订阅链接" -t ai/mixed-global

# 完整流媒体分流
python3 main.py -u "你的订阅链接" -t streaming/tun
```
