import asyncio, time, secrets

async def create_server(host: str, port: int, on_client_callback, identifier: str):
    async def client_callback(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            await on_client_callback(SocketConnection(reader=reader, writer=writer))
        except Exception:
            pass

    return SocketServer(await asyncio.start_server(client_connected_cb=client_callback, host=host, port=port), identifier)


async def connect_client(host: str, port: int):
    reader, writer = await asyncio.open_connection(host=host, port=port)
    return SocketConnection(reader, writer)


class SocketConnection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self.reader = reader
        self.writer = writer
        self.buffer = b''

    async def readuntil(self, match: bytes) -> bytes:
        try:
            index = self.buffer.index(match)
            resp = self.buffer[:index]
            self.buffer = self.buffer[index + 1:]
            return resp
        except ValueError:
            pass  # invalid index

        self.buffer += await self.reader.readuntil(match)
        resp = self.buffer
        self.buffer = b''
        return resp

    def in_buffer(self, buffer : bytes | None, matches : list[bytes]):
        if buffer is None: buffer = self.buffer
        for match in matches:
            if match in buffer:
                return match

    async def readuntil_any(self, matches: list[bytes]) -> bytes:
        buffer = b''
        foundMatch = self.in_buffer(self.buffer, matches)

        while not isinstance(foundMatch, bytes):
            buffer += await self.read(1024)
            foundMatch = self.in_buffer(buffer, matches)

        resp, rest = buffer.split(foundMatch, 1)
        self.push_back(rest)
        return resp + foundMatch

    async def read(self, size: int) -> bytes:
        if len(self.buffer) > 0:
            resp = self.buffer
            self.buffer = b''
            return resp
        resp = await self.reader.read(size)
        return resp

    def push_back(self, data: bytes):
        self.buffer = data + self.buffer

    def write(self, data: bytes):
        self.writer.write(data)

    async def flush(self): await self.writer.drain()

    def close(self):
        self.writer.close()

class HTTPServer:
    def __init__(self, server: SocketConnection, identifier: str):
        self.identifier = identifier
        self.server = server
        self.__requests: dict[str, SocketConnection] = {}

    def register_request_id(self, sc: SocketConnection):
        new_id = f'{self.identifier}+{int(time.time())}{secrets.token_hex(10)}'
        self.__requests[new_id] = sc
        asyncio.get_event_loop().create_task(self.__unregister_id(new_id, 30))
        return new_id

    def get_request_id(self, requestID : str):
        return self.__requests.pop(requestID, None)

    async def __unregister_id(self, request_id: list, validity_time_s: int):
        await asyncio.sleep(validity_time_s)
        sc = self.get_request_id(request_id)
        if sc is None: return
        sc.close()

    def close(self):
        try: self.server.close()
        except Exception: pass


class SocketServer(HTTPServer):
    def __init__(self, server: asyncio.Server, identifier: str):
        self.identifier = identifier
        self.server = server

    @property
    def is_open(self) -> bool: return self.server.is_serving()

    def close(self):
        try: self.server.close()
        except Exception: pass

    async def join(self):
        await self.server.serve_forever()
