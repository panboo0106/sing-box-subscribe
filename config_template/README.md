# sing-box 配置模板

本目录包含兼容 sing-box v1.12+ 的配置模板，按使用场景分类整理。

## 目录结构

```
config_template/
├── 01-tun-ai/           # TUN 模式 + AI 专用路由（推荐）
│   └── ai-universal.json
├── 02-notun-ai/         # NoTUN 模式 + AI 专用路由
│   ├── ai-universal.json      # 简洁版
│   └── ai-global.json         # 多地区分组版
├── 03-full-streaming/   # 完整流媒体分流
│   └── streaming-full.json
├── 04-minimal/          # 极简配置
│   └── minimal.json
└── README.md
```

---

## 快速选择

| 你的需求 | 推荐模板 | 路径 |
|---------|---------|------|
| **手机/电脑全局代理**，AI 走自建节点 | `ai-universal.json` | `01-tun-ai/` |
| **只代理浏览器/特定应用**，简洁配置 | `ai-universal.json` | `02-notun-ai/` |
| **只代理浏览器**，需要多地区分组 | `ai-global.json` | `02-notun-ai/` |
| **需要 Netflix/Disney 等流媒体分流** | `streaming-full.json` | `03-full-streaming/` |
| **测试或低端设备** | `minimal.json` | `04-minimal/` |

---

## 模板详解

### 01. TUN 模式 - AI 通用模板

**文件**: `01-tun-ai/ai-universal.json`

**模式**: TUN + FakeIP

**适用场景**:
- macOS / iOS / Android / Windows / Linux
- 需要全局代理（所有应用自动走代理）
- AI 服务需要指定节点（如美国、日本、新加坡）
- 有 Tailscale 网络需求

**分组结构**:

| 分组名 | 类型 | 说明 |
|--------|------|------|
| `Proxy` | selector | 主选择器，包含所有节点 |
| `AI` | selector | AI 服务专用，默认 selfBuild01 |
| `auto` | urltest | 自动测速选最快节点 |
| `direct` | direct | 直连 |
| `Global` | selector | 境外网站汇总 |
| `China` | selector | 中国网站（direct + Proxy） |

**特点**:
- 最简洁实用的 TUN 配置
- 支持 Tailscale DNS (`.ts.net`)
- AI 路由包含：OpenAI, Claude, Gemini, Perplexity, Copilot, DeepSeek

---

### 02. NoTUN 模式 - AI 全球模板

**文件**: `02-notun-ai/ai-global.json`

**模式**: Mixed Inbound (HTTP/SOCKS5)，无 FakeIP

**适用场景**:
- 只需要代理浏览器
- 配合 SwitchyOmega/Clash Verge 等插件使用
- 不想创建虚拟网卡

**监听端口**: `7890` (Mixed HTTP/HTTPS/SOCKS5)

**分组结构**:

| 分组名 | 类型 | 筛选条件 |
|--------|------|---------|
| `Proxy` | selector | 主选择器 |
| `AI` | selector | SelfBuild/US/JP/SG/auto |
| `Global` | selector | 所有地区节点汇总 |
| `SelfBuild` | selector | `自建\|selfbuild\|🏠` |
| `HK` | selector | `香港\|Hong Kong\|HK\|🇭🇰` |
| `TW` | selector | `台湾\|Taiwan\|TW\|🇹🇼` |
| `SG` | selector | `新加坡\|Singapore\|SG\|🇸🇬` |
| `JP` | selector | `日本\|Japan\|JP\|🇯🇵` |
| `US` | selector | `美国\|US\|USA\|America\|🇺🇸` |
| `Others` | selector | 排除已知地区 |
| `auto` | urltest | 自动测速 |

**使用方法**:
```bash
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
# 或
export ALL_PROXY=socks5://127.0.0.1:7890
```

---

### 02. NoTUN 模式 - AI 通用模板（简洁版）

**文件**: `02-notun-ai/ai-universal.json`

