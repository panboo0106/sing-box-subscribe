import re
from urllib.parse import urlparse
from parsers import common
from parsers.common import ParseError

def parse(data):
    server_info = common.netloc_with_path(urlparse(data))
    if '@' not in server_info.netloc:
        raise ParseError('trojan URI 缺少 password@server')
    _netloc = server_info.netloc.rsplit("@", 1)
    netquery = common.parse_query(server_info.query)
    node = {
        'tag': common.make_tag(server_info.fragment, 'trojan'),
        'type': 'trojan',
        'server': common.clean_host(_netloc[1].rsplit(":", 1)[0]),
        'server_port': common.first_port(_netloc[1].rsplit(":", 1)[1]),
        'password': _netloc[0],
        'tls': {
            'enabled': True,
            'insecure': common.insecure_from_query(netquery)
        }
    }
    if netquery.get('alpn'):
        node['tls']['alpn'] = netquery.get('alpn').strip('{}').split(',')
    if netquery.get('sni'):
        node['tls']['server_name'] = netquery.get('sni', '')
    if netquery.get('fp'):
        node['tls']['utls'] = {
            'enabled': True,
            'fingerprint': netquery.get('fp')
        }
    if netquery.get('type'):
        if netquery['type'] == 'h2':
            node['transport'] = {
                'type':'http',
                'host':netquery.get('host', node['server']),
                'path':netquery.get('path', '/')
            }
        if netquery['type'] == 'ws':
            matches = re.search(r'\?ed=(\d+)$', netquery.get('path', '/'))
            if netquery.get('host'):
                node['transport'] = {
                     'type':'ws',
                     'path':netquery.get('path', '/').rsplit("?ed=", 1)[0] if matches else netquery.get('path', '/'),
                     'headers': {
                         'Host': netquery.get('host')
                    }
                }
        elif netquery['type'] == 'grpc':
            node['transport'] = {
                'type':'grpc',
                'service_name':netquery.get('serviceName', '')
            }
    multiplex = common.build_multiplex(netquery)
    if multiplex:
        node['multiplex'] = multiplex
    return [node]
