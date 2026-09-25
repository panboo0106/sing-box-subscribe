import re
from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = common.netloc_with_path(urlparse(data))
    netquery = common.parse_query(server_info.query)
    ports_match = re.search(r',(\d+-\d+)', server_info.netloc)
    node = {
        'tag': common.make_tag(server_info.fragment, 'hysteria2'),
        'type': 'hysteria2',
        'server': common.clean_host(server_info.netloc.split("@")[-1].rsplit(":", 1)[0]),
        'server_port': common.first_port(server_info.netloc.rsplit(":", 1)[-1]),
        "password": netquery['auth'] if netquery.get('auth') else server_info.netloc.split("@")[0].rsplit(":", 1)[-1],
        'tls': {
            'enabled': True,
            'server_name': netquery.get('sni', netquery.get('peer', '')),
            'insecure': common.insecure_from_query(netquery)
        }
    }
    # Pin bandwidth (Brutal CC) only when the URI explicitly requests it; otherwise
    # leave up/down_mbps unset so sing-box uses adaptive CC, which is far more
    # reliable on lossy variable links (e.g. China Mobile's CMI international path).
    if 'upmbps' in netquery:
        node['up_mbps'] = int(re.search(r'\d+', netquery['upmbps']).group())
    if 'downmbps' in netquery:
        node['down_mbps'] = int(re.search(r'\d+', netquery['downmbps']).group())
    if ports_match:
        node['server_ports'] = [ports_match.group(1).replace('-', ':')]
    elif re.match(r'^\d+-\d+$', netquery.get('mport', '')):
        node['server_ports'] = [netquery['mport'].replace('-', ':')]
    if not node['tls'].get('server_name'):
        del node['tls']['server_name']
        node['tls']['insecure'] = True
    elif node['tls']['server_name'] == 'None':
        del node['tls']['server_name']
    node['tls']['alpn'] = (netquery.get('alpn') or "h3").strip('{}').split(',')
    if netquery.get('obfs', '') not in ['none', '']:
        node['obfs'] = {
            'type': netquery['obfs'],
            'password': netquery['obfs-password'],
        }
    return [node]