**模式**: Mixed Inbound (HTTP/SOCKS5)，无 FakeIP

**适用场景**:
- 只需要代理浏览器或特定应用
- 配合浏览器插件使用（如 SwitchyOmega）
- 不想创建虚拟网卡，保持系统网络不变
- 多平台通用（Windows/macOS/Linux）

**监听端口**: `7890` (Mixed HTTP/HTTPS/SOCKS5)

**分组结构**:

| 分组名 | 类型 | 说明 |
|--------|------|------|
| `Proxy` | selector | 主选择器，包含所有节点 |
| `AI` | selector | AI 服务专用，默认 selfBuild01 |
| `auto` | urltest | 自动测速选最快节点 |
| `direct` | direct | 直连 |
| `Global` | selector | 境外网站汇总 |
| `China` | selector | 中国网站（direct + Proxy） |

**特点**:
- 最简洁的 NoTUN 配置
- 支持 Tailscale DNS (`.ts.net`)
- AI 路由包含：OpenAI, Claude, Gemini
- 无 FakeIP，DNS 解析更直接

**使用方法**:
```bash
export https_proxy=http://127.0.0.1:7890
export http_proxy=http://127.0.0.1:7890
# 或
export ALL_PROXY=socks5://127.0.0.1:7890
```

---

### 03. NoTUN 模式 - AI 全球模板（多地区分组版）

**文件**: `02-notun-ai/ai-global.json`

**模式**: Mixed Inbound (HTTP/SOCKS5)，无 FakeIP

**适用场景**:
- 需要手动选择特定地区节点
- 节点较多时按地区筛选
- 不同网站需要不同地区出口

**监听端口**: `7890` (Mixed HTTP/HTTPS/SOCKS5)

**分组结构**:

| 分组名 | 类型 | 筛选条件 |
|--------|------|---------|
| `Proxy` | selector | 主选择器 |
| `AI` | selector | SelfBuild/US/JP/SG/auto |
| `Global` | selector | 所有地区节点汇总 |
| `SelfBuild` | selector | `自建\|selfbuild\|🏠` |
| `HK` | selector | `香港\|Hong Kong\|HK\|🇭🇰` |
| `TW` | selector | `台湾\|Taiwan\|TW\|🇹🇼` |
| `SG` | selector | `新加坡\|Singapore\|SG\|🇸🇬` |
| `JP` | selector | `日本\|Japan\|JP\|🇯🇵` |
| `US` | selector | `美国\|US\|USA\|America\|🇺🇸` |
| `Others` | selector | 排除已知地区 |
| `auto` | urltest | 自动测速 |

**特点**:
- 节点多时按需选择地区
- AI 优先走自建节点
- 适合有多个地区节点的订阅

---

### 04. 完整流媒体分流

**文件**: `03-full-streaming/streaming-full.json`

**模式**: TUN + FakeIP

**适用场景**:
- 需要解锁 Netflix、Disney+、HBO 等流媒体
- 不同服务需要不同地区节点
- 精细控制每个应用的出口

**分组结构** (26个分组):

| 类别 | 分组名 |
|------|--------|
| 核心 | `Proxy`, `auto`, `direct`, `Global`, `China` |
| AI | `OpenAI` |
| 流媒体 | `Netflix`, `Disney+`, `YouTube`, `Spotify`, `TikTok`, `BiliBili`, `Bahamut`, `Streaming` |
| 社交 | `Telegram`, `Twitter`, `Facebook` |
| 科技 | `Google`, `Apple`, `Microsoft`, `Games` |
| 地区 | `HongKong`, `TaiWan`, `Singapore`, `Japan`, `America`, `Others` |

**特点**:
- 每个流媒体服务独立分组
- 可按需选择解锁节点
- 适合节点较多的订阅

---

### 05. 极简配置

**文件**: `04-minimal/minimal.json`

**模式**: TUN

