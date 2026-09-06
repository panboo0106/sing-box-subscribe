import tool,re
from urllib.parse import urlparse, parse_qs, unquote

def parse(data):
    info = data[:]
    server_info = urlparse(info)
    netquery = dict(
        (k, v if len(v) > 1 else v[0])
        for k, v in parse_qs(server_info.query).items()
    )
    if server_info.path:
      server_info = server_info._replace(netloc=server_info.netloc + server_info.path, path="")
    ports_match = re.search(r',(\d+-\d+)', server_info.netloc)
    node = {
        'tag': unquote(server_info.fragment) or tool.genName()+'_hysteria2',
        'type': 'hysteria2',
        'server': re.sub(r"\[|\]", "", server_info.netloc.split("@")[-1].rsplit(":", 1)[0]),
        'server_port': int(re.search(r'\d+', server_info.netloc.rsplit(":", 1)[-1].split(",")[0]).group()),
        "password": netquery['auth'] if netquery.get('auth') else server_info.netloc.split("@")[0].rsplit(":", 1)[-1],
        'tls': {
            'enabled': True,
            'server_name': netquery.get('sni', netquery.get('peer', '')),
            'insecure': False
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
    if netquery.get('insecure') in ['1', 'true'] or netquery.get('allowInsecure') == '1':
        node['tls']['insecure'] = True
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
    return (node)
