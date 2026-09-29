# 自定义产品路由任务简报

## 1. Goal and scope

用户批准集中维护产品域名到出口的映射，随后要求规则配置与 Python 处理逻辑分别独立为文件，并明确与模板的冲突及优先级（用户回复“同意两个”）。使用 `custom_rules.local.json` 保存规则，由 `local_providers.json` 的 `custom_rules_file` 引用，`custom_rules.py` 负责加载、校验和合入。
范围为生成器、离线测试和使用文档；不新增面板、selector、DNS 策略，不修改真实订阅或运行中配置，不推送、开 PR 或部署。

## 2. Settled design and constraints

- Routing: standard；L2 `R2-CONTRACT`（新增配置字段），独立早期设计审阅和最终双轴评审。
- Execution: inline — 同一个生成入口和测试接缝，控制器已掌握相关代码，无需独立实现上下文。
- Worktree: `/Users/leo/.worktrees/sing-box-subscribe/custom-routing-rules`；branch: `feat/custom-routing-rules`；base: `099a3ceb43bab74077fa3ffe3f3662ab4cff4b89`，来源为默认分支 main。
- 输入是规则数组。每条仅包含 `domain`、`domain_suffix`、`outbound`；至少一个非空域名字符串数组，出口为非空字符串。两个域名字段均存在时遵循 sing-box 的 OR 语义。不增加任意原生规则透传。
- 生成时补 `action: route`；目标必须是生成后已有的 outbound 或 endpoint tag，包括生成的订阅节点/分组。校验失败抛出含字段位置的 ValueError，单个配置不会保存无效结果。
- 保持自定义规则的填写顺序；内置模板中放在内网直连之后、AI/国内分流之前，保留嗅探、DNS、广告拒绝、模式、Tailscale 和已有 direct_* 规则的优先级。
- Decision: 模板用独占对象 `{"custom_rules": true}` 显式声明插入位置，替代旧版通过 ip_is_private 猜测边界；生成后移除标记。非空自定义规则遇到无标记、多标记或错误标记时拒绝生成。没有自定义规则的旧模板继续可用。有标记时检查 DNS/嗅探、模式、内网、拒绝动作和 Tailscale endpoint 路由没有放到标记之后；普通业务规则保持原顺序。
- Decision: 相对规则文件路径以 providers 文件目录为基准，绝对路径原样使用。显式引用的缺失/坏 JSON/非数组文件报错，不静默忽略。保留旧内联 custom_rules 作为兼容入口，两种来源同时出现报错。文件加载仅用于本地 --providers；Web 临时 JSON 不读取服务器本地规则文件。不增加默认自动发现或额外 CLI 参数。
- Decision: 相同匹配项指向不同出口报错（域名比较忽略大小写和尾部点）；同出口重复项允许。按用户填写顺序匹配，不自动排序；前面的后缀规则遮蔽后面的细分规则时警告并指出索引，具体规则放在宽泛规则前可作为例外。内联模板前置域名规则与产品规则有重叠时给出优先级提示；模板业务分流被自定义覆盖是预期行为。远程 rule_set、IP/逻辑/进程等条件不做完整静态求交，文档明确检查边界。
- 不填写或填 `[]` 不改变原有输出；Only-nodes 沿用仅节点模式，不应用或校验路由。批量生成不得污染共享输入或重复追加规则。
- Decision: 仅修改流量路由，不改变 DNS，包括 auto_set_outbounds_dns 的现有处理 — 原需求是指定流量出口 — 文档明确 DNS 请求不一定走该出口，不能承诺完整地域解析行为。
- Artifact: 本简报为 task-scoped，最后消费者为交付审阅；keep-local 时保留。无伴随计划/进度文件。代码、测试、用户文档为 durable。

## 3. Observable acceptance

统一检查：`uv run --frozen python tests/test_custom_rules.py`，通过生成入口及离线 CLI 验证。

