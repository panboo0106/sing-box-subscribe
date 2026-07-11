# sing-box 配置模板

兼容 sing-box **v1.12+** 的配置模板，按目标平台分目录，全部使用 AI 路由风味。

## 目录布局

```
config_template/
├── ios/
│   └── mixed.json        浏览器代理 / 快捷指令场景
├── macos/
│   ├── tun.json          系统级代理，配合官方 Tailscale App
│   └── mixed.json        浏览器代理
├── android/
│   └── tun.json          系统级 + 内置 TS endpoint
├── linux/
│   └── tun.json          系统级 + 内置 TS endpoint + auto_redirect
└── README.md
```

> 旧路径（`ai/` `streaming/` `minimal/`）已删除。如需历史版本（streaming 分流、minimal 极简），用 `git log` 查找最后含旧目录的 commit 后 `git show <hash>:config_template/streaming/tun.json` 取回。

## 平台 → 模板速查

| 平台 | 推荐 | 备注 |
|---|---|---|
| **iOS** | `ios/mixed.json` | SFI 只能跑一个 VPN，搭配 iOS 快捷指令切换 Tailscale App |
| **macOS** | `macos/tun.json` | 配合官方 Tailscale 客户端，NAT 穿透更稳 |
| **macOS（仅浏览器）** | `macos/mixed.json` | 配合 SwitchyOmega 等插件 |
| **Windows** | `macos/tun.json` | 同 macOS（不依赖 macOS 特有字段） |
| **Android** | `android/tun.json` | 内置 Tailscale endpoint（与官方 App 互斥） |
| **Linux** | `linux/tun.json` | 内置 TS + `auto_redirect` 高性能 nftables 转发 |

## 各平台技术要点

### iOS

- 只提供 mixed（HTTP/SOCKS5），不提供 tun
- 完全不含 FakeIP / Tailscale endpoint / `route_exclude_address` 等字段
- Tailscale 由官方 App 独立运行，不与 sing-box 交互
- 典型用法：浏览器代理、快捷指令在 sing-box 与 Tailscale 之间切换

### macOS

- `macos/tun.json`：tun + mixed 双 inbound，含 `route_exclude_address: 100.64.0.0/10` 让 Tailscale App 流量绕过 sing-box TUN
- `macos/mixed.json`：仅 mixed，浏览器代理场景

### Android

- 必须含内置 sing-box Tailscale endpoint —— 官方 Tailscale App 与 sing-box 作为系统 VPN 服务不能共存
- 不排除 `100.64.0.0/10`，让 sing-box 路由 TS 流量到内置 endpoint

**Android TS endpoint 配置规则**（与 Linux 不通用）：

- `state_directory` 用相对路径 `tailscale`，会落在 SFA 工作目录 `/sdcard/Android/data/io.nekohasekai.sfa/files/tailscale`（可写）。**不能**用 `$HOME/...`：sing-box 对 `state_directory` 做 `os.ExpandEnv()`，Android 下 `$HOME` 未设置会展开成空串，路径变成 `/.config/...` 撞上只读根目录，启动报 `mkdir /.config: read-only file system`
- **不要**写 `auth_key`。Android GUI 客户端没有环境变量注入入口，留空后 sing-box 会在 SFA 通知栏弹出 Tailscale 登录 URL，浏览器授权即可
- 用不到 TS 时直接忽略登录通知，sing-box 主体（VPN + 路由）正常工作；TS endpoint 只在路由命中 `100.64.0.0/10` / `.ts.net` 时才会触发

**Android 内置 TS 已知风险**（社区报告，spec 内可接受范围）：

