import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TcpEchoServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 6000):
        self.host = host
        self.port = port
        self.server = None
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info('peername')
        logger.info(f"Client connected: {peer}")
        
        try:
            while True:
                data = await reader.read(1024)
                
                if not data:
                    logger.info(f"Client {peer} disconnected")
                    break
                
                message = data.decode('utf-8', errors='ignore')
                logger.info(f"Received from {peer}: {message.strip()}")
                
                response = f"Echo: {message}"
                writer.write(response.encode('utf-8'))
                await writer.drain()
                logger.info(f"Sent to {peer}: {response.strip()}")
        
        except Exception as e:
            logger.error(f"Error handling client {peer}: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        addr = self.server.sockets[0].getsockname()
        logger.info(f"TCP Echo Server started on {addr[0]}:{addr[1]}")
        
        async with self.server:
            await self.server.serve_forever()
    
    def stop(self):
        if self.server:
            self.server.close()

if __name__ == '__main__':
    port = 6000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting TCP Echo Server on port {port}...")
    server = TcpEchoServer(port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()
