import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class UdpClientProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.transport = None
        self.response = None
        self.event = asyncio.Event()
    
    def connection_made(self, transport):
        self.transport = transport
    
    def datagram_received(self, data: bytes, addr):
        self.response = data.decode('utf-8', errors='ignore')
        logger.info(f"Received from {addr}: {self.response.strip()}")
        self.event.set()
    
    def error_received(self, exc):
        logger.error(f"Error: {exc}")
        self.event.set()
    
    def connection_lost(self, exc):
        if exc:
            logger.error(f"Connection lost: {exc}")


class UdpClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 5000):
        self.host = host
        self.port = port
        self.transport = None
        self.protocol = None
        self.connected = False

    async def connect(self) -> bool:
        if self.connected:
            logger.warning("Already connected")
            return False
        try:
            loop = asyncio.get_event_loop()
            self.transport, self.protocol = await loop.create_datagram_endpoint(
                UdpClientProtocol,
                remote_addr=(self.host, self.port)
            )
            self.connected = True
            logger.info(f"Connected to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.connected = False
            return False

    async def disconnect(self) -> bool:
        if not self.connected:
            logger.warning("Not connected")
            return False
        try:
            if self.transport:
                self.transport.close()
            self.transport = None
            self.protocol = None
            self.connected = False
            logger.info("Disconnected")
            return True
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
            return False

    async def send_message(self, message: str, timeout: int = 5) -> str | None:
        if not self.connected or not self.transport or not self.protocol:
            logger.error("Not connected. Use 'open' or 'connect' to connect first.")
            return None
        try:
            logger.info(f"Sending: {message}")
            self.protocol.event.clear()
            self.protocol.response = None
            self.transport.sendto(message.encode('utf-8'))
            try:
                await asyncio.wait_for(self.protocol.event.wait(), timeout=timeout)
                response = self.protocol.response
            except asyncio.TimeoutError:
                logger.warning(f"No response received within {timeout} seconds")
                response = None
            return response
        except Exception as e:
            logger.error(f"Error: {e}")
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
    port = 5000
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
    
    client = UdpClient(host, port)

    if message:
        # Single message mode: connect, send, disconnect
        if await client.connect():
            await client.send_message(message)
            await client.disconnect()
    else:
        # Interactive mode: manual connection control
        await client.interactive_mode()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
