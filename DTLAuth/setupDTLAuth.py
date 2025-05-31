from helpers import misc
from DTLAuth.utils import AUTH_CALLBACK_TYPE

async def aiohttp(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    from DTLAuth.aiohttpAuth import start_web
    await start_web(port, onResourceAuthCallback)
    print('[HTTP Auth: aiohttp] Running')

async def basichttp(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    from DTLAuth.basichttp import start_web
    await start_web(port, onResourceAuthCallback)
    print('[HTTP Auth: basichttp] Running')

PRIORITY = ['aiohttp', 'basic']
PRIORITY_CALLBACKS = {
    'aiohttp': aiohttp,
    'basic': basichttp
}

async def setupDTLAuth(parsed_argv: dict[str, str], onResourceAuthCallback):
    webPort = misc.to_int(parsed_argv.get('webPort'), None)
    if webPort is None:
        print(f'[DTL Auth] disabled due to no provided port (--webPort arg)')
        return
    
    if webPort < misc.MIN_PORT_NUMBER or webPort > misc.MAX_PORT_NUMBER:
        print(f'[DTL Auth] invalid port (accepted: {misc.MIN_PORT_NUMBER}-{misc.MAX_PORT_NUMBER})')
        return

    webClients = parsed_argv.get('webClient', None)
    webClients = PRIORITY if webClients is None else [webClients]

    errs = []
    is_ok = False

    for webClient in webClients:
        setupCallback = PRIORITY_CALLBACKS.get(webClient, None)
        if setupCallback is None:
            errs.append({'m': webClient, 'e': 'client not found'})
            continue
        try:
            await setupCallback(webPort, onResourceAuthCallback)
            is_ok = True
            break
        except Exception as e:
            errs.append({'m': webClient, 'e': str(e)})

    if not is_ok:
        for i in errs:
            m = i['m']
            e = i['e']
            print(f'[DTL Auth {m}] {e}')
