from urllib.parse import urlparse, unquote
from parsers import common
from parsers.common import ParseError

def parse(data):
    server_info = urlparse(data)
    netquery = common.parse_query(server_info.query, keep_plus=True)
    node = {
        'tag': common.make_tag(server_info.fragment, 'wireguard'),
        'type': 'wireguard',
        'private_key': netquery.get('privateKey') or unquote(server_info.netloc.rsplit("@", 1)[0]),
        'peers': []
    }
    peer_info = {
        'address': common.clean_host(server_info.netloc.rsplit("@", 1)[-1].rsplit(":", 1)[0]),
        'port': common.first_port(server_info.netloc.rsplit("@", 1)[-1].rsplit(":", 1)[1]),
        'public_key': netquery.get('publicKey') or netquery.get('publickey'),
        'allowed_ips': [
            "0.0.0.0/0"
        ],
        'persistent_keepalive_interval': 30
    }
    node['peers'].append(peer_info)
    if netquery.get('mtu'):
        node['mtu'] = int(netquery['mtu'])
    if netquery.get('reserved'):
        reserved_value = netquery.get('reserved')
        node['peers'][0]['reserved'] = [int(val) for val in reserved_value.split(",")] if ',' in reserved_value else reserved_value
    ip_value = netquery.get('ip') or netquery.get('address')
    if not ip_value:
        raise ParseError('wg URI 缺少 ip/address 参数')
    if ',' in ip_value:
        ipv4_value, ipv6_value = ip_value.split(",", 1)
        ipv4_value = ipv4_value + "/32" if '/' not in ipv4_value else ipv4_value
        ipv6_value = ipv6_value + "/128" if '/' not in ipv6_value else ipv6_value
        node['address'] = [ipv4_value, ipv6_value]
    else:
        ipv4_value = ip_value + "/32" if '/' not in ip_value else ip_value
        node['address'] = [ipv4_value]
    if netquery.get('presharedKey'):
        node['peers'][0]['pre_shared_key'] = netquery['presharedKey']
    return [node]
