# sing-box 配置模板

兼容 sing-box **v1.12+** 的配置模板，按"路由风味（routing flavor）"分层，文件名表达 inbound 类型和平台。

---

## 目录布局

```
config_template/
├── ai/                      # AI 服务优先路由（Claude / OpenAI / Gemini / Perplexity / Copilot）
│   ├── tun-android.json     # TUN + 内置 Tailscale endpoint
│   ├── tun-macos.json       # TUN + 外部 Tailscale 客户端共存
│   ├── tun-linux.json       # TUN + auto_redirect + system stack（Linux，外部 Tailscale 客户端）
│   ├── tun-linux-ts.json    # TUN + auto_redirect + 内置 Tailscale endpoint（Linux 服务器推荐）
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

文件名规则按 **三个独立维度** 组合：`<inbound>[-<平台>][-ts]`

#### 维度 1：inbound 类型（必有，文件名第一段）

| 值 | 含义 |
|---|---|
| `tun` | TUN + Mixed 双入站（系统级代理） |
| `mixed` | 仅 HTTP/SOCKS5（应用级代理） |

#### 维度 2：平台后缀（可选，第二段）

| 值 | 含义 |
|---|---|
| `-android` | Android 专属（gvisor，不排除 100.64/10） |
| `-macos` | macOS / iOS / Windows 通用（外部 Tailscale，gvisor） |
| `-linux` | Linux 专属（`auto_redirect` + `strict_route` + `stack: system`） |
| _（无）_ | 跨平台通用 |

#### 维度 3：Tailscale 标记（可选，最后一段）

| 值 | 含义 |
|---|---|
| `-ts` | 含内置 sing-box Tailscale endpoint |
| _（无）_ | 用外部 Tailscale 客户端，或完全不用 Tailscale |

#### 约定例外（不显式带 `-ts` 但含内置 TS）

- `tun-android.json` — Android 不能与官方 Tailscale App 同时跑 VPN，**只能用内置 TS**，是 Android 的唯一方案
- `mixed-global.json` — 多地区分组场景默认含 TS，对应"全功能版"语义

如需例外文件的"无 TS" 变体，对应使用 `tun-macos.json` / `mixed.json`。

---

## 平台 → 模板速查

| 平台 | 推荐 | 备注 |
|------|------|------|
| **Android** | `ai/tun-android.json` | 内置 Tailscale endpoint，统一管理 |
| **macOS** | `ai/tun-macos.json` | 配合官方 Tailscale 客户端，NAT 穿透更稳 |
| **iOS** | `ai/tun-macos.json` | iOS 同时只能跑一个 VPN，用快捷指令切换 |
| **Windows** | `ai/tun-macos.json` | 同 macOS 逻辑（不依赖 macOS 特有字段） |
| **Linux 桌面（已装 tailscaled）** | `ai/tun-linux.json` | 配合官方 tailscaled，`auto_redirect` 高性能 |
| **Linux 服务器（一站式）** | `ai/tun-linux-ts.json` | 内置 TS endpoint，省去 tailscaled，单进程管理 |
| **仅浏览器代理** | `ai/mixed.json` 或 `ai/mixed-ts.json` | 配合 SwitchyOmega 等插件 |
| **多地区分组** | `ai/mixed-global.json` | 节点多、需手动按地区选 |
| **流媒体精细分流** | `streaming/tun.json` 或 `streaming/tun-linux.json` | ⚠️ 不含 AI 分流 |
| **测试 / 低端设备** | `minimal/mixed.json` | 仅 Proxy/auto/direct |

### iOS 特别说明

iOS 系统限制：同时只允许一个活跃 VPN。sing-box (SFI) 和官方 Tailscale App 无法共存：
- 用 **iOS 快捷指令** 一键切换两个 App；或
- 在 VPS 部署 Tailscale Exit Node，iPhone 只跑 Tailscale。

### Linux 模板的取舍

Linux 提供两种 Tailscale 方案：

| 文件 | Tailscale 方案 | 适用 |
|---|---|---|
| `tun-linux.json` | 外部 tailscaled 守护进程 | 已习惯 systemd 管理 tailscaled 的桌面用户 |
| `tun-linux-ts.json` | sing-box 内置 TS endpoint | 服务器/VPS，希望单 binary 部署 |

两者共享 Linux 特性（`auto_redirect: true` + `strict_route: true` + `stack: system`）。`tun-linux.json` 排除 `100.64.0.0/10`（让 tailscaled 处理）；`tun-linux-ts.json` 不排除（让 sing-box 自己路由到 `ts` endpoint）。

> **`tun-linux-ts.json` 的 `state_directory` 路径**：默认 `$HOME/.config/sing-box/tailscale`，适合桌面用户手动 `sing-box run -c config.json`。如用 systemd 部署，`$HOME` 在 service 上下文下可能未设置或为 `/root`，需在 service 单元里显式声明：
> ```ini
> [Service]
> Environment=HOME=/var/lib/sing-box
> # 或者直接改 config.json 把 state_directory 写成绝对路径，例如 /var/lib/sing-box/tailscale
> ```

`tun-linux.json` 与 `tun-macos.json` 的区别只有 3 个字段：
```json
"strict_route": true,         // Linux 上推荐启用，防 DNS 泄露
"auto_redirect": true,        // 启用 nftables 重定向，绕过 gvisor 性能瓶颈
"stack": "system"             // 配合 auto_redirect 用 system stack
```
未指定 `auto_redirect_input_mark` / `auto_redirect_output_mark`，sing-box 用内置默认值（`0x2023` / `0x2024`）。如果系统已有 iptables/nft 规则需要协调，可手动指定其他值。

#### ⚠️ Linux 实战坑

- **`auto_redirect` 与 UFW/firewalld/Docker 的 nftables 冲突**：sing-box 启动时会插入自己的 nftables 链。若机器跑 UFW（Ubuntu 默认）、firewalld（RHEL/Fedora 默认）或 Docker（默认创建 `DOCKER` 链），可能出现规则顺序错乱、Docker 容器外网不通、或 sing-box 自己的链被宿主防火墙清空。排查思路：`nft list ruleset | grep sing-box`，若链不存在或被刷掉就是冲突。临时绕过：把 `auto_redirect` 改回 `false` 退回 gvisor 路径（牺牲性能但稳定）。
- **`strict_route: true` 与 VirtualBox / KVM 桥接 / 多网卡场景**：strict_route 会对未识别的网络段返回 unreachable，桥接网卡上的虚拟机网络可能被切断。排查：虚拟机内 `ping 网关` 不通就是命中。修复：手动把虚拟机网段加入 `route_exclude_address`（如 `192.168.56.0/24` for VBox host-only），或把 `strict_route` 改回 `false`（macOS 模板默认值）。
- **容器/嵌套虚拟化场景**：如遇网络异常，可把 `stack` 从 `system` 改回 `mixed`（编译时默认），用 gvisor 路径换最大兼容性。

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

# Linux 桌面（外部 tailscaled）
python3 main.py -u "你的订阅链接" -t ai/tun-linux

# Linux 服务器（内置 TS endpoint，省去 tailscaled）
python3 main.py -u "你的订阅链接" -t ai/tun-linux-ts

# 仅浏览器代理
python3 main.py -u "你的订阅链接" -t ai/mixed

# 多地区分组
python3 main.py -u "你的订阅链接" -t ai/mixed-global

# 完整流媒体分流
python3 main.py -u "你的订阅链接" -t streaming/tun
```
