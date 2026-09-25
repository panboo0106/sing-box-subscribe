import tool
from urllib.parse import urlparse
from parsers import common

def parse(data):
    server_info = urlparse(data)
    try:
        remark = tool.b64Decode(server_info.netloc+server_info.path).decode().rsplit("/#", 1)
    except UnicodeDecodeError:
        remark = (server_info.netloc).rsplit("/#", 1)
    _netloc = remark[0].rsplit("@", 1)
    node = {
        'tag': common.make_tag(remark[1] if len(remark) > 1 else '', 'http'),
        'type': 'http',
        'server': common.clean_host(_netloc[-1].rsplit(":", 1)[0]),
        'server_port': common.first_port(_netloc[-1].rsplit(":", 1)[1]),
        'tls': {
            'enabled': True,
            'insecure': True
        }
    }
    if remark[0].count("@") == 2:
        node ['username'] = _netloc[0].split(":")[0]
        node ['password'] = _netloc[0].split(":")[1]
    return [node]
