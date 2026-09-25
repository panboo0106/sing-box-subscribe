import json,re,urllib
import tool
from urllib.parse import parse_qs
from parsers import common
from parsers.common import ParseError

def parse(data):
    raw_param = common.strip_scheme(data)
    param = raw_param
    node = {
        'tag':tool.genName()+'_shadowsocks',
        'type':'shadowsocks',
        'server':None,
        'server_port':0,
        'method':None,
        'password':None
    }
    flag = 0
    if param.find('uot') > -1:
        node["udp_over_tcp"] = {
            'enabled': True,
            'version': 2
        }
    if param.find('#') > -1:
        if param[param.find('#') + 1:] != '':
            remark = urllib.parse.unquote(param[param.find('#') + 1:])
            node['tag'] = remark
        param = param[:param.find('#')]
    elif param.find('?remarks=') > -1:
        if param[param.find('?remarks=') + 9:] != '':
            remark = urllib.parse.unquote(param[param.find('?remarks=') + 9:])
            node['tag'] = remark
        param = param[:param.find('?remarks=')]
    if param.find('plugin=obfs-local') > -1 or param.find('plugin=simple-obfs') > -1:
        if param.find('&', param.find('plugin')) > -1:
            plugin = urllib.parse.unquote(param[param.find('plugin'):param.find('&', param.find('plugin'))])
        else:
            plugin = urllib.parse.unquote(param[param.find('plugin'):])
        param = param[:param.find('?')]
        node['plugin'] = 'obfs-local'
        items = plugin.split(';')
        plugin_dict = {item.split('=')[0]: item.split('=')[1] for item in items if '=' in item}
        result_str = "obfs={};{}".format(
            plugin_dict.get("obfs", ''),
            'obfs-host={};'.format(plugin_dict["obfs-host"]) if plugin_dict.get("obfs-host") else ''
        )
        node['plugin_opts'] = result_str
    elif param.find('v2ray-plugin') > -1:
        if param.find('&', param.find('v2ray-plugin')) > -1:
            raw = param[param.find('v2ray-plugin')+13:param.find('&', param.find('v2ray-plugin'))]
            raw_fallback = param[param.find('v2ray-plugin')+15:param.find('&', param.find('v2ray-plugin'))]
        else:
            raw = param[param.find('v2ray-plugin')+13:]
            raw_fallback = param[param.find('v2ray-plugin')+15:]
        try:
            decoded = tool.b64Decode(raw).decode('utf-8')
        except Exception:
            decoded = None
        if decoded is not None:
            # 旧实现在此处 eval 订阅内容，可执行任意代码；现在解析失败按 ParseError 单点跳过
            plugin = common.loads_lenient(decoded)
        else:
            pairs = [pair.split('=') for pair in urllib.parse.unquote(raw_fallback).split(';') if '=' in pair and pair.count('=') == 1]
            plugin = {key: value for key, value in pairs}
        param = param[:param.find('?')]
        node['plugin'] = 'v2ray-plugin'
        result_str = "mode={};{}{}{}{}{}{}{}".format(
            plugin.get("mode", ''),
            'host={};'.format(plugin["host"]) if plugin.get("host") else '',
            'path={};'.format(plugin["path"]) if plugin.get("path") else '',
            'mux={};'.format(plugin["mux"]) if plugin.get("mux") == 1 else '',
            'headers={};'.format(json.dumps(plugin["headers"])) if plugin.get("headers") else '',
            'fingerprint={};'.format(plugin["fingerprint"]) if plugin.get("fingerprint") else '',
            'skip-cert-verify={};'.format('true') if plugin.get("skip-cert-verify") == 1 else '',
            '{};'.format('tls') if plugin.get("tls") == 1 else '',
        )
        node['plugin_opts'] = result_str
    if raw_param.find('protocol') > -1:
        smux = raw_param[raw_param.find('protocol'):]
        smux_dict = {k: v[0] for k, v in parse_qs(smux.split('#')[0]).items() if v[0]}
        multiplex = common.build_multiplex(smux_dict)
        if multiplex:
            node['multiplex'] = multiplex
    try: #fuck
        param = param.split('?')[0]
        matcher = tool.b64Decode(param) #保留'/'测试能不能解码
    except Exception:
        param = param.split('/')[0].split('?')[0] #不能解码说明'/'不是base64内容
    if param.find('@') > -1:
        matcher = re.match(r'(.*?)@(.*):(.*)', param)
        if not matcher:
            raise ParseError('ss URI 不符合 [userinfo]@server:port')
        param = matcher.group(1)
        node['server'] = matcher.group(2)
        node['server_port'] = matcher.group(3).split('&')[0]
        try:
            decoded = tool.b64Decode(param).decode('utf-8')
        except Exception:
            decoded = None
        matcher = re.match(r'(.*?):(.*)', decoded if decoded is not None else param)
        if not matcher:
            raise ParseError('ss userinfo 缺少 method:password')
        node['method'] = matcher.group(1)
        node['password'] = matcher.group(2)
    else:
        try:
            decoded = tool.b64Decode(param).decode('utf-8')
        except Exception:
            raise ParseError('ss URI 无法按 base64(method:pass@server:port) 解码')
        matcher = re.match(r'(.*?):(.*)@(.*):(.*)', decoded)
        if not matcher:
            raise ParseError('ss URI 不符合 base64(method:pass@server:port)')
        node['method'] = matcher.group(1)
        node['password'] = matcher.group(2)
        node['server'] = matcher.group(3)
        node['server_port'] = matcher.group(4).split('&')[0]
    node['server_port'] = int(re.search(r'\d+', node['server_port']).group())
    if raw_param.find('shadow-tls') > -1:
        flag = 1
        if raw_param.find('&', raw_param.find('shadow-tls')) > -1:
            raw_tls = raw_param[raw_param.find('shadow-tls')+11:raw_param.find('&', raw_param.find('shadow-tls'))].split('#')[0]
        else:
            raw_tls = raw_param[raw_param.find('shadow-tls')+11:].split('#')[0]
        # 同 v2ray-plugin：旧实现 eval，现在安全解析
        plugin = common.loads_lenient(tool.b64Decode(raw_tls).decode('utf-8'))
        node['detour'] = node['tag']+'_shadowtls'
        node_tls = {
            'tag':node['detour'],
            'type':'shadowtls',
            'server':node['server'],
            'server_port':node['server_port'],
            'version':int(plugin.get('version', '1')),
            'password':plugin.get('password', ''),
            'tls':{
                'enabled': True,
                'server_name': plugin.get('host', '')
            }
        }
        if plugin.get('address'):
            node_tls['server'] = plugin['address']
        if plugin.get('port'):
            node_tls['server_port'] = int(plugin['port'])
        if plugin.get('fp'):
            node_tls['tls']['utls']={
                'enabled': True,
                'fingerprint': plugin.get('fp')
            }
        del node['server']
        del node['server_port']
    if node['method'] == 'chacha20-poly1305':
        node['method'] = 'chacha20-ietf-poly1305'
    elif node['method'] == 'xchacha20-poly1305':
        node['method'] = 'xchacha20-ietf-poly1305'
    if flag:
        return [node, node_tls]
    return [node]