- Android 10 SIGSYS 崩溃（seccomp 拦截 syscall 434）：[issue #3233](https://github.com/SagerNet/sing-box/issues/3233)
- sing-box 1.13+ UDP 回归（Termux 等 UDP 服务连不上）：[issue #3863](https://github.com/SagerNet/sing-box/issues/3863)
- 双向可达性不对称（手机能被访问、访问不出去）：[issue #3755](https://github.com/SagerNet/sing-box/issues/3755)
- 约 9 天后 token 失效，需重新生成：[issue #3643](https://github.com/SagerNet/sing-box/issues/3643)

### Linux

- 含内置 TS endpoint + `auto_redirect: true` + `strict_route: true` + `stack: system`
- `auto_redirect` 用 nftables 重定向绕过 gvisor 性能瓶颈，比 macOS 模板快很多

**Linux 实战坑**：

- **nftables 冲突**：UFW（Ubuntu 默认）/ firewalld（RHEL 默认）/ Docker 会创建自己的 nftables 链，可能与 sing-box 冲突。排查：`nft list ruleset | grep sing-box`，若链不存在或被刷掉就是冲突。临时绕过：`auto_redirect` 改 `false` 退回 gvisor 路径
- **strict_route 与桥接虚拟机**：VirtualBox / KVM 桥接网卡上的 VM 网络可能被 `strict_route` 切断。修复：把虚拟机网段（如 `192.168.56.0/24`）加入 `route_exclude_address`
- **容器/嵌套虚拟化**：若网络异常，`stack` 从 `system` 改回 `mixed`（gvisor 路径换最大兼容性）

**systemd 部署**（仅 Linux）：默认 `state_directory: $HOME/.config/sing-box/tailscale`（sing-box 对该字段做 `os.ExpandEnv()` 展开）。systemd 上下文下 `$HOME` 可能未设置或为 `/root`，需在 service 单元里显式声明。

模板里的 `auth_key: "$TS_AUTHKEY"` 是**生成期占位符**，sing-box 自身不展开该字段：在 providers 文件配 `"ts_authkey": "tskey-auth-..."` 由 main.py 注入；不配则生成时自动剥离该字段，运行期走 `TS_AUTHKEY` 环境变量（tsnet 原生读取）或日志里的 login URL 授权。

```ini
[Service]
Environment=HOME=/var/lib/sing-box
Environment=TS_AUTHKEY=tskey-auth-xxxx
# 或直接改 config.json 把 state_directory 写成绝对路径
```

> Android 模板用相对路径 `tailscale`（落在 SFA 工作目录），见 §Android。

## AI 路由覆盖

`ai/*` 全部模板优先把以下服务走自建节点：

| 服务 | 域名 |
|---|---|
| **Anthropic / Claude** | claude.ai, api.claude.ai, anthropic.com, api.anthropic.com, statsig.anthropic.com, console.anthropic.com |
| **OpenAI** | openai.com, api.openai.com, chat.openai.com, platform.openai.com, auth.openai.com, cdn.openai.com, files.oaiusercontent.com |
| **Google Gemini** | gemini.google.com, generativelanguage.googleapis.com, aistudio.google.com, aiplatform.googleapis.com, makersuite.google.com |
| **Perplexity** | perplexity.ai |
| **Microsoft Copilot** | copilot.microsoft.com, sydney.bing.com |
| **Cloudflare AI Gateway** | gateway.ai.cloudflare.com |

**DeepSeek 说明**：DeepSeek 服务器在中国大陆，命中 `geosite-cn` 后走 `China → direct`，无需加入 AI 分组。

**流量走向**：

```
AI 域名 → AI selector → selfBuild (优先) → selfBuildAuto (自动) → direct (兜底)
```

> Tailscale endpoint 模板里 `ts.detour` 指向 `selfBuild`（手动选择器，立即可用），而非 `selfBuildAuto`（urltest，需等待健康检查）。避免 selfBuild 全挂时 Tailscale 也连不上的连锁失败。

## 性能调优默认值

| 项 | 值 | 说明 |
|---|---|---|
| `dns.cache_capacity` | 4096 | DNS LRU 缓存，<1024 会被忽略 |
| `dns.independent_cache` | true | 不同 server 之间缓存隔离 |
| `urltest.interval` | 10m | 自动测速周期 |
| `urltest.idle_timeout` | 30m | 30 分钟无流量停止测速，省电 |
| `urltest.tolerance` | 100 ms | 抖动门槛，避免频繁切换 |
| `tun.route_exclude_address` | RFC1918 + Tailscale + IPv6 link-local | 私有网段不进 TUN |
| `cache_file.store_rdrc` | true | 持久化路由结果集 |
| `cache_file.store_fakeip` | true（仅 tun + fakeip 时） | 持久化 fakeip 映射 |

## Clash 控制面安全（`clash_api.secret`）

所有模板 `external_controller` 绑在 `127.0.0.1:9090`，`secret` 默认为空。

- **风险**：同机内任何进程都能调用 Clash API 切换出站
- **加固**：把 `secret` 填随机字符串

## 验证配置

模板里的 `filter` + `{all}` 是订阅工具的 DSL，**不能直接对模板跑 `sing-box check`**（会报 `unknown field "filter"`）。先生成 config 再检查：

```bash
uv run python3 main.py --template_index <idx> --providers local_providers.json
sing-box check -c config.json
```

`linux/tun.json` 的 `auto_redirect` 是 Linux 专属字段，**在 macOS / Windows 上跑 check 会报 `initialize auto-redirect: invalid argument`**，需在 Linux 环境验证。

## 订阅转换示例

```bash
# 交互式选择模板
uv run python3 main.py --providers local_providers.json

# 或直接指定（--template_index 是 0-based）
uv run python3 main.py --template_index 4 --providers local_providers.json  # ios/mixed
```

模板序号顺序对应 `find config_template -name "*.json" | sort` 的字母序：

```
0: android/tun
1: ios/mixed
2: linux/tun
3: macos/mixed
4: macos/tun
```

## sing-box 版本兼容性

- **最低版本**：v1.12.0（DNS 新格式、`action` 字段）
- **推荐版本**：v1.13.x
- `linux/tun.json` 的 `auto_redirect` 需 v1.10+
