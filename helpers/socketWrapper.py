import asyncio

class SocketWrapper:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.buffer = b''
        self.reader = reader
        self.writer = writer
        self.isOpen = True
        self.ip: str | None = None
        self.port: int | None = None
        client_info = writer.transport.get_extra_info('peername')

        if client_info:
            self.ip = client_info[0]
            self.port = client_info[1]

    async def read_until(self, data: bytes):
        try:
            if data in self.buffer:
                buffer, self.buffer = self.buffer.split(data, 1)
                return buffer

            buffer = await self.reader.readuntil(data)
            suffixCut = len(data) * -1
            buffer = self.buffer + buffer[:suffixCut]
            self.buffer = b''
            return buffer
        except Exception:
            return None

    async def readuntil_any(self, matches: list[bytes]) -> tuple[bytes, bytes]:
        foundMatch = self.in_buffer(matches)

        while not isinstance(foundMatch, bytes):
            self.buffer += await self.reader.read(1024)
            foundMatch = self.in_buffer(matches)

        resp, self.buffer = self.buffer.split(foundMatch, 1)
        return resp, foundMatch

    async def read_size(self, size: int, alwaysRecv: int | None = None):
        try:
            if len(self.buffer) > 0 and alwaysRecv == None:
                buffer = self.buffer
                self.buffer = b''
                return buffer
            
            self.buffer += await self.reader.read(size)
            buffer, self.buffer = self.buffer, b''
            return buffer
        except Exception:
            return None

    def write(self, data: bytes):
        self.writer.write(data)

    async def flush(self):
        await self.writer.drain()

    def close(self):
        self.writer.close()
        self.isOpen = False

    def push_back(self, data: bytes):
        self.buffer = data + self.buffer

    def in_buffer(self, matches : list[bytes], buffer : bytes | None = None):
        if buffer is None: buffer = self.buffer
        for match in matches:
            if match in buffer:
                return match
        return None
