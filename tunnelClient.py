import asyncio, sys, datetime
from helpers import misc
from helpers.socketClient import SocketClient

class QuitException(Exception): pass

class TunnelClient:
    def __init__(self, server_host: str, server_port: str, app_host: str, app_port: str, target_type: str, target: str, password: str, auth: str):
        self.server_host = server_host
        self.app_host = app_host
        self.target_type = target_type
        self.target = target
        self.password = password
        self.auth = auth

        use_port_target = self.target_type in ['tcp', 'udp']

        if use_port_target:
            self.target = misc.to_int(self.target, None)
            try: misc.validate_port(self.target)
            except Exception as e: raise QuitException(f'Target port error: {str(e)}')

        server_port_int = misc.to_int(server_port, None)
        app_port_int = misc.to_int(app_port, None)

        if server_port_int == None: raise QuitException('Server port have to be an int')
        if app_port_int == None: raise QuitException('App port have to be an int')

        self.server_port = server_port_int
        self.app_port = app_port_int

        try: misc.validate_port(self.server_port)
        except Exception as e: raise QuitException(f'Server port error: {str(e)}')
        try: misc.validate_port(self.app_port)
        except Exception as e: raise QuitException(f'App port error: {str(e)}')

        self.client = SocketClient(self.server_host, self.server_port)

        self.last_data = datetime.datetime.now()

        self.watchdog: asyncio.Task | None = None

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
            resp = await self.client.connection.read_until(b';')

        if not resp:
            raise QuitException('Failed to authenticate')

        respData = misc.deserialize(resp)
        if not isinstance(respData, dict) or not 'code' in respData or not 'message' in respData:
            return
        
        respCode = respData.get('code')
        respMsg = respData.get('message')

        print('[TCP Client]', respMsg)

        if respCode != 'OK':
            raise QuitException(f'Connection failed: {respMsg} ({respCode})')

        await self.__listen()

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
        dataType = data.get('type')
        if dataType == 'ping':
            if self.client.connection: self.client.connection.write(misc.serialize({'type': 'pong'}) + b';')
            return

        identifier = data.get('identifier')
        command = data.get('command')

        if isinstance(identifier, str) and isinstance(dataType, str) and command == 'new_request':
            misc.queue_task(self.__connect_new_client(identifier))

    async def __connect_new_client(self, identifier: str):
        server = SocketClient(self.server_host, self.server_port)
        application = SocketClient(self.app_host, self.app_port)
        
        await asyncio.gather(server.start(), application.start())

        payload = {
            'type': self.target_type,
            'resource': self.target,
            'command': 'bind',
            'identifier': identifier
        }

        if not server.connection: raise Exception('Connection not opened')

        server.connection.write(misc.serialize(payload) + b';')

        await asyncio.gather(
            self.__passthrough(server, application),
            self.__passthrough(application, server)
        )

    async def __passthrough(self, reader: SocketClient, writer: SocketClient):
        rd = reader.connection
        wr = writer.connection
        if not rd or not wr: return

        while True:
            data = await rd.read_size(5125)
            if not data:
                if reader.connection: reader.connection.close()
                if writer.connection: writer.connection.close()
                break
            try:
                if not writer.connection: raise Exception('Writer has no connection')
                wr.write(data)
            except Exception:
                if reader.connection: reader.connection.close()
                if writer.connection: writer.connection.close()
                break

    async def __watchdog(self):
        TIMEOUT_TIME = 60
        while True:
            seconds_since = misc.seconds_since(self.last_data)
            if seconds_since > TIMEOUT_TIME:
                try:
                    print(f'[TCP Client] Restarting due stale connection for {seconds_since}s')
                    await self.start()
                except Exception:
                    pass
            
            sleep_duration = TIMEOUT_TIME - seconds_since
            if sleep_duration <= 0:
                sleep_duration = TIMEOUT_TIME * 0.5
            sleep_duration += 1
            await asyncio.sleep(sleep_duration)

    def __registerDataTime(self):
        self.last_data = datetime.datetime.now()

async def main():
    loaded_argv = misc.load_argv(sys.argv)

    if 'help' in loaded_argv or len(loaded_argv.keys()) == 0:
        print('py tunnelClient.py {args}\n--appType: tcp/http/udp\n--appHost: local IP to link\n--appPort: local port to link\n--appAuth: password required for others to authenticate before connecting (optional)\n--serverHost: public server host\n--serverTarget: Public port/host to link\n--serverAuth: password of public target\n--bridgePort: Port the server run the bridge service at (default 9000)')
        return

    app_type = loaded_argv.get('appType', '')
    local_host = loaded_argv.get('appHost', '')
    local_port = loaded_argv.get('appPort', '')
    server_host = loaded_argv.get('serverHost', '')
    bridge_port = loaded_argv.get('bridgePort', '9000')
    server_target = loaded_argv.get('serverTarget', '')
    server_auth = loaded_argv.get('serverAuth', '')
    app_auth = loaded_argv.get('appAuth', '')

    tc = TunnelClient(server_host, bridge_port, local_host, local_port, app_type, server_target, server_auth, app_auth)
    while True:
        try:
            await tc.start()
        except QuitException as e:
            print(f'Tunnel client interrupted, err: {str(e)}')
            break
        except Exception as e:
            print(f'Tunnel client interrupted, err: {str(e)}')

if __name__ == '__main__':
    asyncio.run(main())
