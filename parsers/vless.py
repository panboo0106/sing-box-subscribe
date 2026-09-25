import re
from urllib.parse import urlparse
from parsers import common
from parsers.common import ParseError

def parse(data):
    server_info = urlparse(data)
    netloc = common.maybe_b64decode(server_info.netloc)
    _netloc = netloc.split("@")
    if len(_netloc) < 2:
        raise ParseError('vless URI 缺少 uuid@server')
    _netloc_parts = _netloc[1].rsplit(":", 1)
    if len(_netloc_parts) < 2 or not _netloc_parts[1].isdigit(): #fuck
        raise ParseError('vless URI 端口非法')
    server = common.clean_host(_netloc_parts[0])
    server_port = int(_netloc_parts[1])
    netquery = common.parse_query(server_info.query)
    if netquery.get('remarks'):
        remarks = netquery['remarks']
    else:
        remarks = server_info.fragment
    node = {
        'tag': common.make_tag(remarks, 'vless'),
        'type': 'vless',
        'server': server,
        'server_port': server_port,
        'uuid': _netloc[0].split(':', 1)[-1],
        'packet_encoding': netquery.get('packetEncoding', 'xudp')
    }
    if netquery.get('flow'):
        node['flow'] = 'xtls-rprx-vision'
    if netquery.get('security', '') not in ['None', 'none', ''] or netquery.get('tls') == '1':
        node['tls'] = {
            'enabled': True,
            'insecure': common.insecure_from_query(netquery),
            'server_name': ''
        }
        node['tls']['server_name'] = netquery.get('sni', '') or netquery.get('peer', '')
        if node['tls']['server_name'] == 'None':
            node['tls']['server_name'] = ''
        if netquery.get('security') == 'reality' or netquery.get('pbk'): #shadowrocket
            node['tls']['reality'] = {
                'enabled': True,
                'public_key': netquery.get('pbk'),
            }
            # 处理 short_id，避免 fuck 'None' 或 null
            sid = netquery.get('sid')
            if isinstance(sid, str) and sid.strip().lower() != "none":
                node['tls']['reality']['short_id'] = netquery['sid']
            node['tls']['utls'] = {
                'enabled': True
            }
            if netquery.get('fp'):
                node['tls']['utls'] = {
                    'enabled': True,
                    'fingerprint': netquery['fp']
                }
    if netquery.get('type'):
        if netquery['type'] == 'http':
            node['transport'] = {
                'type':'http'
            }
        elif netquery['type'] == 'ws':
            matches = re.search(r'\?ed=(\d+)$', netquery.get('path', '/'))
            node['transport'] = {
                'type':'ws',
                "path": netquery.get('path', '/').rsplit("?ed=", 1)[0] if matches else netquery.get('path', '/'),
                "headers": {
                    "Host": '' if netquery.get('host') is None and netquery.get('sni') == 'None' else netquery.get('host', netquery.get('sni', ''))
                }
            }
            if node.get('tls'):
                if node['tls']['server_name'] == '':
                    if node['transport']['headers']['Host']:
                        node['tls']['server_name'] = node['transport']['headers']['Host']
            if matches:
                node['transport']['early_data_header_name'] = 'Sec-WebSocket-Protocol'
                node['transport']['max_early_data'] = int(netquery.get('path', '/').rsplit("?ed=", 1)[1])
        elif netquery['type'] == 'grpc':
            node['transport'] = {
                'type':'grpc',
                'service_name':netquery.get('serviceName', '')
            }
    elif netquery.get('obfs'):  #shadowrocket
        if netquery['obfs'] == 'websocket':
            matches = re.search(r'\?ed=(\d+)$', netquery.get('path', '/'))
            node['transport'] = {
                'type':'ws',
                "path": netquery.get('path', '/').rsplit("?ed=", 1)[0] if matches else netquery.get('path', '/'),
                "headers": {
                    "Host": '' if netquery.get('obfsParam') is None and netquery.get('sni') == 'None' else netquery.get('peer', netquery.get('obfsParam'))
                }
            }
            if node.get('tls'):
                if node['tls']['server_name'] == '':
                    if node['transport']['headers']['Host']:
                        node['tls']['server_name'] = node['transport']['headers']['Host']
            if matches:
                node['transport']['early_data_header_name'] = 'Sec-WebSocket-Protocol'
                node['transport']['max_early_data'] = int(netquery.get('path', '/').rsplit("?ed=", 1)[1])
    multiplex = common.build_multiplex(netquery)
    if multiplex:
        node['multiplex'] = multiplex
    return [node]
