#!/usr/bin/env python3
"""解析器契约测试（经接口 str -> list[dict]，坏输入抛 ParseError）。

契约（见 parsers/common.py 与 docs/plans/2026-09-25-parser-seam-brief.md）：
1. 所有解析器 parse(uri) 返回 list[dict]；ss+shadow-tls 返回 2 个节点
2. 坏输入抛 ParseError（或意外异常），绝不返回 None / 元组 / print
3. 订阅内嵌 dict 字面量绝不 eval（对抗载荷必须不执行）
4. main.parse_content 是坏节点策略单点：跳过坏节点，不重复追加上一节点
"""

import base64
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from parsers import anytls, http as http_parser, hysteria, hysteria2, socks, ss, ssr, trojan, tuic, vless, vmess, wg
from parsers.common import ParseError

failures = []


def b64(text):
    return base64.urlsafe_b64encode(text.encode()).decode()


def check(name, fn):
    try:
        fn()
        print(f"ok   {name}")
    except Exception as e:
        failures.append(f"{name}: {type(e).__name__}: {e}")
        print(f"FAIL {name}: {type(e).__name__}: {e}")


def expect_parse_error(parse_fn, uri):
    try:
        parse_fn(uri)
    except ParseError:
        return
    raise AssertionError(f"应抛 ParseError，实际没有: {uri[:24]}...")


def one(parse_fn, uri):
    """按契约调用并断言返回恰好 1 个 dict 节点。"""
    result = parse_fn(uri)
    assert isinstance(result, list), f"契约要求 list，实际 {type(result).__name__}"
    assert len(result) == 1, f"契约要求 1 个节点，实际 {len(result)}"
    assert isinstance(result[0], dict), f"契约要求 dict 节点，实际 {type(result[0]).__name__}"
    return result[0]


# ---------- 各协议合法 URI ----------

def test_ss_basic():
    uri = f"ss://{b64('aes-256-gcm:mypassword')}@1.2.3.4:8388#SS%20Node"
    node = one(ss.parse, uri)
    assert node["type"] == "shadowsocks"
    assert node["tag"] == "SS Node"
    assert node["method"] == "aes-256-gcm"
    assert node["password"] == "mypassword"
    assert node["server"] == "1.2.3.4"
    assert node["server_port"] == 8388


def test_ss_chacha_method_fix():
    uri = f"ss://{b64('chacha20-poly1305:mypassword')}@1.2.3.4:8388#SS-ChaCha"
    node = one(ss.parse, uri)
    assert node["method"] == "chacha20-ietf-poly1305"


def test_ss_shadowtls_returns_two_nodes():
    tls_json = json.dumps({"version": "3", "host": "example.com", "password": "tlspass", "fp": "chrome"})
    uri = f"ss://{b64('aes-256-gcm:mypassword')}@1.2.3.4:8388?shadow-tls={b64(tls_json)}#ST%20Node"
    result = ss.parse(uri)
    assert isinstance(result, list) and len(result) == 2, "shadow-tls 应返回 [主节点, detour]"
    node, node_tls = result
    assert node["detour"] == node_tls["tag"] == "ST Node_shadowtls"
    assert node_tls["type"] == "shadowtls"
    assert node_tls["version"] == 3
    assert node_tls["password"] == "tlspass"
    assert node_tls["tls"]["server_name"] == "example.com"
    assert node_tls["tls"]["utls"]["fingerprint"] == "chrome"
    assert "server" not in node and "server_port" not in node


def test_ss_v2ray_plugin_json():
    plugin_json = json.dumps({"mode": "websocket", "host": "h.example.com", "path": "/", "tls": True})
    uri = f"ss://{b64('aes-256-gcm:mypassword')}@1.2.3.4:8388?v2ray-plugin={b64(plugin_json)}#V2P"
    node = one(ss.parse, uri)
    assert node["plugin"] == "v2ray-plugin"
    assert "mode=websocket;" in node["plugin_opts"]
    assert "host=h.example.com;" in node["plugin_opts"]
    assert node["plugin_opts"].endswith("tls;")


def test_ss_eval_never_executes():
    marker = "/tmp/sbs_eval_pwned_test"
    if os.path.exists(marker):
        os.remove(marker)
    payload = f"__import__('os').system('touch {marker}')"
    uri = f"ss://{b64('aes-256-gcm:mypassword')}@1.2.3.4:8388?v2ray-plugin={b64(payload)}#Evil"
    expect_parse_error(ss.parse, uri)
    assert not os.path.exists(marker), "eval 被执行了！订阅内容触发了任意代码"


