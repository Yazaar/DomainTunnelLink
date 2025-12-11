import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TcpClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 6000):
        self.host = host
        self.port = port
        self.reader = None
        self.writer = None
        self.connected = False
    
    async def connect(self) -> bool:
        try:
            if self.connected:
                logger.warning("Already connected")
                return False
            
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.connected = True
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        try:
            if not self.connected:
                logger.warning("Not connected")
                return False
            
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
            
            self.reader = None
            self.writer = None
            self.connected = False
            logger.info("Disconnected")
            return True
        
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False
    
    async def send_message(self, message: str) -> str | None:
        if not self.connected or not self.writer or not self.reader:
            logger.error("Not connected. Use 'open' or 'connect' to connect first.")
            return None
        
        try:
            logger.info(f"Sending: {message}")
            
            self.writer.write(message.encode('utf-8'))
            await self.writer.drain()
            
            data = await self.reader.read(1024)
            response = data.decode('utf-8', errors='ignore')
            
            logger.info(f"Received: {response}")
            
            return response
        
        except Exception as e:
            logger.error(f"Error: {e}")
            self.connected = False
            return None
    
    async def interactive_mode(self):
        logger.info("Interactive mode - Commands:")
        logger.info("  open/connect/1     - Connect to server")
        logger.info("  close/disconnect/0 - Disconnect from server")
        logger.info("  quit/exit          - Exit client")
        logger.info("  Other text         - Send as message")
        logger.info("")
        
        loop = asyncio.get_event_loop()
        
        while True:
            try:
                message = await loop.run_in_executor(None, input, "> ")
                
                if not message:
                    continue
                
                msg_lower = message.lower().strip()

                if msg_lower in ('open', 'connect', '1'):
                    await self.connect()
                
                elif msg_lower in ('close', 'disconnect', '0'):
                    await self.disconnect()
                
                elif msg_lower in ('quit', 'exit'):
                    logger.info("Exiting...")
                    if self.connected:
                        await self.disconnect()
                    break
                
                else:
                    await self.send_message(message)

            except Exception as e:
                logger.error(f"Error: {e}")


async def main():
    host = '127.0.0.1'
    port = 6000
    message = None
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '--host':
            i += 1
            if i < len(sys.argv):
                host = sys.argv[i]
        elif arg == '--port':
            i += 1
            if i < len(sys.argv):
                try:
                    port = int(sys.argv[i])
                except ValueError:
                    logger.error(f"Invalid port: {sys.argv[i]}")
                    sys.exit(1)
        elif arg == '--message':
            i += 1
            if i < len(sys.argv):
                message = sys.argv[i]
        
        i += 1
    
    client = TcpClient(host, port)
    
    if message:
        if await client.connect():
            await client.send_message(message)
            await client.disconnect()
    else:
        await client.interactive_mode()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
