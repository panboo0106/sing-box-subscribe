# 模板精简设计

**日期**：2026-06-01
**作者**：panboo + Claude
**状态**：待评审

## 1. 背景与动机

当前 `config_template/` 有 10 个模板共 4850 行，按多维度组合：

```
ai/        7 个：mixed / mixed-ts / mixed-global / tun-macos / tun-android / tun-linux / tun-linux-ts
streaming/ 2 个：tun / tun-linux
minimal/   1 个：mixed
```

维度过多导致：

- **认知开销大**：选择文件需要在「路由风味 × inbound 类型 × 平台 × Tailscale」四个维度间做组合判断
- **路径迁移历史包袱**：README 里近 50 行专门讲旧路径映射、`-ts` 例外规则等
- **冗余实现**：`streaming/` 和 `minimal/` 实际未在使用
- **现存 fatal 错误**：所有 10 个模板都有 `dns.servers[].local.detour = "direct"`，与 sing-box 1.13+ 的「禁止指向空 direct outbound」检查冲突

## 2. 目标

精简到**按平台 × 接入方式**两个维度的最小完整集合：

- 每个平台对应一个明确的入口目录
- 每个目录下只有 1-2 个文件，对应 tun（系统级）或 mixed（应用级）
- 全部使用 AI 路由风味（覆盖 Claude / OpenAI / Gemini / Perplexity / Copilot）
- 修复 sing-box 1.13+ 的 detour 报错

## 3. 非目标

- 不重构 `parsers/` / `main.py` / 订阅生成逻辑
- 不改变 `geosite` / `rule_set` 等路由规则的内容（只调整文件组织）
- 不提供「无 Tailscale」的 Linux 变体（用户确认只用内置 TS）
- 不保留 `streaming/`（完整流媒体分流）和 `minimal/`（极简）—— 必要时从 git 历史恢复

## 4. 最终目录结构

```
config_template/
├── ios/
│   └── mixed.json        浏览器代理 / 快捷指令场景
├── macos/
│   ├── tun.json          系统级代理，配合官方 Tailscale App
│   └── mixed.json        浏览器代理
├── android/
│   └── tun.json          系统级 + 内置 TS endpoint（与 Tailscale App 不能共存）
├── linux/
│   └── tun.json          系统级 + 内置 TS endpoint + auto_redirect/system stack
└── README.md
```

**合计 5 个模板**，从 10 → 5。

## 5. 各模板技术要点

| 模板 | inbound | TUN/FakeIP | 内置 TS endpoint | TS 网段排除 | Linux 优化 |
|---|---|---|---|---|---|
| `ios/mixed.json` | mixed | ❌ | ❌ | 不适用 | 不适用 |
| `macos/tun.json` | tun + mixed | ✅ | ❌（用官方 App） | ✅ exclude 100.64.0.0/10 | ❌ |
| `macos/mixed.json` | mixed | ❌ | ❌ | 不适用 | 不适用 |
| `android/tun.json` | tun + mixed | ✅ | ✅ | ❌（让 sing-box 路由） | ❌ |
| `linux/tun.json` | tun + mixed | ✅ | ✅ | ❌ | ✅ auto_redirect + strict_route + stack:system |

### 5.1 iOS 特殊处理

- 完全不含 TUN/FakeIP/Tailscale 相关字段
- 仅 mixed inbound，作为浏览器代理或 iOS 快捷指令切换场景
- Tailscale App 独立运行，不与 sing-box 交互

**iOS 模板的硬性验收清单（同 §9 的人工检查项）**：

- ❌ 无 `dns.fakeip` 块
- ❌ 无 `inbounds[].type == "tun"` 或任何 tun 相关字段
- ❌ 无 `endpoints` / `tailscale` 类型 DNS 服务器
- ❌ 无 `route_exclude_address`
- ✅ AI 路由规则与 macOS 一致（Claude / OpenAI / Gemini / Perplexity / Copilot）
- ✅ `sing-box check` 通过

### 5.2 macOS 双模板的存在理由

- `tun.json`：日常系统级代理。需要 `route_exclude_address: 100.64.0.0/10` 让 Tailscale App 流量绕过 sing-box TUN
- `mixed.json`：浏览器/SwitchyOmega 等应用级代理使用
- 用户确认日常用 tun，FakeIP 保留

