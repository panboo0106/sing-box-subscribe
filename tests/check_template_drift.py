#!/usr/bin/env python3
"""config_template 一致性检查，防止同源模板漂移。

约束（见 config_template/README.md §验证配置）：
1. ios/mixed.json 与 macos/mixed.json 逐字节相同
2. android/tun.json 与 linux/tun.json 仅允许在平台字段上不同
   （tun 的 strict_route/auto_redirect/stack、endpoint 的 state_directory/auth_key）
3. 所有模板的内联 AI 域名列表（DNS 规则与 route 规则、跨文件）完全一致
"""
import copy
import json
import sys
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "config_template"
TEMPLATES = [
    "android/tun.json",
    "ios/mixed.json",
    "linux/tun.json",
    "macos/mixed.json",
    "macos/tun.json",
]


def normalize_platform_fields(cfg):
    cfg = copy.deepcopy(cfg)
    tun = next(i for i in cfg["inbounds"] if i["type"] == "tun")
    for key in ("strict_route", "auto_redirect", "stack"):
        tun.pop(key, None)
    for endpoint in cfg.get("endpoints", []):
        endpoint.pop("state_directory", None)
        endpoint.pop("auth_key", None)
    return cfg


def ai_domain_lists(cfg):
    dns = [r["domain"] for r in cfg["dns"]["rules"] if "domain" in r]
    route = [r["domain"] for r in cfg["route"]["rules"]
             if "domain" in r and r.get("outbound") == "AI"]
    return dns, route


def main():
    errors = []
    raw = {t: (TEMPLATE_DIR / t).read_text() for t in TEMPLATES}
    cfgs = {t: json.loads(raw[t]) for t in TEMPLATES}

    if raw["ios/mixed.json"] != raw["macos/mixed.json"]:
        errors.append("ios/mixed.json 与 macos/mixed.json 不一致（应逐字节相同）")

    if normalize_platform_fields(cfgs["android/tun.json"]) != \
            normalize_platform_fields(cfgs["linux/tun.json"]):
        errors.append("android/tun.json 与 linux/tun.json 在平台字段之外出现差异")

    reference = None
    for name, cfg in cfgs.items():
        dns, route = ai_domain_lists(cfg)
        if len(dns) != 1 or len(route) != 1:
            errors.append(f"{name}: 期望 DNS/route 各恰好 1 条内联 AI domain 规则，"
                          f"实际 dns={len(dns)} route={len(route)}")
            continue
        if dns[0] != route[0]:
            errors.append(f"{name}: DNS 与 route 的内联 AI 域名列表不一致")
        if reference is None:
            reference = dns[0]
        elif dns[0] != reference:
            errors.append(f"{name}: 内联 AI 域名列表与其他模板不一致")

    if errors:
        print("模板漂移检查失败：")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"OK：{len(TEMPLATES)} 个模板一致性检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
