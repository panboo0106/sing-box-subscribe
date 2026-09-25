"""协议 URI 解析的共享助手。

统一 parse 契约（main.get_parser 经此调度，进程内唯一消费方）：
    parse(data: str) -> list[dict]
    通常 1 个节点；ss 带 shadow-tls 插件时返回 2 个（主节点 + detour）。
    坏输入抛 ParseError；不返回 None、不 print、不返回元组。
    意外异常也会被 main.parse_content 单点捕获跳过，但解析器不应依赖这一点。

注意：ParseError 消息不得回显 URI 内容——节点 URI 含密码等敏感信息，
异常消息可能进入部署环境日志。
"""
import ast
import json
import re
import tool
from urllib.parse import parse_qs, unquote


class ParseError(ValueError):
    """输入是该协议的 URI 但内容非法；由 main.parse_content 单点跳过。"""


def strip_scheme(data):
    """去掉 'proto://' 前缀；缺失或无内容时抛 ParseError。"""
    _, sep, rest = data.partition('://')
    if not sep:
        raise ParseError('URI 缺少 :// 协议前缀')
    if not rest.strip():
        raise ParseError('URI 协议前缀后无内容')
    return rest


def parse_query(query, keep_plus=False):
    """parse_qs 结果展平为单值 dict。
    keep_plus 把空格还原为 '+'：parse_qs 会把 '+' 解码成空格，而 wg 的密钥需要保留。"""
    flat = {}
    for k, v in parse_qs(query).items():
        value = v if len(v) > 1 else v[0]
        if keep_plus:
            value = [x.replace(' ', '+') for x in value] if isinstance(value, list) else value.replace(' ', '+')
        flat[k] = value
    return flat


def clean_host(host):
    """去掉 IPv6 字面量的方括号。"""
    return re.sub(r'\[|\]', '', host)


def netloc_with_path(server_info):
    """把 path 并回 netloc：部分上游 URI 的 host:port 写法不规范，
    urlparse 会把 host:port 一段落进 path。"""
    if server_info.path:
        return server_info._replace(netloc=server_info.netloc + server_info.path, path='')
    return server_info


def first_port(port_field):
    """从 '443' / '443,8443-9443' / '443/path' 等形态取第一个端口。"""
    m = re.search(r'\d+', port_field)
    if not m:
        raise ParseError('URI 中未找到端口')
    return int(m.group())


_TRUTHY = ('1', 'true', 'yes', 'on')
_INSECURE_KEYS = ('insecure', 'allowInsecure', 'allow_insecure', 'allow-insecure')


def is_truthy(value):
    return isinstance(value, str) and value.strip().lower() in _TRUTHY


def insecure_from_query(netquery):
    """统一 insecure 判断：接受常见拼写与真值写法（行为变化见任务简报）。"""
    return any(is_truthy(netquery.get(k)) for k in _INSECURE_KEYS)


def make_tag(name, proto):
    """tag 优先用 URI 备注（URL 解码），缺失时生成随机名。"""
    name = unquote(name) if name else ''
    return name or tool.genName() + '_' + proto


def build_multiplex(params):
    """smux/yamux/h2mux 复用块；params 可以是 URI query 或 vmess JSON 字段。
    只写存在的字段，缺失的限制交给 sing-box 默认值（修复旧实现 KeyError 吞节点）。"""
    protocol = params.get('protocol')
    if protocol not in ('smux', 'yamux', 'h2mux'):
        return None
    multiplex = {
        'enabled': True,
        'protocol': protocol
    }
    max_streams = params.get('max-streams') or params.get('max_streams')
    if max_streams:
        multiplex['max_streams'] = int(max_streams)
    else:
        max_connections = params.get('max-connections') or params.get('max_connections')
        min_streams = params.get('min-streams') or params.get('min_streams')
        if max_connections:
            multiplex['max_connections'] = int(max_connections)
        if min_streams:
            multiplex['min_streams'] = int(min_streams)
    padding = params.get('padding')
    if padding == 'True' or padding is True:
        multiplex['padding'] = True
    return multiplex


def loads_lenient(text):
    """安全解析订阅内嵌的 dict 字面量：JSON 优先，Python 字面量回退，绝不 eval。
    JSON 的 true 解析为 True，下游 == 1 判断依然成立（True == 1）。"""
    try:
        result = json.loads(text)
    except ValueError:
        normalized = text.replace('true', 'True').replace('false', 'False').replace('null', 'None')
        try:
            result = ast.literal_eval(normalized)
        except (ValueError, SyntaxError):
            raise ParseError('不是合法的 dict 字面量')
    if not isinstance(result, dict):
        raise ParseError('期望 dict 字面量，实际是 ' + type(result).__name__)
    return result


def maybe_b64decode(text):
    """能按 base64 解码就解码，否则原样返回。"""
    try:
        return tool.b64Decode(text).decode('utf-8')
    except Exception:
        return text
