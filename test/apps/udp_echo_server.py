import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UdpEchoProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
    
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Server listening on {transport.get_extra_info('sockname')}")
    
    def datagram_received(self, data: bytes, addr):
        if not self.transport: raise Exception('No transport set')

        message = data.decode('utf-8', errors='ignore')
        logger.info(f"Received from {addr}: {message.strip()}")

        response = f"Echo: {message}"
        self.transport.sendto(response.encode('utf-8'), addr)
        logger.info(f"Sent to {addr}: {response.strip()}")
    
    def error_received(self, exc):
        logger.error(f"Error: {exc}")
    
    def connection_lost(self, exc):
        if exc:
            logger.error(f"Connection lost: {exc}")


class UdpEchoServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.host = host
        self.port = port
        self.transport = None
        self.protocol = None
    
    async def start(self):
        loop = asyncio.get_event_loop()
        
        transport, protocol = await loop.create_datagram_endpoint(
            UdpEchoProtocol,
            local_addr=(self.host, self.port)
        )
        
        self.transport = transport
        self.protocol = protocol
        
        logger.info(f"UDP Echo Server started on {self.host}:{self.port}")
        
        try:
            while True:
                await asyncio.sleep(1)
        finally:
            transport.close()

if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting UDP Echo Server on port {port}...")
    server = UdpEchoServer(port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
