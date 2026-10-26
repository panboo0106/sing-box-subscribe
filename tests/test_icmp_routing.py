#!/usr/bin/env python3
"""验证生成配置中的 ICMP 直连及自动 DNS 路由。"""

import unittest

from test_custom_rules import TEMPLATES, generate, template


class IcmpRoutingTests(unittest.TestCase):
    def test_tun_routes_icmp_direct_before_mode_overrides(self):
        for path in TEMPLATES:
            if path.name != "tun.json":
                continue
            with self.subTest(template=path):
                rules = generate(template(path), {})["route"]["rules"]
                icmp = {"network": "icmp", "action": "route", "outbound": "direct"}
                self.assertIn(icmp, rules)
                position = rules.index(icmp)
                self.assertLess(next(i for i, r in enumerate(rules) if r.get("action") == "hijack-dns"), position)
                self.assertLess(position, next(i for i, r in enumerate(rules) if "clash_mode" in r))

    def test_auto_dns_omits_icmp_and_preserves_tcp_udp(self):
        config = template()
        config["dns"]["rules"] = []
        config["route"]["rules"] = [
            {"network": network, "domain": ["example.com"], "outbound": "direct"}
            for network in ("icmp", "tcp", "udp")
        ]
        result = generate(config, {"auto_set_outbounds_dns": {"proxy": "remote", "direct": "local"}})
        self.assertEqual(result["dns"]["rules"], [
            {"network": "tcp", "domain": ["example.com"], "server": "local"},
            {"network": "udp", "domain": ["example.com"], "server": "local"},
        ])

    def test_auto_dns_preserves_logical_icmp_conditions(self):
        for mode in ("and", "or"):
            for invert in (False, True):
                with self.subTest(mode=mode, invert=invert):
                    config = template()
                    config["dns"]["rules"] = []
                    conditions = [{"network": "icmp", "invert": invert}, {"domain": ["example.com"]}]
                    config["route"]["rules"] = [{
                        "type": "logical", "mode": mode, "outbound": "direct", "rules": conditions,
                    }]
                    result = generate(config, {"auto_set_outbounds_dns": {"proxy": "remote", "direct": "local"}})
                    self.assertEqual(result["dns"]["rules"], [{
                        "type": "logical", "mode": mode, "server": "local", "rules": conditions,
                    }])

    def test_auto_dns_preserves_inverted_icmp(self):
        config = template()
        config["dns"]["rules"] = []
        config["route"]["rules"] = [{"network": "icmp", "invert": True, "outbound": "direct"}]
        result = generate(config, {"auto_set_outbounds_dns": {"proxy": "remote", "direct": "local"}})
        self.assertEqual(result["dns"]["rules"], [{"network": "icmp", "invert": True, "server": "local"}])

if __name__ == "__main__":
    unittest.main(verbosity=2)
