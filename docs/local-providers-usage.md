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
