import tool
from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = urlparse(data)
    netloc1 = common.parse_query(server_info.netloc)
    netloc = (tool.b64Decode(server_info.netloc.split('&')[0])).decode()
    if '@' in netloc:
        _netloc = netloc.rsplit("@", 1)
        server_port = _netloc[1]
    else:
       server_port = netloc
    node = {
        'tag': common.make_tag(server_info.fragment, 'http'),
        'type': 'http',
        'server': common.clean_host(server_port.rsplit(":", 1)[0]),
        'server_port': common.first_port(server_port.rsplit(":", 1)[1]),
        'tls': {
            'enabled': True,
            'insecure': True
        }
    }
    if netloc1.get('sni'):
        node['tls']['server_name'] = netloc1['sni']
    if '@' in netloc:
        node['username'] = _netloc[0].split(":")[0]
        node['password'] = _netloc[0].split(":")[1]
    return [node]
