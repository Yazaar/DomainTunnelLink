import json
from pathlib import Path
from aiohttp import web
from DTLAuth.utils import AUTH_CALLBACK_TYPE, handle_auth_request
from helpers import misc

_onResourceAuthCallback = None

STATIC_FOLDER = Path(__file__).parent / 'web/public'
TEMPLATE_FOLDER = Path(__file__).parent / 'web/templates'

app = web.Application()
routes = web.RouteTableDef()

routes.static('/public', STATIC_FOLDER)

@routes.get('/')
async def web_root(request: web.Request):
    with open(TEMPLATE_FOLDER / 'index.html', 'r') as f:
        ROOT_HTML_RESP = f.read()
    return web.Response(text=ROOT_HTML_RESP, content_type='text/html')

@routes.post('/api/auth-resource')
async def api_web_auth_resource(request: web.Request):
    ip = misc.get_ip(dict(request.headers), [request.remote])

    try:
        data = await request.json()
    except Exception:
        return web.Response(text=json.dumps({ 'statusMessage': 'Failed to read data' }), content_type='application/json')

    result = await handle_auth_request(ip, data, _onResourceAuthCallback)
    return web.Response(text=json.dumps({ 'statusMessage': result[1] }), content_type='application/json')

app.add_routes(routes)
runner = web.AppRunner(app)

async def start_web(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    global _onResourceAuthCallback
    _onResourceAuthCallback = onResourceAuthCallback

    await runner.setup()
    site = web.TCPSite(runner=runner, host='0.0.0.0', port=port)
    await site.start()
