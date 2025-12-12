import asyncio, sys, datetime, logging, typing
from helpers import misc, SocketClient
from helpers.socketHost import UdpHost, AddrType

logger = logging.getLogger(__name__)

class QuitException(Exception): pass

WATCHDOG_TIMEOUT = 60
WATCHDOG_SLEEP_FACTOR = 0.5

class UDPSession:
    def __init__(self, host: str, port: int, on_message: typing.Callable[[bytes, AddrType, 'UDPSession'], typing.Coroutine]):
        self.host = host
        self.port = port
        self.internal_host = '0.0.0.0'
        self.internal_port = 0
        self.on_message = on_message
        self.host_obj: UdpHost | None = None
        self.running = False

    async def open(self):
        if self.running:
            return

        try:
            self.host_obj = UdpHost(self.internal_host, self.internal_port, self.__on_message)
            await self.host_obj.start()
        except OSError:
            self.host_obj = UdpHost(self.internal_host, 0, self.__on_message)
            await self.host_obj.start()

        if self.host_obj.transport:
            self.internal_port = int(self.host_obj.transport.get_extra_info("sockname")[1])

        self.running = True

    async def close(self):
        if not self.running:
            return
        if self.host_obj:
            await self.host_obj.stop()
            self.host_obj = None
        self.running = False

    async def send(self, addr: AddrType, data: bytes):
        if not self.running or not self.host_obj:
            logger.warning("UDP is not open, message ignored")
            return

        await self.host_obj.send(addr, data)
    
    async def __on_message(self, payload: bytes, addr: AddrType):
        await self.on_message(payload, addr, self)

class UDPSessions:
    def __init__(self, on_message: typing.Callable[[bytes, AddrType, UDPSession], typing.Coroutine]):
        self.on_message = on_message
        self.closed: dict[str, UDPSession] = {}
        self.staged: dict[str, UDPSession] = {}
        self.current: dict[str, UDPSession] = {}

        misc.queue_task(self.__cleanup_task())

    async def get(self, ip: str, port: int):
        sender = f'{ip}:{port}'

        current = self.current.get(sender, None)
        if current: return current

        staged = self.staged.get(sender, None)
        if staged:
            self.current[sender] = staged
            self.staged.pop(sender)
            return staged

        closed = self.closed.get(sender, None)
        if closed:
            self.current[sender] = closed
            self.closed.pop(sender)
            await closed.open()
            return closed
        
        created = UDPSession(ip, port, self.on_message)
        await created.open()

        self.current[sender] = created
        return created

    async def __cleanup_task(self):
        while True:
            await asyncio.sleep(60 * 3)
            await self.__handle_cleanup()

    async def __handle_cleanup(self):
        _, self.closed, self.staged, self.current = self.closed, self.staged, self.current, {}

        tasks = []
        for key in self.closed:
            value = self.closed[key]
            tasks.append(value.close())
        
        await asyncio.gather(*tasks)