def test_ss_malformed():
    expect_parse_error(ss.parse, "ss://   ")
    expect_parse_error(ss.parse, "ss://not-a-valid-uri-at-all")


def test_ssr():
    content = "9.9.9.9:8388:auth_aes128_md5:aes-256-cfb:tls1.2_ticket_auth:{}/?obfsparam=&protoparam=&remarks={}".format(
        b64("ssrpass"), b64("SSR Node"))
    node = one(ssr.parse, "ssr://" + b64(content))
    assert node["type"] == "shadowsocksr"
    assert node["tag"] == "SSR Node"
    assert node["server"] == "9.9.9.9"
    assert node["server_port"] == 8388
    assert node["password"] == "ssrpass"
    assert node["protocol"] == "auth_aes128_md5"
    assert node["obfs"] == "tls1.2_ticket_auth"


def test_vmess_json():
    item = {"v": "2", "ps": "VM Node", "add": "5.6.7.8", "port": "443", "id": "uid-1", "aid": "0", "net": "tcp", "tls": ""}
    node = one(vmess.parse, "vmess://" + b64(json.dumps(item)))
    assert node["tag"] == "VM Node"
    assert node["server"] == "5.6.7.8"
    assert node["server_port"] == 443
    assert node["uuid"] == "uid-1"
    assert node["security"] == "auto"
    assert node["transport"]["type"] == "http"


def test_vmess_malformed_no_print():
    expect_parse_error(vmess.parse, "vmess://%%%%not-base64%%%%")


def test_trojan_ws():
    uri = "trojan://t-pass@9.9.9.9:443?sni=example.com&allowInsecure=1&type=ws&host=h.example.com&path=%2Fws#Trojan%20Node"
    node = one(trojan.parse, uri)
    assert node["tag"] == "Trojan Node"
    assert node["password"] == "t-pass"
    assert node["server"] == "9.9.9.9"
    assert node["server_port"] == 443
    assert node["tls"]["insecure"] is True
    assert node["tls"]["server_name"] == "example.com"
    assert node["transport"]["type"] == "ws"
    assert node["transport"]["path"] == "/ws"
    assert node["transport"]["headers"]["Host"] == "h.example.com"


def test_trojan_missing_at():
    expect_parse_error(trojan.parse, "trojan://9.9.9.9:443#NoAt")


def test_trojan_multiplex_without_limits():
    # 旧实现此处 KeyError（节点被吞甚至重复追加），现在只写存在的字段
    node = one(trojan.parse, "trojan://p@9.9.9.9:443?protocol=smux#Mux")
    assert node["multiplex"] == {"enabled": True, "protocol": "smux"}


def test_vless_ws_early_data():
    uri = "vless://uuid-2@9.9.9.9:443?security=tls&sni=ex.com&type=ws&path=%2Fws%3Fed%3D2048&host=h.com&allowInsecure=0#VLess%20Node"
    node = one(vless.parse, uri)
    assert node["tag"] == "VLess Node"
    assert node["uuid"] == "uuid-2"
    assert node["tls"]["enabled"] is True
    assert node["tls"]["insecure"] is False
    assert node["tls"]["server_name"] == "ex.com"
    assert node["transport"]["path"] == "/ws"
    assert node["transport"]["max_early_data"] == 2048
    assert node["transport"]["early_data_header_name"] == "Sec-WebSocket-Protocol"


def test_vless_bad_port():
    expect_parse_error(vless.parse, "vless://uuid@9.9.9.9:abc#BadPort")


def test_hysteria2_full():
    uri = "hysteria2://h2pass@9.9.9.9:443,8443-9443?insecure=true&sni=ex.com&upmbps=10&downmbps=50#Hy2%20Node"
    node = one(hysteria2.parse, uri)
    assert node["tag"] == "Hy2 Node"
    assert node["password"] == "h2pass"
    assert node["server"] == "9.9.9.9"
    assert node["server_port"] == 443
    assert node["server_ports"] == ["8443:9443"]
    assert node["up_mbps"] == 10 and node["down_mbps"] == 50
    assert node["tls"]["insecure"] is True
    assert node["tls"]["server_name"] == "ex.com"
    assert node["tls"]["alpn"] == ["h3"]


def test_hysteria2_mport_and_no_sni():
    node = one(hysteria2.parse, "hysteria2://p@1.2.3.4:443?mport=20000-30000#NoSni")
    assert node["server_ports"] == ["20000:30000"]
    assert "server_name" not in node["tls"]
    assert node["tls"]["insecure"] is True


