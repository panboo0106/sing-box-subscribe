#!/usr/bin/env python3
"""离线验证产品路由配置，经真实生成入口和 CLI 检查输出。"""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import main


TEMPLATES = sorted((ROOT / "config_template").rglob("*.json"))
CUSTOM_RULES = [
    {"domain_suffix": ["example.com", "example-api.com"], "outbound": "🇺🇸美国"},
    {"domain": ["app.example.org"], "outbound": "🇭🇰香港"},
]
NODES = {
    "fixture": [
        {"type": "socks", "tag": "🏠🇺🇸fixture", "server": "127.0.0.1", "server_port": 1080},
        {"type": "socks", "tag": "🏠🇭🇰fixture", "server": "127.0.0.1", "server_port": 1081},
    ],
}


def template(path=None):
    return json.loads((path or ROOT / "config_template/macos/tun.json").read_text())


def generate(config, options, nodes=None):
    providers = {"subscribes": [], **options}
    with patch.object(main, "providers", providers), patch.object(
        main, "args", SimpleNamespace(gh_proxy_index=None), create=True,
    ):
        return main.generate_final_config(copy.deepcopy(config), copy.deepcopy(NODES if nodes is None else nodes))


class CustomRulesTests(unittest.TestCase):
    def test_all_templates_preserve_priority_and_input(self):
        options = {"custom_rules": copy.deepcopy(CUSTOM_RULES)}
        original = copy.deepcopy(options)
        expected = [{**rule, "action": "route"} for rule in CUSTOM_RULES]
        for path in TEMPLATES:
            with self.subTest(template=path.relative_to(ROOT)):
                baseline = generate(template(path), {})
                result = generate(template(path), options)
                rules = result["route"]["rules"]
                anchor = next(i for i, r in enumerate(rules) if r.get("ip_is_private"))
                self.assertEqual(rules[anchor + 1:anchor + 3], expected)
                self.assertEqual(rules[:anchor + 1] + rules[anchor + 3:], baseline["route"]["rules"])
                self.assertEqual(result["dns"], baseline["dns"])
                self.assertEqual(options, original)

    def test_domain_and_suffix_can_be_combined(self):
        rule = {"domain": ["api.example.net"], "domain_suffix": ["example.com"], "outbound": "direct"}
        result = generate(template(), {"custom_rules": [rule]})
        self.assertIn({**rule, "action": "route"}, result["route"]["rules"])

    def test_custom_template_without_private_rule(self):
        config = template()
        prefix = [
            {"action": "sniff"},
            {"protocol": "dns", "action": "hijack-dns"},
            {"domain": ["ads.example.net"], "action": "reject"},
            {"clash_mode": "global", "action": "route", "outbound": "Global"},
        ]
        business = [{"domain_suffix": ["example.com"], "action": "route", "outbound": "AI"}]
        for original in ([], business, prefix + business):
            with self.subTest(rules=original):
                config["route"]["rules"] = copy.deepcopy(original)
                result = generate(config, {"custom_rules": [CUSTOM_RULES[0]]})
                index = len(prefix) if original == prefix + business else 0
                expected = original[:index] + [{**CUSTOM_RULES[0], "action": "route"}] + original[index:]
                self.assertEqual(result["route"]["rules"], expected)

    def test_generated_nodes_groups_and_endpoints_are_valid_targets(self):
        config = template()
        config["endpoints"] = [{"type": "tailscale", "tag": "fixture-ts"}]
        targets = ["🏠🇺🇸fixture", "mygroup", "fixture-ts"]
        options = {
            "custom_rules": [{"domain": ["app.example.net"], "outbound": target} for target in targets],
        }
        result = generate(config, options, {"fixture-mygroup-subgroup": NODES["fixture"]})
        for rule in options["custom_rules"]:
            self.assertIn({**rule, "action": "route"}, result["route"]["rules"])

    def test_invalid_rules_report_the_field(self):
        valid = CUSTOM_RULES[0]
        cases = [
            (None, "custom_rules"),
            ({}, "custom_rules"),
            ("example.com", "custom_rules"),
            ([None], r"custom_rules\[0\]"),
            ([{**valid, "outbound": "missing-egress"}], r"custom_rules\[0\].outbound"),
            ([{**valid, "outbound": ""}], r"custom_rules\[0\].outbound"),
            ([{**valid, "outbound": []}], r"custom_rules\[0\].outbound"),
            ([{"domain": ["example.com"]}], r"custom_rules\[0\].outbound"),
            ([{"outbound": "direct"}], r"custom_rules\[0\]"),
            ([{**valid, "domain_suffix": []}], r"custom_rules\[0\].domain_suffix"),
            ([{**valid, "domain_suffix": "example.com"}], r"custom_rules\[0\].domain_suffix"),
            ([{**valid, "domain_suffix": [""]}], r"custom_rules\[0\].domain_suffix"),
            ([{**valid, "domain_suffix": ["  "]}], r"custom_rules\[0\].domain_suffix"),
            ([{**valid, "domain_suffix": [123]}], r"custom_rules\[0\].domain_suffix"),
            ([{**valid, "domain_sufix": ["typo.net"]}], r"custom_rules\[0\]"),
        ]
        for rules, message in cases:
            with self.subTest(rules=rules):
                with self.assertRaisesRegex(ValueError, message):
                    generate(template(), {"custom_rules": rules})

    def test_omitted_empty_and_only_nodes_are_compatible(self):
        for path in TEMPLATES:
            with self.subTest(template=path.name):
                self.assertEqual(generate(template(path), {}), generate(template(path), {"custom_rules": []}))
        self.assertEqual(
            generate(template(), {"Only-nodes": True, "custom_rules": "ignored"}),
            NODES["fixture"],
        )

    def test_existing_direct_overrides_and_dns_stay_unchanged(self):
        options = {"direct_domain": ["app.example.org"], "direct_ip": ["192.0.2.1/32"]}
        baseline = generate(template(), options)
        result = generate(template(), {**options, "custom_rules": CUSTOM_RULES})
        rules = result["route"]["rules"]
        index = rules.index({**CUSTOM_RULES[1], "action": "route"})
        self.assertTrue(any("app.example.org" in r.get("domain", []) and r.get("outbound") == "direct" for r in rules[:index]))
        self.assertTrue(any("192.0.2.1/32" in r.get("ip_cidr", []) and r.get("outbound") == "direct" for r in rules[:index]))
        self.assertEqual(result["dns"], baseline["dns"])

    def test_custom_template_keeps_direct_overrides_first(self):
        config = template()
        config["route"]["rules"] = [{"domain": ["existing.example.net"], "outbound": "direct"}]
        result = generate(config, {
            "direct_domain": ["example.com"], "direct_ip": ["192.0.2.1/32"],
            "custom_rules": [CUSTOM_RULES[0]],
        })
        self.assertEqual(result["route"]["rules"][-1], {**CUSTOM_RULES[0], "action": "route"})
        self.assertTrue(all(r["outbound"] == "direct" for r in result["route"]["rules"][:-1]))

    def test_auto_dns_does_not_change_with_custom_routes(self):
        options = {"auto_set_outbounds_dns": {"proxy": "remote", "direct": "local"}}
        baseline = generate(template(), options)
        result = generate(template(), {**options, "custom_rules": CUSTOM_RULES})
        self.assertIn({**CUSTOM_RULES[0], "action": "route"}, result["route"]["rules"])
        self.assertEqual(result["dns"], baseline["dns"])

    def test_cli_all_templates_and_rejected_output(self):
        with tempfile.TemporaryDirectory(prefix="sbs-custom-rules-") as directory:
            root = Path(directory)
            providers = root / "providers.json"
            output = root / "config.json"
            options = {
                "subscribes": [], "custom_rules": CUSTOM_RULES,
                "save_config_path": str(output), "auto_backup": False,
            }
            providers.write_text(json.dumps(options))
            command = [sys.executable, str(ROOT / "main.py"), "--providers", str(providers)]
            result = subprocess.run(command + ["--all_templates"], cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            outputs = sorted(root.glob("config_*.json"))
            self.assertEqual(len(outputs), len(TEMPLATES))
            for path in outputs:
                rules = json.loads(path.read_text())["route"]["rules"]
                for rule in CUSTOM_RULES:
                    self.assertEqual(rules.count({**rule, "action": "route"}), 1)
            output.write_text("previous config")
            options["custom_rules"] = [{**CUSTOM_RULES[0], "outbound": "missing-egress"}]
            providers.write_text(json.dumps(options))
            result = subprocess.run(command + ["--template_index", "4"], cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("custom_rules[0].outbound", result.stderr)
            self.assertEqual(output.read_text(), "previous config")


if __name__ == "__main__":
    unittest.main(verbosity=2)