### 5.3 Android 必须内置 TS

- 官方 Tailscale App 与 sing-box 在 Android 上同为系统 VPN 服务，**不能共存**
- 因此 sing-box 必须内置 TS endpoint
- 不排除 `100.64.0.0/10`，让 sing-box 自己处理 TS 流量

**Android 配置方式与 Linux 不通用**（2026-06-01 实测补充）：

- sing-box 不做 shell 变量展开。Linux/systemd 上 `state_directory: $HOME/.config/...` 能 work 是靠 systemd 的 `Environment=HOME=...` 注入；**Android GUI 客户端没有这种入口**，`$HOME` 直接当字面量，`mkdir /.config` 撞上 Android 根目录只读 → `post-start endpoint/tailscale[ts]: tsnet: mkdir /.config: read-only file system`
- Android 模板的 `state_directory` 必须用相对路径（如 `tailscale`），落到 SFA 工作目录 `/sdcard/Android/data/io.nekohasekai.sfa/files/` 下
- Android 模板**不写** `auth_key`。sing-box 在 GUI 客户端会弹通知给出 Tailscale 登录 URL，浏览器授权（[官方文档](https://sing-box.sagernet.org/configuration/endpoint/tailscale/)：「By default, sing-box will log the login URL (or popup a notification on graphical clients)」）

**Android 内置 TS 已知风险**（社区报告，可接受范围内）：

| 风险 | issue |
|---|---|
| Android 10 SIGSYS 崩溃（seccomp 拦截 syscall 434） | [#3233](https://github.com/SagerNet/sing-box/issues/3233) |
| sing-box 1.13+ UDP 回归 | [#3863](https://github.com/SagerNet/sing-box/issues/3863) |
| 双向可达性不对称（mobile 出向 ICMP 不走 TUN） | [#3755](https://github.com/SagerNet/sing-box/issues/3755) |
| 约 9 天 token 失效 | [#3643](https://github.com/SagerNet/sing-box/issues/3643) |

### 5.4 Linux 单一变体

- 用户确认仅用内置 TS 方案（不维护外部 tailscaled 共存版）
- 保留 Linux 特有的 `auto_redirect: true` + `strict_route: true` + `stack: system`
- README 中保留 nftables 冲突、虚拟机网段、容器场景三个实战坑的提示

## 6. 删除清单

### 6.1 整目录删除

| 路径 | 行数 | 删除理由 |
|---|---|---|
| `config_template/streaming/tun.json` | 824 | 流媒体分流场景未使用 |
| `config_template/streaming/tun-linux.json` | 818 | 同上 |
| `config_template/minimal/mixed.json` | 187 | 极简版未使用 |

### 6.2 单文件删除

| 路径 | 行数 | 删除/合并理由 |
|---|---|---|
| `config_template/ai/mixed-global.json` | 525 | 多地区手选场景未使用 |
| `config_template/ai/mixed-ts.json` | 420 | mixed 模式下不需要 sing-box 内置 TS（mixed 不接管系统路由） |
| `config_template/ai/tun-linux.json` | 402 | 外部 tailscaled 共存方案未使用 |

### 6.3 文件移动 / 重命名

| 旧路径 | 新路径 | 改动 |
|---|---|---|
| `ai/tun-android.json` | `android/tun.json` | 移动 + 删 `dns.servers[].local.detour: "direct"` |
| `ai/tun-macos.json` | `macos/tun.json` | 移动 + 删 `detour: "direct"` |
| `ai/tun-linux-ts.json` | `linux/tun.json` | 移动 + 删 `detour: "direct"` |
| `ai/mixed.json` | `macos/mixed.json` | 移动 + 删 `detour: "direct"` |

### 6.4 新建文件

| 路径 | 来源 | 改动 |
|---|---|---|
| `ios/mixed.json` | 派生自 `macos/mixed.json` | 派生后逐字段审计，去掉任何 iOS SFI 不支持/不适用的字段；保留所有 AI 路由规则；inbound 只保留 mixed |

## 7. 共性修复：DNS `local` 服务器的 `detour: "direct"`

所有保留模板的 DNS 配置：

```jsonc
// 修复前（fatal: detour to an empty direct outbound makes no sense）
{
  "tag": "local",
  "type": "https",
  "server": "223.5.5.5",
  "detour": "direct"
}

// 修复后
{
  "tag": "local",
  "type": "https",
  "server": "223.5.5.5"
}
```

DNS 默认就是直连，删除 detour 字段后行为完全等价，并解决 sing-box 1.13+ 启动失败。

> `ios/mixed.json` 派生自已修复后的 `macos/mixed.json`，自动继承此修复，无需重复处理。

## 8. README.md 重写

旧 README 255 行，新 README 目标 100-120 行。

### 8.1 保留内容

- 5 模板平台速查表
- AI 路由覆盖范围（服务和域名表）
- 各平台关键技术点：iOS 限制、macOS Tailscale 共存、Android App 冲突、Linux auto_redirect 坑
- 性能调优默认值表
- 订阅转换示例（5 条命令）
- Clash 控制面安全提示
- sing-box 版本兼容性

### 8.2 删除内容

- 旧路径迁移表（旧目录已删完，迁移说明短句一行即可）
- 三维度命名规则说明（新结构无需）
- `-ts` 例外说明（无此维度）
- `minimal/` `streaming/` `mixed-global` 相关章节

### 8.3 新增内容

- 旧路径 → 新路径单行迁移提示（一行）
- iOS 模板「仅 mixed」的设计说明（为什么没有 tun 版）

## 9. 验证计划

模板里的 `filter: [...]` + `{all}` 是订阅工具 `main.py` 的 DSL，不是 sing-box 原生字段。因此**不能直接对模板跑 `sing-box check`**（会报 `unknown field "filter"`）。

**正确的两段式验证**：

### 9.1 模板语法验证（任何平台）

```bash
python3 -c "import json; json.load(open('config_template/<platform>/<inbound>.json'))"
```

确保 JSON 合法、关键字段（inbounds、outbounds、route）齐全。

### 9.2 生成 config 后验证（按平台）

```bash
# macOS / 通用模板可在 macOS 上完整 check
uv run python3 main.py --template_index <idx> --providers local_providers.json
sing-box check -c config.json
```

**linux/tun.json 的跨平台限制**：含 `auto_redirect: true` + `stack: system` 是 Linux 专属 inbound 字段，**不能在 macOS / Windows 上跑 `sing-box check`**（会报 `initialize auto-redirect: invalid argument`，这是 sing-box 的 platform-specific init 行为）。在 macOS 上用 JSON 解析 + 字段审计验证；真正的 init check 需在 Linux 环境执行。

iOS 模板额外人工检查：

- 无 `dns.fakeip` 块
- 无 `inbounds[].type == "tun"` 或 tun 相关字段
- 无 `endpoints` / `tailscale` 类型 DNS 服务器
- 无 `route_exclude_address`

合并到当前生成 config（`/opt/homebrew/etc/sing-box/config.json`）路径迁移验证：

```bash
python3 main.py -u "<订阅链接>" -t macos/tun
sing-box check -c /opt/homebrew/etc/sing-box/config.json
sing-box run -c /opt/homebrew/etc/sing-box/config.json  # 不再报 fatal
```

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| iOS 模板无现成参考，可能漏字段 | 从 `macos/mixed.json` 派生后逐字段审计；sing-box check + iOS SFI 实测 |
| 用户订阅命令依赖旧路径 `ai/...` | README 写明新路径，并保留单行 PathMigration 说明 |
| `streaming/` `minimal/` 删除不可逆 | git 历史保留；README 提示 `git show HEAD~N:path` 可恢复 |
| 当前生成的 `config.json` 用旧路径生成 | 用户重新生成订阅后采用新路径，旧 config 不受影响 |

## 11. 实施顺序

1. 创建 `ios/` `macos/` `android/` `linux/` 四个新目录
2. 移动/重命名 4 个保留文件，逐个删 `detour: "direct"`
3. 从 `macos/mixed.json` 派生 `ios/mixed.json`，做字段审计
4. 对 5 个新文件分别跑 `sing-box check`
5. 删除 `ai/` `streaming/` `minimal/` 三个旧目录
6. 重写 `config_template/README.md`
7. commit
8. 用户验证一份生成的 config 真能跑

## 12. 不在本设计范围

- `parsers/` 目录的解析器修改
- 订阅源 (`local_providers.json` / `providers.json`) 修改
- API / Vercel 部署相关
- 其他 docs（如 `vercel-cn.md`）的更新