class TunnelClient:
    def __init__(
            self,
            server_host: str, server_port: str, server_ssl: bool, server_ssl_unsafe: bool,
            app_host: str, app_port: str, app_ssl: bool, app_ssl_unsafe: bool,
            target_type: str, target: str, password: str, auth: str, pool_count: str):
        self.server_host = server_host
        self.app_host = app_host
        self.target_type = target_type.lower()
        self.target = target
        self.password = password
        self.auth = auth

        self.server_ssl = server_ssl
        self.server_ssl_unsafe = server_ssl_unsafe
        self.app_ssl = app_ssl
        self.app_ssl_unsafe = app_ssl_unsafe

        use_port_target = self.target_type in ['tcp', 'udp']

        if use_port_target:
            self.target = misc.to_int(self.target, None)
            try: misc.validate_port(self.target)
            except Exception as e: raise QuitException(f'Target port error: {str(e)}')

        server_port_int = misc.to_int(server_port, None)
        app_port_int = misc.to_int(app_port, None)
        self.pool_count = misc.to_int(pool_count, None) or 1

        if server_port_int is None: raise QuitException('Server port have to be an int')
        if app_port_int is None: raise QuitException('App port have to be an int')

        if self.target_type == 'udp' and self.pool_count < 1:
            raise QuitException('UDP protocol require at least 1 UDP pool connection')

        self.server_port = server_port_int
        self.app_port = app_port_int

        try: misc.validate_port(self.server_port)
        except Exception as e: raise QuitException(f'Server port error: {str(e)}')
        try: misc.validate_port(self.app_port)
        except Exception as e: raise QuitException(f'App port error: {str(e)}')

        self.client = SocketClient(self.server_host, self.server_port, ssl_client=server_ssl, ssl_disable_verify=self.server_ssl_unsafe)
        self.pools: list[SocketClient] = []
        self.pool_index = -1

        self.last_data = datetime.datetime.now()

        self.watchdog: asyncio.Task | None = None

        self.udp_sessions = UDPSessions(self.__handle_session_message)

    async def start(self):
        if self.client.running:
            self.client.stop()
        await self.client.start()

        if self.watchdog is None:
            self.watchdog = asyncio.create_task(self.__watchdog())

        self.__registerDataTime()
        payload = {
            'type': self.target_type,
            'resource': self.target,
            'secret': self.password,
            'command': 'authenticate'
        }

        if self.password:
            payload['auth'] = self.auth

        serializedPayload = misc.serialize(payload) + b';'

        resp = None
        if self.client.connection:
            self.client.connection.write(serializedPayload)
            await self.client.connection.flush()
            resp = await self.client.connection.read_until(b';')

        if not resp:
            raise QuitException('Failed to authenticate')

        respData = misc.deserialize(resp)
        if not isinstance(respData, dict) or not 'code' in respData or not 'message' in respData:
            return
        
        respCode = respData.get('code')
        respMsg = respData.get('message')

        logger.info(respMsg)

        if respCode != 'OK':
            raise QuitException(f'Connection failed: {respMsg} ({respCode})')
        
        if self.client.connection and self.target_type == 'udp':
            await self.__send_add_pool_command()

        await self.__listen()
    
    async def __send_add_pool_command(self):
        if not self.client.connection:
            logger.warning('Client connection not started')
            return
        self.client.connection.write(misc.serialize({ 'command': 'add_pool' }) + b';')
        await self.client.connection.flush()

    async def __listen(self):
        con = self.client.connection
        if not con: return

        while True:
            resp = await con.read_until(b';')
            if not resp:
                return
            data = misc.deserialize(resp)
            
            if isinstance(data, dict):
                self.__registerDataTime()
                await self.__handle_listen_payload(data)

    async def __handle_listen_payload(self, data: dict):
        command_type = data.get('type')
        if command_type == 'ping':
            if self.client.connection:
                self.client.connection.write(misc.serialize({'type': 'pong'}) + b';')
                await self.client.connection.flush()
            return

        identifier = data.get('identifier')
        command = data.get('command')

        if isinstance(identifier, str):
            if command == 'new_request': misc.queue_task(self.__connect_new_client(identifier))
            elif command == 'new_pool': misc.queue_task(self.__connect_new_pool(identifier))

    async def __connect_new_client(self, identifier: str):
        server = SocketClient(self.server_host, self.server_port, ssl_client=self.server_ssl, ssl_disable_verify=self.server_ssl_unsafe)
        application = SocketClient(self.app_host, self.app_port, ssl_client=self.app_ssl, ssl_disable_verify=self.app_ssl_unsafe)
        
        await asyncio.gather(server.start(), application.start())

        if not server.connection: raise Exception('Connection not opened')

        payload = {
            'type': self.target_type,
            'resource': self.target,
            'command': 'bind',
            'identifier': identifier
        }
        server.connection.write(misc.serialize(payload) + b';')
        await server.connection.flush()

        await asyncio.gather(
            self.__passthrough(server, application),
            self.__passthrough(application, server)
        )

    async def __connect_new_pool(self, identifier: str):
        if len(self.pools) + 2 < self.pool_count:
            await self.__send_add_pool_command()

        server = SocketClient(self.server_host, self.server_port, self.server_ssl, self.server_ssl_unsafe)
        await server.start()

        if not server.connection: raise Exception('Connection not opened')

        self.pools.append(server)

        payload = {
            'type': self.target_type,
            'resource': self.target,
            'command': 'bind',
            'identifier': identifier
        }
        server.connection.write(misc.serialize(payload) + b';')
        await server.connection.flush()

        await self.__pool_passthrough(server)

    def __get_pool(self):
        count = len(self.pools)
        if count == 0: return None
        self.pool_index = index = (self.pool_index + 1) % count
        return self.pools[index]
    
    async def __pool_passthrough(self, reader: SocketClient):
        rd = reader.connection
        if not rd: return
        try:
            while True:
                data = await rd.read_until(b';')
                if not data:
                    break
                data = misc.deserialize(data)
                payload = bytes.fromhex(data['payload'])
                host = data['source_host']
                port = data['source_port']
                await self.__handle_pool_message(payload, host, port)
        except Exception:
            pass
        finally:
            if reader.connection: reader.connection.close()

    async def __handle_pool_message(self, payload: bytes, host: str, port: int):
        session = await self.udp_sessions.get(host, port)
        await session.send((self.app_host, self.app_port), payload)

    async def __handle_session_message(self, payload: bytes, addr: AddrType, session: UDPSession, retries = 3):
        pool = self.__get_pool()
        if not pool or not pool.connection:
            if retries > 0:
                logger.warning(f'Pool not found to handle message ({retries - 1} retries left)')
                await asyncio.sleep(5)
                await self.__handle_session_message(payload, addr, session, retries - 1)
                return
            logger.error('Pool not found and unable to process message!')
            return
    
        event = misc.serialize({
            'type': 'new_message',
            'source_host': session.host,
            'source_port': session.port,
            'payload': payload.hex()
        }) + b';'

        pool.connection.write(event)

    async def __passthrough(self, reader: SocketClient, writer: SocketClient):
        rd = reader.connection
        wr = writer.connection
        if not rd or not wr: return

        try:
            while True:
                data = await rd.read_size(5125)
                if not data:
                    break
                if not writer.connection:
                    raise Exception('Writer has no connection')
                wr.write(data)
        except Exception:
            pass
        finally:
            if reader.connection: reader.connection.close()
            if writer.connection: writer.connection.close()

    async def __watchdog(self):
        while True:
            seconds_since = misc.seconds_since(self.last_data)
            if seconds_since > WATCHDOG_TIMEOUT:
                try:
                    logger.warning(f'Restarting due stale connection for {seconds_since}s')
                    await self.start()
                except Exception:
                    pass
            
            sleep_duration = WATCHDOG_TIMEOUT - seconds_since
            if sleep_duration <= 0:
                sleep_duration = WATCHDOG_TIMEOUT * WATCHDOG_SLEEP_FACTOR
            sleep_duration += 1
            await asyncio.sleep(sleep_duration)

    def __registerDataTime(self):
        self.last_data = datetime.datetime.now()

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    loaded_argv = misc.load_argv(sys.argv)

    if 'help' in loaded_argv or len(loaded_argv.keys()) == 0:
        print('\n'.join([
            'py tunnelClient.py {args}',
            '--appType: tcp/http/udp',
            '--appHost: local IP to link',
            '--appPort: local port to link',
            '--appSSL: Enable https/ssl for the app (values: 1/0, default 0)',
            '--appSSLUnsafe: Disable ssl verification (values: 1/0, default 0)',
            '--appAuth: password required for others to authenticate before connecting (optional)',
            '--serverHost: public server host',
            '--serverSSL: Enable https/ssl for the server (values: 1/0, default 0)',
            '--serverSSLUnsafe: Disable ssl verification (values: 1/0, default 0)',
            '--serverTarget: Public port/host to link',
            '--serverAuth: password of public target',
            '--bridgePort: Port the server run the bridge service at (default 9000)',
            '--pools: Amount of pools used to handle UDP connections (default 1)'
        ]))
        return

    app_type = loaded_argv.get('appType', '')
    local_host = loaded_argv.get('appHost', '')
    local_port = loaded_argv.get('appPort', '')
    app_ssl = loaded_argv.get('appSSL', '0') == '1'
    app_ssl_unsafe = loaded_argv.get('appSSLUnsafe', '0') == '1'
    server_host = loaded_argv.get('serverHost', '')
    bridge_port = loaded_argv.get('bridgePort', '9000')
    server_target = loaded_argv.get('serverTarget', '')
    server_auth = loaded_argv.get('serverAuth', '')
    server_ssl = loaded_argv.get('serverSSL', '0') == '1'
    server_ssl_unsafe = loaded_argv.get('serverSSLUnsafe', '0') == '1'
    app_auth = loaded_argv.get('appAuth', '')
    pool_count = loaded_argv.get('pools', '')

    tc = TunnelClient(
        server_host, bridge_port, server_ssl, server_ssl_unsafe,
        local_host, local_port, app_ssl, app_ssl_unsafe,
        app_type, server_target, server_auth, app_auth, pool_count
    )
    while True:
        try:
            await tc.start()
        except QuitException as e:
            logger.info(f'Tunnel client closed (quitting), err: {str(e)}')
            break
        except Exception as e:
            logger.warning(f'Tunnel client interrupted (restarting in 10s), err: {str(e)}')
            await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main())
