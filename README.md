# 操作说明去看[英文文档](https://github.com/Toperlock/sing-box-subscribe/blob/main/instructions/README.md)，中文文档操作说明不再提供

# 免责声明：sing-box-subscribe.vercel.app域名目前已被其他人占用，与本项目无关。后果自负
![image](https://github.com/Toperlock/sing-box-subscribe/assets/86833913/f9af80bc-f1b7-45dd-a2eb-e26910069f21)

### 使用 `/config/URL` 添加参数符号已修改，从原来的 `/&` 改为 `&`。有问题请提issue，不要打扰 `sing-box`

```
https://xxxxxxx.vercel.app/config/https://xxxxxxsubscribe?token=123456&file=https://github.com/Toperlock/sing-box-subscribe/raw/main/config_template/config_template_groups_rule_set_tun.json
```

```
https://xxxxxxx.vercel.app/config/https://xxxxxxsubscribe?token=123456&file=2
```

本地python执行脚本命令：

```
python main.py
```

或者你可以直接带template_index参数选定模板，0表示第一个模板(no flask不支持此参数)

```
python main.py --template_index=0
```

#### 使用本地配置文件（保护订阅链接）

为了防止订阅链接泄露到 Git 仓库，推荐使用本地配置文件：

```bash
# 1. 复制示例配置文件
cp providers.example.json local_providers.json

# 2. 编辑 local_providers.json，添加你的订阅链接

# 3. 运行时使用 --providers 参数指定本地配置文件
python main.py --providers ./local_providers.json --template_index=0
```

**注意：** `local_providers.json` 已被 `.gitignore` 排除，不会被提交到 Git 仓库，保护你的订阅链接安全。

详细文档请参考：[docs/local-providers-usage.md](docs/local-providers-usage.md)

#### local_providers.json 字段说明

```json
{
  "subscribes": [
    {
      "url": "订阅链接或本地文件路径",
      "tag": "内部标识符",
      "enabled": true,
      "emoji": 1,
      "subgroup": "订阅名称",
      "prefix": "节点名前缀",
      "ex-node-name": "关键词1|关键词2",
      "User-Agent": "clashmeta"
    }
  ],
  "auto_set_outbounds_dns": {
    "proxy": "dns_proxy",
    "direct": "dns_direct"
  },
  "save_config_path": "./config.json",
  "auto_backup": false,
  "exclude_protocol": "ssr",
  "config_template": "",
  "Only-nodes": false
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| url | string | 订阅链接（支持 V2/Clash/Sing-box 格式）或本地文件路径 |
| tag | string | 内部标识符，用于在配置模板中引用 |
| enabled | boolean | 是否启用此订阅（true/false） |
| emoji | number | 是否在节点名添加国旗 emoji（1/0） |
| subgroup | string | 订阅名称，会自动生成对应的出站组 |
| prefix | string | 节点名前缀（空字符串表示不添加） |
| ex-node-name | string | 过滤节点关键词，多个用 \| 分隔（排除） |
| User-Agent | string | 请求订阅时使用的 UA（如 clashmeta/sing-box/v2rayng） |
| auto_set_outbounds_dns | object | 自动设置出站对应的 DNS 服务器 |
| save_config_path | string | 生成配置文件的保存路径 |
| auto_backup | boolean | 是否自动备份旧配置（true/false） |
| exclude_protocol | string | 排除的协议类型（如 ssr,vmess，用逗号分隔） |
| config_template | string | 自定义配置模板的 URL |
| Only-nodes | boolean | 是否仅输出节点信息（true/false） |

支持Docker

```
docker build --tag 'sing-box' .
docker run -p 5000:5000 sing-box:latest
```

支持自定义GitHub加速链接（使用参数&gh=1 数字代表使用第一个github加速），默认不加此参数。只有原始GitHub文件链接或者已经使用以下GitHub加速链接才能替换

```
1. "https://gh-proxy.com/",
2. "https://gh.sageer.me/",
3. "https://ghproxy.com/",
4. "https://mirror.ghproxy.com/",
5. "https://cdn.jsdelivr.net",
6. "https://testingcf.jsdelivr.net"
```

### 根据已有的qx，surge，loon，clash规则列表自定义规则集[https://github.com/Toperlock/sing-box-geosite](https://github.com/Toperlock/sing-box-geosite)

### wechat规则集源文件写法：
```json
{
  "version": 1,
  "rules": [
    {
      "domain": [
        "dl.wechat.com",
        "sgfindershort.wechat.com",
        "sgilinkshort.wechat.com",
        "sglong.wechat.com",
        "sgminorshort.wechat.com",
        "sgquic.wechat.com",
        "sgshort.wechat.com",
        "tencentmap.wechat.com.com",
        "qlogo.cn",
        "qpic.cn",
        "servicewechat.com",
        "tenpay.com",
        "wechat.com",
        "wechatlegal.net",
        "wechatpay.com",
        "weixin.com",
        "weixin.qq.com",
        "weixinbridge.com",
        "weixinsxy.com",
        "wxapp.tc.qq.com"
      ]
    },
    {
      "domain_suffix": [
        ".qlogo.cn",
        ".qpic.cn",
        ".servicewechat.com",
        ".tenpay.com",
        ".wechat.com",
        ".wechatlegal.net",
        ".wechatpay.com",
        ".weixin.com",
        ".weixin.qq.com",
        ".weixinbridge.com",
        ".weixinsxy.com",
        ".wxapp.tc.qq.com"
      ]
    },
    {
      "ip_cidr": [
        "101.32.104.4/32",
        "101.32.104.41/32",
        "101.32.104.56/32",
        "101.32.118.25/32",
        "101.32.133.16/32",
        "101.32.133.209/32",
        "101.32.133.53/32",
        "129.226.107.244/32",
        "129.226.3.47/32",
        "162.62.163.63/32"
      ]
    }
  ]
}
```
配置文件添加源文件规则集：
```
{
  "tag": "geosite-wechat",
  "type": "remote",
  "format": "source",
  "url": "https://raw.githubusercontent.com/Toperlock/sing-box-geosite/main/wechat.json",
  "download_detour": "auto"
}
```

