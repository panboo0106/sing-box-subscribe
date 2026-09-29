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

规则单独放在 `custom_rules.local.json`，无需逐个平台修改模板：

```bash
cp custom_rules.example.json custom_rules.local.json
```

在 `local_providers.json` 顶层引用它（以下字段合入已有文件）：

```json
{
  "custom_rules_file": "custom_rules.local.json"
}
```

然后只需维护规则文件里的数组（域名请替换成产品实际域名）：

```json
[
  {
    "domain_suffix": ["example.com", "example-api.com"],
    "outbound": "🇺🇸美国"
  },
  {
    "domain": ["app.example.org"],
    "outbound": "🇭🇰香港"
  }
]
```

相对路径以 **providers 文件所在目录**为基准，也可使用绝对路径。`*.local.json` 已被 Git 忽略，示例文件不包含真实规则。显式引用的文件不存在、JSON 错误或顶层不是数组时会报错，不会当成空规则继续生成。

- `domain`：精确匹配完整域名；`domain_suffix`：匹配域名后缀。至少填写一个非空字符串数组，同时填写时为 OR 匹配。
- `domain_suffix: ["example.com"]` 覆盖根域名及子域名；`[".example.com"]` 只覆盖子域名，不包含根域名。见 [sing-box 后缀匹配说明](https://sing-box.sagernet.org/migration/#domain_suffix-behavior-update)。
- `outbound`：与生成配置中的出口标签完全一致，可选已有分组、具体节点或 endpoint。内置模板有 `🇺🇸美国`、`🇭🇰香港`、`selfBuild`、`AI`、`Proxy`、`direct`。标签存在只代表配置可引用，不保证组内节点可用；地区组没有匹配节点时仍沿用现有的 direct 兜底。
- 每条只接受上述三个字段，生成器自动补 `action: route`。未知字段、空匹配、错误类型或不存在的出口会报出 `custom_rules[序号]`，终止当前配置生成。
- 不配置来源或在规则文件中填写 `[]` 保持原有分流；`Only-nodes: true` 时跳过规则文件读取和路由校验。
- 旧版在 providers 内写 `custom_rules: [...]` 的方式仍兼容；它与 `custom_rules_file` 不能同时配置，即便数组为空。Web 的 `--temp_json_data` 只支持内联规则，不允许读取服务器本地规则文件。

### 优先级与冲突

| 顺序 | 规则 | 与产品规则的关系 |
|---|---|---|
| 1 | 模板基础处理：嗅探、DNS、广告、模式、Tailscale、显式直连和内网 | 保留优先级，不被产品规则覆盖 |
| 2 | 自定义产品规则，按文件顺序 | 优先于模板 AI/国内分流 |
| 3 | 模板普通业务分流（AI、国内等） | 未被产品规则匹配的流量继续匹配 |
| 4 | 模板默认出口 | 兜底 |

内置模板用独立的 `{"custom_rules": true}` 对象标明第 2 层位置。生成器在这里替换规则并移除标记，不再猜测插入位置。自定义模板需在基础规则之后、业务分流之前添加同样的标记。非空规则遇到标记缺失、重复或格式错误时拒绝生成；已知基础动作、模式、内网、Tailscale endpoint 路由放在标记后也会报错。没有自定义规则的旧模板不要求添加标记。

- **同一匹配项指定不同出口：报错。** 逐个检查数组中的匹配项，比较时忽略大小写和尾部点；同出口的重复项允许。
- **宽泛规则在前，细分规则在后：警告。** 例如先把 `example.com` 及其子域名送往美国，再把 `api.example.com` 送往香港，后者会被遮住。把香港的精确规则放在前面即可形成例外；生成器不会擅自重排。
- **与前置模板域名规则重叠：提示模板优先。** 包括原有 `direct_domain` 覆盖，提示带规则索引。部分重叠只影响交集，不代表整条规则失效。
- **与后面的 AI/国内规则重叠：按优先级覆盖。** 这是自定义产品分流的预期用途，不当成错误。

静态检查限于 `domain`/`domain_suffix` 和前置简单域名规则，不下载或展开远程 `rule_set`，也不尝试求解 IP、逻辑、进程等所有条件组合。广告规则集等仍按模板顺序先匹配；有疑问时需在客户端连接记录中确认实际命中规则。加载、校验和合入逻辑集中在 `custom_rules.py`，`main.py` 只调用。

此字段只改变**流量出口**，DNS 仍沿用模板及原有 `auto_set_outbounds_dns` 行为，不会为产品同步创建 DNS 规则或指定 DNS 出口。产品的 API、登录等独立域名也需要覆盖。

### 生成与生效

修改规则文件后重新生成，再更新/重载客户端配置：

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
