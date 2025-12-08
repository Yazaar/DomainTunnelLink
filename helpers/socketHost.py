import asyncio, typing, logging
from abc import ABC, abstractmethod
from helpers import SocketWrapper, misc

logger = logging.getLogger(__name__)

AddrType = tuple[str | typing.Any, int]

class SocketHost(ABC):
    @abstractmethod
    async def start(self):
        pass
    
    @abstractmethod
    async def stop(self):
        pass
    
    @abstractmethod
    async def send(self, addr: tuple[str | typing.Any, int], data: bytes):
        pass

def create_host(host: str, port: int, on_client: typing.Callable[[SocketWrapper], typing.Coroutine] | None, on_message: typing.Callable[[bytes, AddrType], typing.Coroutine] | None, protocol: str = 'tcp') -> SocketHost:
    proto = (protocol or 'tcp').lower()
    
    if proto == 'udp':
        if not on_message: raise Exception('on_message callback not found')
        return UdpHost(host, port, on_message)
    if proto == 'tcp':
        if not on_client: raise Exception('on_client callback not found')
        return TcpHost(host, port, on_client)

    raise NotImplementedError('Invalid protocol')

################
# TCP PROTOCOL #
################

class TcpHost(SocketHost):
    def __init__(self, host: str, port: int, on_client: typing.Callable[[SocketWrapper], typing.Coroutine]) -> None:
        self.host = host
        self.port = port
        self.on_client = on_client
        self.server: asyncio.Server | None = None
        self.running = False

    async def start(self):
        if self.running:
            return
        self.running = True
        self.server = await asyncio.start_server(self.__on_client, self.host, self.port)
    
    async def stop(self):
        if self.server:
            self.server.close()
            self.server = None
        self.running = False
    
    async def send(self, addr: tuple[str | typing.Any, int], data: bytes):
        logger.critical('TcpHost.send is not implemented please use client.write')
    
    async def __on_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        connection = SocketWrapper(reader, writer)
        misc.queue_task(self.on_client(connection))

################
# UDP PROTOCOL #
################

class UdpHost(SocketHost):
    def __init__(self, host: str, port: int, on_message: typing.Callable[[bytes, AddrType], typing.Coroutine]) -> None:
        self.host = host
        self.port = port
        self.on_message = on_message
        self.transport: asyncio.DatagramTransport | None = None
        self.running = False
    
    async def start(self):
        if self.running:
            return
        self.running = True
        loop = asyncio.get_running_loop()
        
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: DatagramProtocol(self.__on_client_recv),
            local_addr=(self.host, self.port)
        )
    
    async def stop(self):
        if self.transport:
            self.transport.close()
            self.transport = None        
        self.running = False
    
    async def send(self, addr: tuple[str | typing.Any, int], data: bytes):
        if not self.transport:
            logger.warning(f'No transport to transmit data through for {addr[0]}:{addr[1]}')
            return

        self.transport.sendto(data, addr)

    async def __on_client_recv(self, data: bytes, addr: AddrType):
        await self.on_message(data, addr)

class DatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_recv: typing.Callable[[bytes, AddrType], typing.Coroutine]) -> None:
        self.__on_recv = on_recv
    
    def datagram_received(self, data: bytes, addr) -> None:
        misc.queue_task(self.__on_recv(data, addr))
