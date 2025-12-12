import logging, os
from helpers import misc
from DTLAuth.utils import AUTH_CALLBACK_TYPE

logger = logging.getLogger(__name__)

async def aiohttp(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    from DTLAuth.aiohttpAuth import start_web
    await start_web(port, onResourceAuthCallback)
    logger.info('Auth aiohttp running')

async def basichttp(port: int, onResourceAuthCallback: AUTH_CALLBACK_TYPE):
    from DTLAuth.basichttp import start_web
    await start_web(port, onResourceAuthCallback)
    logger.info('Auth basichttp running')

PRIORITY = ['aiohttp', 'basic']
PRIORITY_CALLBACKS = {
    'aiohttp': aiohttp,
    'basic': basichttp
}

async def setupDTLAuth(parsed_argv: dict[str, str], on_resource_auth_callback):
    web_port = misc.to_int(parsed_argv.get('webPort'), None) or misc.to_int(os.environ.get('DTL_AUTH_PORT', None), None)
    if web_port is None:
        logger.info('DTL Auth disabled due to no provided port (--webPort arg)')
        return
    
    if web_port < misc.MIN_PORT_NUMBER or web_port > misc.MAX_PORT_NUMBER:
        logger.error(f'DTL Auth invalid port (accepted: {misc.MIN_PORT_NUMBER}-{misc.MAX_PORT_NUMBER})')
        return

    web_clients = parsed_argv.get('webClient', None)
    web_clients = PRIORITY if web_clients is None else [web_clients]

    errs = []
    is_ok = False

    for web_client in web_clients:
        setup_callback = PRIORITY_CALLBACKS.get(web_client, None)
        if setup_callback is None:
            errs.append({'m': web_client, 'e': 'client not found'})
            continue
        try:
            await setup_callback(web_port, on_resource_auth_callback)
            is_ok = True
            break
        except Exception as e:
            errs.append({'m': web_client, 'e': str(e)})

    if not is_ok:
        for i in errs:
            m = i['m']
            e = i['e']
            logger.error(f'DTL Auth {m}: {e}')
