# 使用本地配置文件保护订阅链接

## 背景

为了防止订阅链接意外泄露到 Git 仓库（如 GitHub），我们支持使用本地配置文件来存储敏感的订阅链接。

## 快速开始

### 1. 创建本地配置文件

复制示例文件：

```bash
cp providers.example.json local_providers.json
```

### 2. 编辑本地配置文件

在 `local_providers.json` 中添加你的订阅链接：

```json
{
  "subscribes": [
    {
      "url": "https://你的订阅链接",
      "tag": "my_sub",
      "enabled": true,
      "emoji": 1,
      "prefix": "",
      "User-Agent": "v2rayng"
    }
  ],
  "auto_set_outbounds_dns": {
    "proxy": "",
    "direct": ""
  },
  "save_config_path": "./config.json",
  "auto_backup": false,
  "exclude_protocol": "ssr",
  "config_template": "",
  "Only-nodes": false
}
```

**注意：** `local_providers.json` 已经被 `.gitignore` 排除，不会被提交到 Git 仓库。

### 3. 运行脚本

使用 `--providers` 参数指定本地配置文件：

```bash
# 使用本地配置文件
python main.py --providers ./local_providers.json

# 交互式选择模板
python main.py --providers ./local_providers.json

# 直接指定模板序号
python main.py --providers ./local_providers.json --template_index 0
```

## 自定义产品路由

在 `local_providers.json` 顶层添加 `custom_rules`，即可指定产品流量走哪个出口，无需逐个平台修改模板。下面是要合入现有文件的字段示例（域名请替换为产品实际域名）：

```json
{
  "custom_rules": [
    {
      "domain_suffix": ["example.com", "example-api.com"],
      "outbound": "🇺🇸美国"
    },
    {
      "domain": ["app.example.org"],
      "outbound": "🇭🇰香港"
    }
  ]
}
```

- `domain`：精确匹配完整域名；`domain_suffix`：匹配域名后缀。至少填写一个非空字符串数组，同时填写时为 OR 匹配。
- `outbound`：与生成配置中的出口标签完全一致，可选已有分组、具体节点或 endpoint。内置模板有 `🇺🇸美国`、`🇭🇰香港`、`selfBuild`、`AI`、`Proxy`、`direct`。标签存在只代表配置可引用，不保证组内节点可用；地区组没有匹配节点时仍沿用现有的 direct 兜底。
- 每条只接受上述三个字段，生成器自动补 `action: route`。未知字段、空匹配、错误类型或不存在的出口会报出 `custom_rules[序号]`，终止当前配置生成。
- 不填或填 `[]` 保持原行为；`Only-nodes: true` 时不应用或校验路由。

内置模板中的顺序为：原有基础处理（嗅探、DNS、广告、模式、Tailscale、直连/内网）→ `custom_rules`（按填写顺序）→ AI/国内分流 → 默认出口。同一域名命中多个产品规则时，靠前的规则优先；全局/直连模式仍优先于产品规则。

自定义模板优先在内网直连规则后插入；没有该规则时，放在最后一条嗅探、DNS 劫持、拒绝、模式或 direct 出口规则之后，没有这些规则则放开头。自定义模板的既有顺序可能不同，请检查生成结果。

此字段只改变**流量出口**，DNS 仍沿用模板及原有 `auto_set_outbounds_dns` 行为，不会为产品同步创建 DNS 规则或指定 DNS 出口。产品的 API、登录等独立域名也需要覆盖。

修改后重新生成，再更新/重载客户端配置：

```bash
# 生成全部平台配置
uv run python main.py --providers ./local_providers.json --all_templates

# 或仅生成 macOS TUN（当前模板序号为 4），默认输出 config.json
uv run python main.py --providers ./local_providers.json --template_index 4
sing-box check -c config.json
```

不要只编辑生成的 `config*.json`，下次生成会覆盖。校验失败时当前输出文件不会被覆盖；批量生成逐个保存，若后续模板失败，之前成功生成的文件仍保留。

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--providers` | 指定订阅配置文件路径 | `providers.json` |
| `--template_index` | 指定配置模板序号 | 交互式选择 |
| `--temp_json_data` | 临时 JSON 数据（Web 使用） | - |
| `--gh_proxy_index` | GitHub 加速链接索引 | - |

## 与 Web 模式的关系

在 Web 模式（Vercel）中，订阅链接通过网页表单提交，不会存储在服务器上，因此不需要使用本地配置文件。

本地配置文件主要用于：
- 本地 Python 脚本运行
- 保护订阅链接不被意外提交到 Git

## 示例：多人协作场景

假设团队成员各自有不同的订阅链接：

```bash
# 团队成员 A
cp providers.example.json alice_providers.json
# 编辑 alice_providers.json 添加自己的订阅
python main.py --providers ./alice_providers.json

# 团队成员 B
cp providers.example.json bob_providers.json
# 编辑 bob_providers.json 添加自己的订阅
python main.py --providers ./bob_providers.json
```

每个人的配置文件都独立且不会被提交到 Git 仓库。

## 故障排除

### 配置文件找不到

```bash
# 确保文件存在
ls -la local_providers.json

# 检查文件路径
python main.py --providers ./local_providers.json
```

### JSON 格式错误

使用 JSON 验证工具检查配置文件的语法：

```bash
# 使用 Python 验证
python3 -c "import json; json.load(open('local_providers.json'))"
```

### 订阅链接无效

检查订阅链接是否可以正常访问：

```bash
curl -L -A "v2rayng/1.0" "你的订阅链接"
```
