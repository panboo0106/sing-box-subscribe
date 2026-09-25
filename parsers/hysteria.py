from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = urlparse(data)
    netquery = common.parse_query(server_info.query)
    node = {
        'tag': common.make_tag(server_info.fragment, 'hysteria'),
        'type': 'hysteria',
        'server': common.clean_host(server_info.netloc.rsplit(":", 1)[0]),
        'server_port': common.first_port(server_info.netloc.rsplit(":", 1)[1]), #fuck all
        'auth_str': netquery.get('auth', ''),
        'tls': {
            'enabled': True,
            'server_name': netquery.get('sni', netquery.get('peer', '')),
            'insecure': common.insecure_from_query(netquery)
        }
    }
    if netquery.get('alpn'):
        node['tls']['alpn'] = netquery['alpn'].strip('{}').split(',')
    if netquery.get('obfs') and netquery['obfs'] != 'none':
        node['obfs'] = netquery.get('obfs')
    return [node]
