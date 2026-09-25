from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = urlparse(data)
    netquery = common.parse_query(server_info.query)
    netloc = server_info.netloc
    node = {
        'tag': common.make_tag(server_info.fragment, 'anytls'),
        'type': 'anytls',
        'server': common.clean_host(netloc.split("@")[-1].rsplit(":", 1)[0]),
        'server_port': common.first_port(netloc.rsplit(":", 1)[1]), #fuck all
        'password': netquery['auth'] if netquery.get('auth') else netloc.split("@")[0].rsplit(":", 1)[-1],
        'tls': {
            'enabled': True,
            'server_name': netquery.get('sni', netquery.get('peer', '')),
            'insecure': common.insecure_from_query(netquery)
        }
    }
    if netquery.get('idleSessionCheckInterval'):
        node['idle_session_check_interval'] = netquery['idleSessionCheckInterval']+'s'
    if netquery.get('idleSessionTimeout'):
        node['idle_session_timeout'] = netquery['idleSessionTimeout']+'s'
    if netquery.get('minIdleSession'):
        node['min_idle_session'] = int(netquery['minIdleSession'])
    if netquery.get('fp'):
        node['tls']['utls'] = {
            'enabled': True,
            'fingerprint': netquery.get('fp')
        }
    if netquery.get('alpn'):
        node['tls']['alpn'] = netquery['alpn'].strip('{}').split(',')
    return [node]
