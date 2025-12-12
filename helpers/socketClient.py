import asyncio
from helpers import SocketWrapper
import ssl

class SocketClient:
    def __init__(self, host: str, port: int, ssl_client=False, ssl_disable_verify=False) -> None:
        self.host = host
        self.port = port
        self.connection: SocketWrapper | None = None

        self.__ssl_context = ssl.create_default_context() if ssl_client else None

        if self.__ssl_context and ssl_disable_verify:
            self.__ssl_context.check_hostname = False
            self.__ssl_context.verify_mode = ssl.CERT_NONE

    @property
    def running(self): return self.connection is not None and bool(self.connection.isOpen)

    async def start(self):
        reader, writer = await asyncio.open_connection(self.host, self.port, ssl=self.__ssl_context)
        self.connection = SocketWrapper(reader, writer)

    def stop(self):
        if not self.connection: return
        self.connection.close()
        self.connection = None
