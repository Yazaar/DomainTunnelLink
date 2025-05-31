import asyncio, typing, hashlib, uuid, time, json, base64, datetime
from pathlib import Path
from helpers.socketWrapper import SocketWrapper

ROOT = Path(__file__).parent.parent

MIN_PORT_NUMBER = 1
MAX_PORT_NUMBER = 65535
READ_BUFFER_SIZE = 5125

__task_stack: dict[str, asyncio.Task] = {}

def queue_task(coro: typing.Coroutine):
    taskId = new_uuid()
    def on_done(doneTask: asyncio.Task):
        try: __task_stack.pop(taskId)
        except Exception: pass

        try: doneTask.result()
        except Exception as e:
            print(f"[Queue Task] Unhandled exception in background task: {str(e)}")

    task = asyncio.create_task(coro)
    __task_stack[taskId] = task
    task.add_done_callback(on_done)

def validate_port(port):
    if not isinstance(port, int): raise ValueError(f'Port has to be an int between {MIN_PORT_NUMBER} and {MAX_PORT_NUMBER}')
    if port > MAX_PORT_NUMBER: raise ValueError(f'Port have to be an int of max {MAX_PORT_NUMBER}')
    if port < MIN_PORT_NUMBER: raise ValueError(f'Port have to be an int of min {MIN_PORT_NUMBER}')

def load_argv(sys_argv: list[str]):
    i = 0
    c = len(sys_argv) - 1
    parsed_args = {}
    while i < c:
        argv_item = sys_argv[i]
        if argv_item.startswith('--'):
            parsed_args[argv_item[2:]] = sys_argv[i + 1]
            i += 1
        i += 1
    return parsed_args

async def run_forever():
    while True:
        await asyncio.sleep(10)

def get_file(path: str):
    return ROOT / path

def to_int(data: str | None, default: int | None):
    if (data is None): return default
    try: return int(data)
    except Exception: return default

def find_first(collection: list, compare: typing.Callable[[typing.Any], bool]):
    for i in collection:
        if compare(i):
            return i

def sha256(secret: str, salt: str):
    return hashlib.sha256(f'{secret}{salt}'.encode('utf-8')).hexdigest()

def sha256_match(hexdigest: str, secret: str, salt: str):
    return hexdigest == sha256(secret, salt)

def new_uuid():
    return f'{uuid.uuid4().hex}.{time.time_ns()}'

def seconds_since(ts: datetime.datetime, current_time: datetime.datetime | None = None):
    if current_time is None: current_time = datetime.datetime.now()
    delta = current_time - ts
    return delta.total_seconds()

def serialize(object):
    return base64.b64encode(json.dumps(object).encode('utf-8'))

def deserialize(encoded):
    return json.loads(base64.b64decode(encoded).decode())

def http_response(msg: str):
    utctime = datetime.datetime.now(datetime.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S UTC')
    return f'HTTP/1.1 200 OK\r\nServer: Yazaar-DTL-server\r\nDate: {utctime}\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {len(msg)}\r\nConnection: close\r\n\r\n{msg}'

def get_http_headers(data_bytes: bytes):
    headers: dict[str, str] = {}

    data = data_bytes.decode()
    for line in data.split('\n'):
        header_items = line.split(':', 1)
        if len(header_items) != 2: continue

        header_key = header_items[0].lower().strip()
        header_value = header_items[1].strip()

        if not header_key or not header_value: continue

        headers[header_key] = header_value
    return headers

async def http_identification(connection: SocketWrapper):
    buffer = b''

    raw_headers, match = await connection.readuntil_any([b'\r\n\r\n', b'\n\n'])
    buffer += raw_headers + match

    headers = get_http_headers(raw_headers)
    header_host = headers.get('host')

    if not header_host:
        connection.push_back(buffer)
        return False, None

    connection.push_back(buffer)
    return True, header_host
