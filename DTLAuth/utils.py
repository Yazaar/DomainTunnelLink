import typing, mimetypes
from pathlib import Path

AUTH_CALLBACK_TYPE = typing.Optional[typing.Callable[[str, str, str, str], typing.Awaitable[bool]]]

STATIC_FOLDER = Path(__file__).parent / 'web/public'
TEMPLATE_FOLDER = Path(__file__).parent / 'web/templates'

async def handle_auth_request(ip: str | None, data: dict[str, str], onResourceAuthCallback: AUTH_CALLBACK_TYPE) -> tuple[bool, str]:
    if not onResourceAuthCallback:
        return False, 'Auth not configured'

    if not ip:
        return False, 'Invalid IP'

    if not isinstance(data, dict):
        return False, 'Invalid data'

    resourceType = data.get('resourceType')
    resourceItem = data.get('resourceItem')
    resourceCode = data.get('resourceCode')

    if not isinstance(resourceType, str) or not isinstance(resourceItem, str) or not isinstance(resourceCode, str):
        return False, 'Invalid message'

    resolvedAuth = await onResourceAuthCallback(ip, resourceType, resourceItem, resourceCode)
    if resolvedAuth:
        return True, 'Access provided'
    else:
        return False, 'Access blocked'

def static_resolver(path: str) -> tuple[str, str | bytes | None]:
    if not path.startswith('/public/'):
        raise Exception('File access illegal')

    target = path[8:]
    full_path = STATIC_FOLDER / target

    if (not full_path.is_relative_to(STATIC_FOLDER)) or (not full_path.is_file()):
        raise Exception('File access illegal')

    mime = mimetypes.guess_type(full_path)[0]
    if not mime: mime = 'application/octet-stream'

    read_mode = 'r' if mime.startswith('text/') else 'rb'
    enc_mode = 'utf-8' if read_mode else None

    data = None

    try:
        with open(full_path, read_mode, encoding=enc_mode) as f:
            data = f.read()
    except Exception:
        pass

    return mime, data

