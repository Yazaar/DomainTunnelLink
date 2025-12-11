import asyncio, datetime, uuid, logging, typing
from helpers import SocketWrapper, SocketRegistry, misc
from helpers.socketHost import create_host

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 90
PING_INTERVAL = 15
PING_TIMEOUT = 60
MAX_POOLS = 5

class GenericHost:
    def __init__(self, host_type: str, con: str, sha256hex: str, salt: str) -> None:
        self.host_type = host_type

        self.con = con

        if self.host_type in ['tcp', 'udp']:
            con_int = misc.to_int(self.con, None)
            if con_int is None: raise ValueError(f'Host-type {self.host_type} require target to be of type int')
            self.con = con_int

        self.sha256hex = sha256hex
        self.salt = salt
        self.host = create_host('0.0.0.0', self.con, self.on_client, self.on_message, protocol=self.host_type) if isinstance(self.con, int) and self.host_type in ['tcp', 'udp'] else None
        self.binding: SocketWrapper | None = None
        self.lastPong = datetime.datetime.now()
        self.sessionId: str | None = None
        self.auth = ''

        self.accepted: list[str] = []

        self.pendings: list[SocketWrapper] = []

        self.request_ids: list[str] = []

        self.pool_index = -1
        self.pool: list[SocketWrapper] = []

        self.registry = SocketRegistry()
        self.pool_registry = SocketRegistry(MAX_POOLS * 2)

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
                await connection.flush()
                connection.close()
                return

        if not isVerified:
            connection.write(misc.serialize({'code': 'AUTHENTICATION_ERROR', 'message': f'Invalid password for {self.host_type} {self.con}'}) + b';')
            await connection.flush()
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
        await connection.flush()
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
    
    async def add_pool(self, data: dict, connection: SocketWrapper):
        if len(self.pool) >= MAX_POOLS:
            connection.close()
            return

        identifier = data['identifier']
        client = self.pool_registry.pop(identifier)
        if not client:
            connection.close()
            return
        
        self.pool.append(connection)
        try: await self.__pool_reader(connection)
        except Exception: pass

        try: self.pool.remove(connection)
        except Exception: pass

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
            'identifier': identifier,
            'command': 'new_request'
        }) + b';'

        if not self.binding:
            connection.close()
            return

        self.binding.write(payload)
        await self.binding.flush()

        await asyncio.sleep(REQUEST_TIMEOUT)
        if self.registry.pop(identifier):
            connection.close()

    async def on_message(self, data: bytes, addr: tuple[str | typing.Any, int], retries = 3):
        pool = self.get_pool()
        if not pool:
            logging.warning(f'Failed to get pool ({retries} retries left)')
            await asyncio.sleep(3)
            if retries > 0:
                await self.on_message(data, addr, retries=retries-1)
            return
        
        host, port = addr
        command = misc.serialize({
            'type': 'new_message',
            'source_host': host,
            'source_port': port,
            'payload': data.hex()
        }) + b';'

        pool.write(command)
        await pool.flush()

    def get_pool(self):
        count = len(self.pool)
        if count == 0: return None
        self.pool_index = index = (self.pool_index + 1) % count
        return self.pool[index]

    async def __listen(self):
        currentBinding = self.binding
        if not currentBinding: return
        while True:
            buffer = await currentBinding.read_until(b';')
            if buffer is None or not currentBinding.isOpen or len(buffer) == 0:
                currentBinding.close()
                if self.host: await self.host.stop()
                break
            else:
                self.lastPong = datetime.datetime.now()

            try: await self.__process_listen_command(currentBinding, buffer)
            except Exception: pass

    async def __process_listen_command(self, binding: SocketWrapper, buffer: bytes):
        in_payload = misc.deserialize(buffer)
        command = in_payload['command']
        if command == 'add_pool':
            identifier = self.pool_registry.register(binding)
            payload = misc.serialize({
                'type': self.host_type,
                'identifier': identifier,
                'command': 'new_pool',
                'target': self.con
            }) + b';'
            binding.write(payload)
            await binding.flush()

    async def __ping(self):
        currentBinding = self.binding
        if not currentBinding: return
        self.lastPong = datetime.datetime.now()
        while True:
            if not currentBinding.isOpen:
                currentBinding.close()
                logger.info('Disconnecting: connection closed')
                break

            deltaSec = misc.seconds_since(self.lastPong)
            if deltaSec > PING_TIMEOUT:
                currentBinding.close()
                logger.warning(f'Disconnecting: Timeout ({deltaSec}s)')
                break
            try:
                currentBinding.write(misc.serialize({'type': 'ping'}) + b';')
                await currentBinding.flush()
            except Exception:
                logger.error('Disconnecting: failed to send ping')
                currentBinding.close()
                break
            await asyncio.sleep(PING_INTERVAL)

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
    
    async def __pool_reader(self, connection: SocketWrapper):
        while True:
            try:
                data = await connection.read_until(b';')
                if not data or not connection.isOpen:
                    break
                
                event = misc.deserialize(data)
                event_type = event['type']
                if event_type == 'new_message':
                    source_host = event['source_host']
                    source_port = event['source_port']
                    body = bytes.fromhex(event['payload'])
                    if self.host:
                        await self.host.send((source_host, source_port), body)
            except Exception: break
        connection.close()