def test_hysteria():
    node = one(hysteria.parse, "hysteria://9.9.9.9:443?auth=h-auth&peer=ex.com&obfs=salamander#Hy1")
    assert node["type"] == "hysteria"
    assert node["auth_str"] == "h-auth"
    assert node["obfs"] == "salamander"
    assert node["tls"]["server_name"] == "ex.com"


def test_tuic():
    node = one(tuic.parse, "tuic://uuid-3:tpass@9.9.9.9:443?congestion_control=bbr&sni=ex.com#Tuic%20Node")
    assert node["tag"] == "Tuic Node"
    assert node["uuid"] == "uuid-3"
    assert node["password"] == "tpass"
    assert node["congestion_control"] == "bbr"
    assert node["tls"]["server_name"] == "ex.com"


def test_wg():
    uri = "wg://priv-key@9.9.9.9:51820?publicKey=pub-key&ip=172.16.0.2/32&reserved=1,2,3&mtu=1420#WG%20Node"
    node = one(wg.parse, uri)
    assert node["tag"] == "WG Node"
    assert node["private_key"] == "priv-key"
    assert node["peers"][0]["public_key"] == "pub-key"
    assert node["peers"][0]["port"] == 51820
    assert node["peers"][0]["reserved"] == [1, 2, 3]
    assert node["address"] == ["172.16.0.2/32"]
    assert node["mtu"] == 1420


def test_wg_missing_ip():
    # 旧实现此处 TypeError；契约要求 ParseError
    expect_parse_error(wg.parse, "wg://priv-key@9.9.9.9:51820?publicKey=pub-key#WG-NoIp")


def test_socks():
    node = one(socks.parse, f"socks://{b64('user:spass@9.9.9.9:1080')}#Socks%20Node")
    assert node["tag"] == "Socks Node"
    assert node["username"] == "user"
    assert node["password"] == "spass"
    assert node["server"] == "9.9.9.9"
    assert node["server_port"] == 1080


def test_http():
    node = one(http_parser.parse, f"http://{b64('9.9.9.9:8080')}#HTTP%20Node")
    assert node["tag"] == "HTTP Node"
    assert node["type"] == "http"
    assert node["server"] == "9.9.9.9"
    assert node["server_port"] == 8080
    assert node["tls"]["enabled"] is True


def test_anytls():
    node = one(anytls.parse, "anytls://apass@9.9.9.9:443?sni=ex.com&fp=chrome&insecure=1#AnyTLS%20Node")
    assert node["tag"] == "AnyTLS Node"
    assert node["password"] == "apass"
    assert node["tls"]["server_name"] == "ex.com"
    assert node["tls"]["utls"]["fingerprint"] == "chrome"
    assert node["tls"]["insecure"] is True


# ---------- main.parse_content：坏节点策略单点 ----------

def test_parse_content_skips_bad_node_without_duplication():
    import main
    main.init_parsers()
    main.providers = {}
    content = "\n".join([
        "trojan://p1@1.1.1.1:443#NodeA",
        "wg://priv-key@9.9.9.9:51820?publicKey=pub-key#WGBad",  # 缺 ip：旧实现抛 TypeError 并重复追加 NodeA
        "trojan://p2@2.2.2.2:443#NodeB",
    ])
    nodes = main.parse_content(content)
    tags = [n["tag"] for n in nodes]
    assert tags == ["NodeA", "NodeB"], f"坏节点应被跳过且不重复追加，实际 {tags}"


def test_parse_content_flattens_shadowtls():
    import main
    main.init_parsers()
    main.providers = {}
    tls_json = json.dumps({"version": "3", "host": "example.com", "password": "tlspass"})
    uri = f"ss://{b64('aes-256-gcm:mypassword')}@1.2.3.4:8388?shadow-tls={b64(tls_json)}#Flat"
    nodes = main.parse_content(uri)
    assert len(nodes) == 2, "shadow-tls 双节点应在 parse_content 出口即为扁平 list"
    assert nodes[0]["detour"] == nodes[1]["tag"]


def main_check():
    tests = [(name, fn) for name, fn in sorted(globals().items()) if name.startswith("test_")]
    for name, fn in tests:
        check(name, fn)
    if failures:
        print(f"\n{len(failures)} 个测试失败：")
        for f in failures:
            print("  - " + f)
        return 1
    print(f"\nOK：{len(tests)} 个解析器契约测试全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main_check())
