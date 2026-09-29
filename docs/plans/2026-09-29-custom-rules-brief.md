# 自定义产品路由任务简报

## 1. Goal and scope

用户批准在 `local_providers.json` 增加 `custom_rules`：集中维护产品域名到出口的映射，生成所有平台配置时自动注入并校验出口。
范围为生成器、离线测试和使用文档；不新增面板、selector、DNS 策略，不修改真实订阅或运行中配置，不推送、开 PR 或部署。

## 2. Settled design and constraints

- Routing: standard；L2 `R2-CONTRACT`（新增配置字段），独立早期设计审阅和最终双轴评审。
- Execution: inline — 同一个生成入口和测试接缝，控制器已掌握相关代码，无需独立实现上下文。
- Worktree: `/Users/leo/.worktrees/sing-box-subscribe/custom-routing-rules`；branch: `feat/custom-routing-rules`；base: `099a3ceb43bab74077fa3ffe3f3662ab4cff4b89`，来源为默认分支 main。
- 输入是规则数组。每条仅包含 `domain`、`domain_suffix`、`outbound`；至少一个非空域名字符串数组，出口为非空字符串。两个域名字段均存在时遵循 sing-box 的 OR 语义。不增加任意原生规则透传。
- 生成时补 `action: route`；目标必须是生成后已有的 outbound 或 endpoint tag，包括生成的订阅节点/分组。校验失败抛出含字段位置的 ValueError，单个配置不会保存无效结果。
- 保持自定义规则的填写顺序；内置模板中放在内网直连之后、AI/国内分流之前，保留嗅探、DNS、广告拒绝、模式、Tailscale 和已有 direct_* 规则的优先级。
- Decision: 自定义模板缺少内网直连锚点时，放在最后一个嗅探、DNS 劫持、拒绝、clash_mode 或 direct 出口规则之后；没有这些前置规则时放开头 — 兼容现有 config_template 入口并保留 direct_* 优先级 — 非标准模板需用户检查最终优先级。
- 不填写或填 `[]` 不改变原有输出；Only-nodes 沿用仅节点模式，不应用或校验路由。批量生成不得污染共享输入或重复追加规则。
- Decision: 仅修改流量路由，不改变 DNS，包括 auto_set_outbounds_dns 的现有处理 — 原需求是指定流量出口 — 文档明确 DNS 请求不一定走该出口，不能承诺完整地域解析行为。
- Artifact: 本简报为 task-scoped，最后消费者为交付审阅；keep-local 时保留。无伴随计划/进度文件。代码、测试、用户文档为 durable。

## 3. Observable acceptance

统一检查：`uv run --frozen python tests/test_custom_rules.py`，通过生成入口及离线 CLI 验证。

1. Given 产品域名 example.com 指定 🇺🇸美国，When 生成任一内置平台配置，Then 产生带 route 动作的相应域名规则；精确域名、后缀及组合均支持。
2. Given 两条用户规则分别指定美国/香港，When 生成配置，Then 它们保持顺序，位于既有基础规则之后、AI/国内分流之前。
3. Given 自定义模板无内网锚点或规则为空，When 生成配置，Then 自定义规则仍生效并保留已存在的基础动作和模式优先级。
4. Given 规则指向不存在的标签或包含无效结构（非数组、空匹配、未知字段），When 生成配置，Then 明确报出 custom_rules 及错误位置；CLI 非零退出且不覆盖已有输出。
5. Given 规则目标是订阅生成的节点/分组或模板 endpoint，When 生成配置，Then 通过校验并引用该目标。
6. Given 没有 custom_rules 或值为 []，When 生成配置，Then 输出等同原有行为；Only-nodes 不受路由配置影响。
7. Given 同一份 custom_rules 用于全部平台，When 批量生成，Then 每个平台各注入一次且 providers 输入保持不变。
8. Given 模板已有 DNS 和 direct_domain/direct_ip 策略，When 加入 custom_rules，Then DNS 内容不变且既有直连覆盖仍位于产品规则之前。

回归：`tests/test_parsers.py`（26 项）、`tests/check_template_drift.py`（5 模板）通过；离线 CLI 生成全部模板。对兼容本机的生成配置运行 sing-box 1.14.2 check；Linux 的 auto_redirect 需 Linux，不声称已做 Linux 运行验证。

## 4. Necessary steps and dependencies

1. 早期审阅本简报与生成接缝；新增 `tests/test_custom_rules.py`，先获得行为缺失的 RED（已完成）。
2. 步骤 1 后修改 `main.py` 实现校验和注入；补充 `README.md`、`docs/local-providers-usage.md`、`config_template/README.md` 使用说明；跑验收与回归（实现与验证完成）。
3. 步骤 2 后按 `request-review` 独立评审两轴并处理发现；本地提交、保留分支和工作区。

## 5. Verification results and pending work

- 初始 Git clean，无 sequencer，无本任务既有 SDD ledger。
- `uv sync --frozen` 成功，Python 3.14.7；未改依赖或锁文件。
- 基线：26 个解析器测试、5 个模板一致性检查通过（2026-09-29）。
- 早期独立评审（custom_rules_review）：发现无内网锚点时 fallback 可能抢在 direct_* 之前；accepted，设计改为保留 direct 规则前置并增加回归。建议补充启用 auto_set_outbounds_dns 的兼容检查，已纳入测试。
- 首轮新行为 RED：旧实现忽略 custom_rules，缺少规则且无效输入不报错；省略/空数组/Only-nodes 兼容测试通过。修正生成分组测试的输入接缝为现有的订阅节点分组 key。
- GREEN：`uv run --frozen python tests/test_custom_rules.py` 10 项通过，包含 5 模板参数化覆盖、离线 CLI 批量生成以及错误时保留旧文件。
- 最终回归：26 个解析器测试、5 个模板一致性检查通过；`git diff --check` 通过。main.py 原有 CRLF 保留，新增行用 LF，避免无关全文件格式化。
- `sing-box check -c /dev/stdin`：通过真实生成入口以离线 socks 节点、两条 custom_rules 生成配置，经 sing-box 1.14.2 检查 android/tun、ios/tun、macos/mixed、macos/tun 均 exit 0，无诊断。Linux 配置已通过生成测试，但 auto_redirect 的原生检查未在 macOS 执行。
- 验收 1–8 均有上述脚本证据；未对实际产品域名发起网络请求或重载运行中的服务。
- 最终双轴评审在当前提交冻结后进行，实际报告与绑定记录保存在 Git 私有元数据；交付仅本地分支，不发布或清理工作区。
