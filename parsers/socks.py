from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = common.netloc_with_path(urlparse(data))
    node = {
        'tag': common.make_tag(server_info.fragment, 'socks'),
        'type': 'socks',
        "version": "5",
        'udp_over_tcp': {}
    }
    netloc = common.maybe_b64decode(server_info.netloc)
    if '@' in netloc:
        _netloc = netloc.split("@")
        node['server'] = common.clean_host(_netloc[1].rsplit(":", 1)[0])
        node['server_port'] = int(_netloc[1].rsplit(":", 1)[1])
        node['username'] = _netloc[0].split(":")[0]
        node['password'] = _netloc[0].split(":")[1]
    elif '@' in server_info.netloc:
        _netloc = server_info.netloc.split("@")
        node['server'] = common.clean_host(_netloc[1].rsplit(":", 1)[0])
        node['server_port'] = int(_netloc[1].rsplit(":", 1)[1])
        node['username'] = netloc.split(":")[0]
        node['password'] = netloc.split(":")[1]
    else:
        node['server'] = common.clean_host(netloc.rsplit(":", 1)[0])
        node['server_port'] = int(netloc.rsplit(":", 1)[1])
    return [node]
