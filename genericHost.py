import asyncio, datetime, uuid
from helpers.socketHost import SocketHost
from helpers.socketWrapper import SocketWrapper
from helpers.socketRegistry import SocketRegistry
from helpers import misc

class GenericHost:
    def __init__(self, host_type: str, con: str, sha256hex: str, salt: str) -> None:
        self.host_type = host_type

        self.con = con

        if self.host_type in ['tcp']:
            con_int = misc.to_int(self.con, None)
            if con_int is None: raise ValueError(f'Host-type {self.host_type} require target to be of type int')
            self.con = con_int

        self.sha256hex = sha256hex
        self.salt = salt
        self.host = SocketHost('0.0.0.0', self.con, self.on_client) if isinstance(self.con, int) and self.host_type in ['tcp'] else None
        self.binding: SocketWrapper | None = None
        self.lastPong = datetime.datetime.now()
        self.sessionId: str | None = None
        self.auth = ''

        self.accepted: list[str] = []

        self.pendings: list[SocketWrapper] = []

        self.request_ids: list[str] = []

        self.registry = SocketRegistry()

    async def auth_request(self, ip: str, resourceCode: str):
        if not self.auth:
            return False
        
        if not self.auth == resourceCode:
            return False
        
        if not ip in self.accepted:
            self.accepted.append(ip)
        return True

    async def bind(self, data: dict, connection: SocketWrapper):
        isOpen = await self.is_open()
        isVerified = await self.verify(data)
        if isOpen:
            if self.binding and self.binding.ip == connection.ip:
                self.binding.close()
            else:
                connection.write(misc.serialize({'code': 'RESOURCE_OCCUPIED', 'message': f'The {self.host_type} {self.con} is occupied by another client'}) + b';')
                connection.close()
                return

        if not isVerified:
            connection.write(misc.serialize({'code': 'AUTHENTICATION_ERROR', 'message': f'Invalid password for {self.host_type} {self.con}'}) + b';')
            connection.close()
            return

        self.sessionId = str(uuid.uuid4())
        self.binding = connection
        self.lastPong = datetime.datetime.now()
        self.auth = data.get('auth', '')
        if not isOpen:
            self.accepted = []

        if self.host: await self.host.start()
        connection.write(misc.serialize({'code': 'OK', 'message': f'Successfully bound to {self.host_type} {self.con}'}) + b';')
        listen = self.__listen()
        ping = self.__ping()
        await asyncio.gather(listen, ping)

    async def new_client(self, data: dict, connection: SocketWrapper):
        identifier = data['identifier']
        client = self.registry.pop(identifier)
        if not client:
            connection.close()
            return

        data_out = self.__write_worker(client, connection)
        data_in = self.__write_worker(connection, client)
        await asyncio.gather(data_out, data_in)

    async def verify(self, data: dict):
        if not misc.sha256_match(self.sha256hex, data['secret'], self.salt):
            return False
        return True

    async def is_open(self):
        return self.binding and self.binding.isOpen

    async def on_client(self, connection: SocketWrapper, *, headers: dict | None = None):
        isOpen = await self.is_open()
        if not isOpen:
            connection.close()
            return
        
        ip = misc.get_ip(headers if headers else {}, [connection.ip])
        
        if self.auth and (not ip or not ip in self.accepted):
            connection.close()
            return

        identifier = self.registry.register(connection)
        payload = misc.serialize({
            'type': self.host_type,
            'identifier': identifier,
            'command': 'new_request',
            'target': self.con
        }) + b';'

        if not self.binding:
            connection.close()
            return

        self.binding.write(payload)

        await asyncio.sleep(90)
        if self.registry.pop(identifier):
            connection.close()

    async def __listen(self):
        currentBinding = self.binding
        if not currentBinding: return
        while True:
            buffer = await currentBinding.read_size(misc.READ_BUFFER_SIZE)
            if buffer is None or not currentBinding.isOpen or len(buffer) == 0:
                currentBinding.close()
                if self.host: await self.host.stop()
                break
            else:
                self.lastPong = datetime.datetime.now()

    async def __ping(self):
        currentBinding = self.binding
        if not currentBinding: return
        self.lastPong = datetime.datetime.now()
        INTERVAL = 15
        TIMEOUT = 60
        while True:
            if not currentBinding.isOpen:
                currentBinding.close()
                print(f'[TCP Host] Disconnecting: connection closed')
                break

            deltaSec = misc.seconds_since(self.lastPong)
            if deltaSec > TIMEOUT:
                currentBinding.close()
                print(f'[TCP Host] Disconnecting: Timeout ({deltaSec}s)')
                break
            try:
                currentBinding.write(misc.serialize({'type': 'ping'}) + b';')
            except Exception:
                print('[TCP Host] Disconnecting: failed to send ping')
                currentBinding.close()
                break
            await asyncio.sleep(INTERVAL)

    async def __write_worker(self, reader: SocketWrapper, writer: SocketWrapper):
        while True:
            try:
                data = await reader.read_size(misc.READ_BUFFER_SIZE)
                if data == None or data == b'' or not reader.isOpen or not writer.isOpen:
                    break
                writer.write(data)
                await writer.flush()
            except Exception: break
        reader.close()
        writer.close()
