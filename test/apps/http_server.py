import asyncio
import logging
import sys
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HttpServer:
    def __init__(self, host: str = '127.0.0.1', port: int = 8000):
        self.host = host
        self.port = port
        self.server = None
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        peer = writer.get_extra_info('peername')
        logger.info(f"Client connected: {peer}")
        
        try:
            request_line = await reader.readline()
            request_text = request_line.decode('utf-8', errors='ignore')
            logger.info(f"Received from {peer}: {request_text.strip()}")
            
            headers = {}
            while True:
                header_line = await reader.readline()
                if header_line == b'\r\n' or header_line == b'\n' or not header_line:
                    break
                header_text = header_line.decode('utf-8', errors='ignore').strip()
                if ':' in header_text:
                    key, value = header_text.split(':', 1)
                    headers[key.strip()] = value.strip()
                logger.info(f"Header: {header_text}")
            
            parts = request_text.split()
            method = parts[0] if len(parts) > 0 else 'GET'
            path = parts[1] if len(parts) > 1 else '/'
            
            response_body = f"""<!DOCTYPE html>
<html>
<head>
    <title>HTTP Server Test</title>
</head>
<body>
    <h1>HTTP Server Response</h1>
    <p>Time: {datetime.now()}</p>
    <p>Method: {method}</p>
    <p>Path: {path}</p>
    <p>From: {peer[0]}:{peer[1]}</p>
    <p>Host: {headers.get('Host', 'Unknown')}</p>
</body>
</html>"""
            
            response = f"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
Content-Length: {len(response_body)}\r
Connection: close\r
\r
{response_body}"""
            
            logger.info(f"Sending response to {peer}")
            writer.write(response.encode('utf-8'))
            await writer.drain()
        
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
        logger.info(f"HTTP Server started on {addr[0]}:{addr[1]}")
        
        async with self.server:
            await self.server.serve_forever()
    
    def stop(self):
        if self.server:
            self.server.close()


if __name__ == '__main__':
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)
    
    logger.info(f"Starting HTTP Server on port {port}...")
    server = HttpServer(port=port)
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop()
