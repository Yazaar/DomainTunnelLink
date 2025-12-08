"""Simple HTTP client for testing."""

import asyncio
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 8000):
        self.host = host
        self.port = port
    
    async def get(self, path: str = '/', domain: str | None = None) -> str | None:
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            
            logger.info(f"Connected to {self.host}:{self.port}")
            
            if domain:
                host_header = domain
            else:
                host_header = f"{self.host}:{self.port}"
            
            request = f"""GET {path} HTTP/1.1\r
Host: {host_header}\r
Connection: close\r
\r
"""
            
            logger.info(f"Sending request:\n{request}")
            writer.write(request.encode('utf-8'))
            await writer.drain()
            
            # Read response
            response = b''
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                response += data
            
            response_text = response.decode('utf-8', errors='ignore')
            logger.info(f"Received response:\n{response_text[:500]}...")
            
            writer.close()
            await writer.wait_closed()
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error: {e}")
            return None
    
    async def post(self, path: str = '/', body: str = '', domain: str | None = None) -> str | None:
        try:
            reader, writer = await asyncio.open_connection(self.host, self.port)
            
            logger.info(f"Connected to {self.host}:{self.port}")

            if domain:
                host_header = domain
            else:
                host_header = f"{self.host}:{self.port}"
            
            body_bytes = body.encode('utf-8')
            request = f"""POST {path} HTTP/1.1\r
Host: {host_header}\r
Content-Length: {len(body_bytes)}\r
Connection: close\r
\r
"""
            
            logger.info(f"Sending request:\n{request}")
            writer.write(request.encode('utf-8') + body_bytes)
            await writer.drain()

            response = b''
            while True:
                data = await reader.read(1024)
                if not data:
                    break
                response += data
            
            response_text = response.decode('utf-8', errors='ignore')
            logger.info(f"Received response:\n{response_text[:500]}...")
            
            writer.close()
            await writer.wait_closed()
            
            return response_text
        
        except Exception as e:
            logger.error(f"Error: {e}")
            return None


async def main():
    host = '127.0.0.1'
    port = 8000
    path = '/'
    method = 'GET'
    body = ''
    domain = None
    
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
        elif arg == '--path':
            i += 1
            if i < len(sys.argv):
                path = sys.argv[i]
        elif arg == '--method':
            i += 1
            if i < len(sys.argv):
                method = sys.argv[i].upper()
        elif arg == '--body':
            i += 1
            if i < len(sys.argv):
                body = sys.argv[i]
        elif arg == '--domain':
            i += 1
            if i < len(sys.argv):
                domain = sys.argv[i]
        
        i += 1
    
    client = HttpClient(host, port)
    
    if method == 'GET':
        await client.get(path, domain)
    elif method == 'POST':
        await client.post(path, body, domain)
    else:
        logger.error(f"Unsupported method: {method}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
