"""加载产品路由，并在模板声明的位置校验、合入规则。"""

import copy
import json
import warnings
from pathlib import Path


DOMAIN_FIELDS = ("domain", "domain_suffix")


def load_rules(providers, providers_file=None):
    """文件路径相对于本地 providers 文件；临时 JSON 不读取服务器文件。"""
    if providers.get("Only-nodes"):
        return []
    if "custom_rules_file" not in providers:
        return providers.get("custom_rules", [])
    if providers_file is None:
        raise ValueError("custom_rules_file 仅支持本地 --providers 文件，临时 JSON 请使用 custom_rules")
    if "custom_rules" in providers:
        raise ValueError("custom_rules_file 与 custom_rules 不能同时配置")
    filename = providers["custom_rules_file"]
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("custom_rules_file 必须是非空文件路径")
    path = Path(filename)
    if not path.is_absolute():
        path = Path(providers_file).resolve().parent / path
    try:
        with path.open(encoding="utf-8-sig") as source:
            rules = json.load(source)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"custom_rules_file 无法读取有效 JSON：{path}") from error
    if not isinstance(rules, list):
        raise ValueError("custom_rules_file 顶层必须是规则数组")
    return rules


def _canonical(domain):
    return domain.lower().rstrip(".")


def _matchers(rule):
    for field in DOMAIN_FIELDS:
        values = rule.get(field, [])
        if isinstance(values, str):
            values = [values]
        for value in values:
            yield field, _canonical(value)


def _covers(earlier, later):
    field, value = earlier
    later_field, later_value = later
    if field == "domain":
        return later_field == "domain" and value == later_value
    if later_field == "domain":
        return later_value.endswith(value) if value.startswith(".") else (
            later_value == value or later_value.endswith("." + value)
        )
    base, later_base = value.removeprefix("."), later_value.removeprefix(".")
    if base == later_base:
        return not value.startswith(".") or later_value.startswith(".")
    return later_base.endswith("." + base)


def _validate_rules(custom_rules, tags):
    if not isinstance(custom_rules, list):
        raise ValueError("custom_rules 必须是规则数组")
    normalized, seen = [], {}
    for index, rule in enumerate(custom_rules):
        location = f"custom_rules[{index}]"
        if not isinstance(rule, dict):
            raise ValueError(f"{location} 必须是对象")
        if rule.keys() - {*DOMAIN_FIELDS, "outbound"}:
            raise ValueError(f"{location} 仅支持 domain、domain_suffix、outbound 字段")
        outbound = rule.get("outbound")
        if not isinstance(outbound, str) or not outbound.strip():
            raise ValueError(f"{location}.outbound 必须是非空出口标签")
        if outbound not in tags:
            raise ValueError(f"{location}.outbound 在生成配置中不存在，请核对出口标签")
        if not set(DOMAIN_FIELDS).intersection(rule):
            raise ValueError(f"{location} 至少需要 domain 或 domain_suffix")
        for field in DOMAIN_FIELDS:
            if field not in rule:
                continue
            domains = rule[field]
            if not isinstance(domains, list) or not domains or any(
                not isinstance(domain, str) or domain != domain.strip() or not _canonical(domain)
                for domain in domains
            ):
                raise ValueError(f"{location}.{field} 必须是非空域名字符串数组，不能包含首尾空白")
        for matcher in _matchers(rule):
            if matcher in seen and seen[matcher][1] != outbound:
                raise ValueError(f"{location} 与 custom_rules[{seen[matcher][0]}] 的匹配项出口冲突")
            seen.setdefault(matcher, (index, outbound))
        normalized.append({**copy.deepcopy(rule), "action": "route"})
    return normalized


def _is_foundation(rule, tailscale_tags):
    return (
        rule.get("action") in ("sniff", "hijack-dns", "reject")
        or "clash_mode" in rule or "ip_is_private" in rule
        or rule.get("outbound") in tailscale_tags
        or any(_is_foundation(child, tailscale_tags) for child in rule.get("rules", []))
    )


def _warn_overlaps(custom_rules, prefix):
    for index, rule in enumerate(custom_rules):
        matches = list(_matchers(rule))
        for earlier_index, earlier in enumerate(custom_rules[:index]):
            if earlier["outbound"] != rule["outbound"] and any(
                _covers(a, b) for a in _matchers(earlier) for b in matches
            ):
                warnings.warn(
                    f"custom_rules[{index}] 与 custom_rules[{earlier_index}] 存在匹配遮蔽；"
                    "重叠部分采用前面的规则，需要例外时请将细分规则前置",
                    UserWarning, stacklevel=3,
                )
        for template_index, earlier in enumerate(prefix):
            # 只对简单、终止匹配的域名规则做静态判断，不能把条件规则当成无条件覆盖。
            if earlier.keys() - {*DOMAIN_FIELDS, "action", "outbound"}:
                continue
            if earlier.get("action", "route") not in ("route", "reject"):
                continue
            if earlier.get("outbound") == rule["outbound"]:
                continue
            if any(_covers(a, b) or _covers(b, a) for a in _matchers(earlier) for b in matches):
                warnings.warn(
                    f"custom_rules[{index}] 与模板 route.rules[{template_index}] 的域名匹配重叠；"
                    "重叠部分由前置模板规则优先处理",
                    UserWarning, stacklevel=3,
                )


def apply_rules(config, custom_rules):
    """只替换唯一模板标记；不重排模板规则、不修改 DNS 或调用方的规则数组。"""
    tags = {item.get("tag") for item in config.get("outbounds", []) + config.get("endpoints", [])}
    normalized = _validate_rules(custom_rules, tags)
    rules = config.get("route", {}).get("rules", [])
    slots = [i for i, rule in enumerate(rules) if "custom_rules" in rule]
    if not slots and not normalized:
        return
    if len(slots) != 1:
        raise ValueError('custom_rules 需要模板 route.rules 中唯一的 {"custom_rules": true} 标记')
    slot = slots[0]
    if set(rules[slot]) != {"custom_rules"} or rules[slot]["custom_rules"] is not True:
        raise ValueError('custom_rules 标记必须是独立的 {"custom_rules": true} 对象')
    tailscale_tags = {item["tag"] for item in config.get("endpoints", []) if item.get("type") == "tailscale"}
    if any(_is_foundation(rule, tailscale_tags) for rule in rules[slot + 1:]):
        raise ValueError("模板基础规则必须位于 custom_rules 标记之前")
    _warn_overlaps(normalized, rules[:slot])
    rules[slot:slot + 1] = normalized
