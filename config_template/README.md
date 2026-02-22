# sing-box 配置模板

本目录包含兼容 sing-box v1.12+ 的配置模板。

## 文件说明

### 主要配置模板

| 文件名 | 说明 | 适用场景 |
|--------|------|----------|
| `config_template_1.12.json` | 标准 1.12 模板（含 FakeIP） | 推荐使用 |
| `config_template_groups_rule_set_tun.json` | 分组规则模板（TUN 模式） | 需要分组管理 |
| `config_template_groups_rule_set_tun_fakeip.json` | 分组规则模板（TUN + FakeIP） | 需要 FakeIP |
| `config_template_no_groups_tun_VN.json` | 无分组简化模板（越南） | 简化配置 |

### 备份文件

`.legacy.json` 文件是迁移前的旧版本配置备份，如需参考旧格式可查看。

## sing-box 版本兼容性

- **最低版本**: v1.12.0
- **推荐版本**: v1.12.22 (当前最新稳定版)

## 从旧版本迁移

如需将旧配置迁移到 1.12+ 格式，可使用仓库根目录的迁移脚本：

```bash
# 迁移单个文件
python3 migrate_config.py old_config.json new_config.json

# 示例
python3 migrate_config.py my_config.json my_config_v1.12.json
```

### 主要变更点

从 1.11 迁移到 1.12 的主要变更：

1. **DNS 服务器格式**
   - 旧: `"address": "tls://8.8.8.8"`
   - 新: `"type": "tls", "server": "8.8.8.8"`

2. **DNS 规则变更**
   - 移除了 `"outbound": "any"` 规则
   - 添加了 `route.default_domain_resolver`

3. **废弃选项**
   - `dns.strategy` 已废弃，移至 `route.default_domain_resolver.strategy`
   - 出站连接的 `domain_strategy` 改为 `domain_resolver` 对象

## 验证配置

使用 sing-box 命令验证配置有效性：

```bash
# 验证配置
sing-box check -c config_template_1.12.json

# 格式化并保存
sing-box format -w -c config_template_1.12.json
```

## 规则集来源

配置中使用的规则集主要来自：
- [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat) - 主要规则集
- [Toperlock/sing-box-geosite](https://github.com/Toperlock/sing-box-geosite) - 自定义规则集

## 注意事项

1. 所有配置模板都使用 TUN 模式，需要管理员/root 权限运行
2. FakeIP 配置需要启用 `experimental.cache_file`
3. Clash API 默认监听 `127.0.0.1:9090`，可通过 Web UI 管理
