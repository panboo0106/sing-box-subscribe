# 任务简报:解析器接缝统一 + 死代码清理

日期:2026-09-25 · 分支:`refactor/parser-seam` · 来源:improve-architecture 评审候选 1、5,用户批示"1 5 修"。

## 路由与风险记录

- 入口:**standard**(本简报即任务载体)。命中 Full 提醒条件 `R3-JUDGMENT`(解析器契约统一属架构判断);用户在候选清单后直接批示落地、未选 brainstorming,按 routing 规则记录该决定并以 standard 继续。
- 风险级别:**L3**(R3-JUDGMENT)。人类批准 = 用户批示;独立评审 = 非实现者子代理在 PR 前评审 diff。
- 附带安全修复:移除 `ss.py` 对订阅内容的 `eval()`(降低风险,不引入新安全边界)。

## 目标与验收标准

1. **统一 parse 契约**:所有协议解析器 `parse(data: str) -> list[dict]`(通常 1 个节点,ss+shadow-tls 返回 2 个);坏输入抛 `ParseError(ValueError 子类)`,不再返回 `None`、不再 print、不再返回元组。
2. **共享助手模块** `parsers/common.py`:收拢 query 展平、IPv6 括号剥离、path 并回 netloc、insecure 真值判断、multiplex 块、tag 回退、首端口提取、宽容 dict 字面量解析(JSON → ast.literal_eval,**绝不 eval**)。每个助手至少 2 个真实调用方。
3. **错误策略单点**:坏节点跳过策略只在 `main.py:parse_content` 一处;修复解析失败重复追加上一节点的 bug(main.py:206-211),不打印节点 URI(防订阅信息进日志)。
4. **死代码清理**:`tool.py` 删除零调用方的 `get_encoding/firstLine/checkKeywords/filterNodes/replaceStr/prefixStr/removeNodes/is_ip/ConfigSSH` 及 paramiko/scp/chardet 导入链;`main.py` 移除 `from api.app import TEMP_DIR`。依赖清单(requirements.txt/pyproject)不动,留作后续。
5. **测试**:新增 `tests/test_parsers.py`(纯脚本,风格同 `check_template_drift.py`,项目无 pytest):每协议至少 1 条合法 URI + 关键坏输入;含重复节点 bug 回归测试与 eval 不执行的对抗测试。`check_template_drift.py` 保持通过;ruff 通过;端到端跑一次 main.py 验证生成。

## 有意的行为变化(评审时核对)

- 解析失败:旧行为重复追加上一节点(首条失败则 UnboundLocalError 崩溃)→ 新行为跳过并打印协议名。
- insecure 语义统一:各解析器统一接受 `insecure/allowInsecure/allow_insecure` 的 `1/true/yes/on`(旧:trojan 只认 allowInsecure=1,hysteria2 认 insecure∈{1,true} 等)。vmess 的反向逻辑(tls 默认 insecure)保持原样。
- multiplex 块:旧代码缺 `max-streams` 且缺 `max-connections` 时 KeyError(节点被吞)→ 新代码只写存在的字段,sing-box 用默认值。ss 的 protocol 值同时收拢到 smux/yamux/h2mux 白名单(旧 ss 接受任意值、产出 sing-box 无效配置;vmess/vless/trojan 原本就是白名单)。两个连带改善:ss 备注含 "protocol" 子串不再 KeyError 吞节点;vmess 的 padding 额外接受字符串 `'True'`(此前只认 JSON true)。
- tuic、http 与 ssr 的 tag 现在做 URL 解码(与其他协议一致;此前这三个不解码,`%20` 会原样进 tag)。
- `common://`、`clash2base64://` 之类指向非协议模块的行:get_parser 对无 parse 属性的模块返回 None 跳过(旧实现 AttributeError 中断整个生成,clash2base64 为既有隐患,common 是本次新增模块)。
- loads_lenient 的 ast.literal_eval 回退对 true/false/null 做子串替换,理论上可能改写含这些子串的字符串值(旧 eval 实现同样或更糟);JSON 优先路径无此问题。
- wg 缺 `ip/address` 参数:旧 TypeError → 新 ParseError(同样被跳过,但走单点策略)。
- ss 的 v2ray-plugin/shadow-tls 字典:`eval` → `json.loads` 优先、`ast.literal_eval` 回退;`True == 1` 使下游 `== 1` 判断行为不变。

## 不在范围

候选 2(模板生成器)、3(generate_config 接缝)、4(分组策略收拢);api/app.py 重构;依赖清单精简;genName 随机性。

## 影响面

`parsers/*.py`(除 clash2base64.py,它是反向转换器非解析器)、`main.py`(仅 parse_content/get_nodes/第 6 行导入)、`tool.py`(仅删)、`tests/`(仅增)。消费方唯一:main.py(进程内)与 api/app.py(经 subprocess,契约不变)。
