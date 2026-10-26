#!/usr/bin/env python3
"""经生成入口验证共享非中国出口、GitLab 路由和空节点兜底。"""

import contextlib
import io
import unittest

from test_custom_rules import TEMPLATES, generate, template


FORBIDDEN = [
    "🇨🇳中国", "中國", "大陆", "大陸", "北京", "上海", "回国", "回國",
    "China-01", "CN01", "cn-02", "🇭🇰香港", "Hong Kong", "hongkong", "HK01",
    "hk-02", "🇲🇴澳门", "澳門", "Macao", "Macau", "MO01", "mo-02",
]
ALLOWED = ["🏠🇺🇸美国-reality", "🇯🇵日本", "🇸🇬Singapore", "🇹🇼台湾", "🇩🇪Germany"]


def nodes(tags):
    return {"fixture": [
        {"type": "socks", "tag": "fixture-" + tag, "server": "127.0.0.1", "server_port": 1080 + i}
        for i, tag in enumerate(tags)
    ]}


def generated(path, tags):
    with contextlib.redirect_stdout(io.StringIO()):
        return generate(template(path), {}, nodes(tags))


class NonChinaRoutingTests(unittest.TestCase):
    def test_other_products_can_reuse_one_non_china_group(self):
        rules = [
            {"domain_suffix": ["example.net"], "outbound": "NonChina"},
            {"domain": ["api.example.org"], "outbound": "NonChina"},
        ]
        for path in TEMPLATES:
            with self.subTest(template=path):
                with contextlib.redirect_stdout(io.StringIO()):
                    config = generate(template(path), {"custom_rules": rules}, nodes(FORBIDDEN + ALLOWED))
                groups = [o for o in config["outbounds"] if o["tag"] == "NonChina"]
                self.assertEqual(len(groups), 1)
                self.assertEqual(groups[0]["outbounds"], ["fixture-" + tag for tag in ALLOWED] + ["non-china-block"])
                for rule in rules:
                    self.assertIn({**rule, "action": "route"}, config["route"]["rules"])
                self.assertNotIn("GitLab", [o["tag"] for o in config["outbounds"]])

    def test_all_templates_exclude_forbidden_regions(self):
        for path in TEMPLATES:
            with self.subTest(template=path):
                config = generated(path, FORBIDDEN + ALLOWED)
                group = next(o for o in config["outbounds"] if o["tag"] == "NonChina")
                self.assertEqual(group["outbounds"], ["fixture-" + tag for tag in ALLOWED] + ["non-china-block"])
                self.assertEqual(next(o for o in config["outbounds"] if o["tag"] == "non-china-block"),
                                 {"tag": "non-china-block", "type": "block"})

    def test_empty_or_forbidden_only_nodes_never_fall_back_to_direct(self):
        for path in TEMPLATES:
            for tags in ([], FORBIDDEN):
                with self.subTest(template=path, tags=tags):
                    config = generated(path, tags)
                    group = next(o for o in config["outbounds"] if o["tag"] == "NonChina")
                    self.assertEqual(group["outbounds"], ["non-china-block"])

    def test_gitlab_route_and_dns_precede_mode_overrides(self):
        for path in TEMPLATES:
            with self.subTest(template=path):
                config = generated(path, ALLOWED)
                rules = config["route"]["rules"]
                rule = {"domain_suffix": ["gitlab.com"], "action": "route", "outbound": "NonChina"}
                self.assertIn(rule, rules)
                position = rules.index(rule)
                self.assertLess(next(i for i, r in enumerate(rules) if r.get("action") == "hijack-dns"), position)
                self.assertLess(position, next(i for i, r in enumerate(rules) if "clash_mode" in r))
                if path.name == "tun.json":
                    self.assertLess(position, next(i for i, r in enumerate(rules) if r.get("network") == "icmp"))
                dns = config["dns"]
                self.assertEqual(next(s for s in dns["servers"] if s["tag"] == "non-china-dns"),
                                 {"tag": "non-china-dns", "type": "tls", "server": "8.8.8.8", "detour": "NonChina"})
                gitlab_rules = [r for r in dns["rules"] if "gitlab.com" in r.get("domain_suffix", [])]
                expected = [{"domain_suffix": ["gitlab.com"], "action": "route", "server": "non-china-dns"}]
                if path.name == "tun.json":
                    expected.insert(0, {"domain_suffix": ["gitlab.com"], "query_type": ["A", "AAAA"],
                                        "action": "route", "server": "fakeip"})
                self.assertEqual(gitlab_rules, expected)
                mode_position = next(i for i, r in enumerate(dns["rules"]) if "clash_mode" in r)
                self.assertTrue(all(dns["rules"].index(r) < mode_position for r in gitlab_rules))


if __name__ == "__main__":
    unittest.main(verbosity=2)
