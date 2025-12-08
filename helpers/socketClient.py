import asyncio
from helpers import SocketWrapper

class SocketClient:
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.connection: SocketWrapper | None = None

    @property
    def running(self): return self.connection is not None and bool(self.connection.isOpen)

    async def start(self):
        reader, writer = await asyncio.open_connection(self.host, self.port)
        self.connection = SocketWrapper(reader, writer)

    def stop(self):
        if not self.connection: return
        self.connection.close()
        self.connection = None