**适用场景**:
- 测试 sing-box 是否正常工作
- 低端设备资源有限
- 只需要最基本的代理功能

**分组结构** (3个分组):

| 分组名 | 类型 | 说明 |
|--------|------|------|
| `proxy` | selector | 主代理 |
| `auto` | urltest | 自动测速 |
| `direct` | direct | 直连 |

**特点**:
- 最简单，无复杂规则
- 仅 mixed-in 入站
- 适合调试和入门

---

## AI 路由规则

所有 AI 相关模板都包含以下 AI 服务的路由：

| 服务 | 域名 |
|------|------|
| **OpenAI** | chat.openai.com, api.openai.com, platform.openai.com |
| **Anthropic/Claude** | claude.ai, api.claude.ai, anthropic.com |
| **Google Gemini** | gemini.google.com, aistudio.google.com |
| **Perplexity** | perplexity.ai |
| **Microsoft Copilot** | copilot.microsoft.com |
| **DeepSeek** | chat.deepseek.com, api.deepseek.com |

**流量走向**:
```
AI 域名 → AI selector → selfBuild (优先) → US/JP/SG/auto (备选)
```

---

## FakeIP 说明

### 什么是 FakeIP？

FakeIP 是一种 DNS 优化技术：
- DNS 查询立即返回假 IP（198.18.x.x），零延迟
- 真实 DNS 解析在 sing-box 后台并行进行
- 节省 DNS 查询等待时间，提升网页打开速度

### 模板 FakeIP 支持

| 模板 | FakeIP | 说明 |
|------|--------|------|
| `01-tun-ai/ai-universal.json` | ✅ | TUN 模式有效 |
| `02-notun-ai/ai-universal.json` | ❌ | NoTUN 无需 FakeIP |
| `02-notun-ai/ai-global.json` | ❌ | NoTUN 无需 FakeIP |
| `03-full-streaming/streaming-full.json` | ✅ | TUN 模式有效 |
| `04-minimal/minimal.json` | ❌ | 简化配置 |

---

## sing-box 版本兼容性

- **最低版本**: v1.12.0
- **推荐版本**: v1.12.22 (当前最新稳定版)

---

## 验证配置

```bash
# 验证配置有效性
sing-box check -c config_template/01-tun-ai/ai-universal.json

# 格式化配置
sing-box format -w -c config_template/01-tun-ai/ai-universal.json
```

---

## 订阅转换示例

```bash
# 使用 TUN AI 模板（全局代理）
python3 main.py -u "你的订阅链接" -t 01-tun-ai/ai-universal

# 使用 NoTUN AI 模板（简洁版，仅浏览器代理）
python3 main.py -u "你的订阅链接" -t 02-notun-ai/ai-universal

# 使用 NoTUN AI 模板（多地区分组版）
python3 main.py -u "你的订阅链接" -t 02-notun-ai/ai-global

# 使用流媒体模板
python3 main.py -u "你的订阅链接" -t 03-full-streaming/streaming-full
```

或在 `subscribes.json` 中指定：
```json
{
  "subscribes": [
    {
      "url": "你的订阅链接",
      "tag": "my_sub",
      "enabled": true,
      "subgroup": "机场节点"
    }
  ],
  "config_template": "01-tun-ai/ai-universal.json"
}
```

---

## 已删除的重复模板

以下模板因功能重复已被合并或删除：

| 原文件名 | 替代方案 | 原因 |
|---------|---------|------|
| `config_template_tun_ai_global.json` | `01-tun-ai/ai-universal.json` | 功能被覆盖 |
| `config_template_universal_ai.json` | `01-tun-ai/ai-universal.json` | 命名统一 |
| `config_template_notun_ai.json` | `02-notun-ai/ai-global.json` | 功能被覆盖 |
| `config_template_groups_rule_set_tun_fakeip.json` | `03-full-streaming/streaming-full.json` | 合并为同一类 |
| `config_template_1.12.json` | 删除 | 旧格式不再维护 |
