from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = common.netloc_with_path(urlparse(data))
    _netloc = server_info.netloc.rsplit("@", 1)
    netquery = common.parse_query(server_info.query)
    node = {
        'tag': common.make_tag(server_info.fragment, 'tuic'),
        'type': 'tuic',
        'server': common.clean_host(_netloc[1].rsplit(":", 1)[0]),
        'server_port': common.first_port(_netloc[1].rsplit(":", 1)[1]),
        'uuid': _netloc[0].split(":")[0],
        'password': _netloc[0].split(":")[1] if len(_netloc[0].split(":")) > 1 else netquery.get('password', ''),
        'congestion_control': netquery.get('congestion_control', 'bbr'),
        'udp_relay_mode': netquery.get('udp_relay_mode'),
        'zero_rtt_handshake': False,
        'heartbeat': '10s',
        'tls': {
            'enabled': True,
            'alpn': (netquery.get('alpn') or "h3").strip('{}').split(','),
            'insecure': common.insecure_from_query(netquery)
        }
    }
    if netquery.get('disable_sni') and netquery['disable_sni'] != '1':
        node['tls']['server_name'] = netquery.get('sni', netquery.get('peer', ''))
    if netquery.get('sni') or netquery.get('peer'):
        node['tls']['server_name'] = netquery.get('sni', netquery.get('peer', ''))
    return [node]
