import asyncio, typing
from helpers.socketWrapper import SocketWrapper
from helpers import misc

class SocketHost:
    def __init__(self, host: str, port: int, on_client: typing.Callable[[SocketWrapper], typing.Coroutine]) -> None:
        self.host = host
        self.port = port
        self.on_client = on_client
        self.server : asyncio.Server | None = None
        self.running = False

    async def start(self):
        if self.running: return
        self.running = True
        self.server = await asyncio.start_server(self.__on_client, self.host, self.port)

    async def stop(self):
        if self.server:
            self.server.close()
            self.server = None
        self.running = False

    async def __on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        connection = SocketWrapper(reader, writer)
        misc.queue_task(self.on_client(connection))