1. Given 产品域名 example.com 指定 🇺🇸美国，When 生成任一内置平台配置，Then 产生带 route 动作的相应域名规则；精确域名、后缀及组合均支持。
2. Given 两条用户规则分别指定美国/香港，When 生成配置，Then 它们保持顺序，位于既有基础规则之后、AI/国内分流之前。
3. Given 模板在基础规则后、业务规则前放置唯一插入标记，When 生成配置，Then 自定义规则只占该位置且最终输出无标记；缺标记、多标记或基础规则放在标记后时明确失败，旧模板在没有自定义规则时不变。
4. Given 规则指向不存在的标签或包含无效结构（非数组、空匹配、未知字段），When 生成配置，Then 明确报出 custom_rules 及错误位置；CLI 非零退出且不覆盖已有输出。
5. Given 规则目标是订阅生成的节点/分组或模板 endpoint，When 生成配置，Then 通过校验并引用该目标。
6. Given 没有 custom_rules 或值为 []，When 生成配置，Then 输出等同原有行为；Only-nodes 不受路由配置影响。
7. Given 同一份 custom_rules 用于全部平台，When 批量生成，Then 每个平台各注入一次且 providers 输入保持不变。
8. Given 模板已有 DNS 和 direct_domain/direct_ip 策略，When 加入 custom_rules，Then DNS 内容不变且既有直连覆盖仍位于产品规则之前。
9. Given providers 引用独立规则文件，When 从项目目录生成全部模板，Then 按 providers 所在目录解析相对路径且规则统一生效；坏文件、双来源、临时 JSON 读本地文件时非零退出并保留已有输出。
10. Given example.com 的同一匹配项指定不同出口，When 生成配置，Then 拒绝冲突；宽泛后缀在前遮住 api.example.com 时产生索引警告；细分规则在前时允许例外并保留顺序。
11. Given 前置模板直连域名覆盖产品域名，When 生成配置，Then 提示模板规则优先；普通模板 AI/国内分流位于产品规则之后，不作为冲突拒绝。

回归：`tests/test_parsers.py`（26 项）、`tests/check_template_drift.py`（5 模板）通过；离线 CLI 生成全部模板。对兼容本机的生成配置运行 sing-box 1.14.2 check；Linux 的 auto_redirect 需 Linux，不声称已做 Linux 运行验证。

## 4. Necessary steps and dependencies

1. 续做基线为本分支 9bb7a63，clean。既有 10 项验收与回归证据用于模块拆分的行为保持部分；对文件加载、显式边界、冲突提示先补 RED 测试（完成）。
2. 步骤 1 后新增 `custom_rules.py` 和 `custom_rules.example.json`，让 `main.py` 仅调用；5 个内置模板加入标记；更新原有使用文档、README 和本简报；验收与回归（完成）。
3. 步骤 2 后按 L2（配置契约及顺序语义）完成独立双轴评审、处理发现、本地提交。原任务分支和工作区保留，不发布。

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

### 2026-09-29 用户反馈续做

- 上述 GREEN 和评审证据对应第一版 9bb7a63，不能证明本次新增行为。第一版双轴评审 clean。
- 更新依据：用户要求两份独立文件、避免规则冲突并明确优先级；standard / inline 路线继续，独立早期与最终评审继续。
- 早期独立评审 custom_rules_review：direct_* 注入可能修改标记后的业务直连规则；accepted，经 RED 复现后限定为只查找标记前的规则，必要时在标记前新增直连覆盖。双编码临时 JSON、Only-nodes、数组内单项冲突建议均 accepted 并覆盖。
- RED：旧实现对独立文件加载、显式标记替换、基础规则位置校验、重复出口冲突、后缀遮蔽警告、前置模板覆盖提示、标记后直连覆盖和临时 JSON 文件限制的测试均按预期失败。
- GREEN：`uv run --frozen python tests/test_custom_rules.py` 20 项通过（含参数化用例和 CLI 子进程）；`tests/test_parsers.py` 26 项通过，`tests/check_template_drift.py` 5 模板通过，`git diff --check` 通过。
- sing-box 1.14.2：android/tun、ios/tun、macos/mixed、macos/tun 分别以空规则和 2 条规则生成后运行 `sing-box check -c /dev/stdin`，8 次均 exit 0、无诊断。Linux 生成覆盖但未作原生 auto_redirect 检查；未测试实际外部流量。
- 官方域名后缀语义核实来源：https://sing-box.sagernet.org/migration/#domain_suffix-behavior-update 。带点后缀不覆盖根域名，边界用例已覆盖。
- 本次验收 1–11 已有上述证据；最终独立双轴评审针对后续冻结提交，报告存 Git 私有元数据。本地交付，简报与工作区继续保留。
