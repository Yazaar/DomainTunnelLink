import asyncio, sys
from socketConnection import SocketConnection, connect_client

class TunnelClient:
    def __init__(self, server_host: str, server_port: int, app_host: str, app_port: int, target_type: str, target: str, auth_key: str):
        self.server_host = server_host
        self.server_port = server_port
        self.app_host = app_host
        self.app_port = app_port
        self.target_type = target_type
        self.target = target
        self.auth_key = auth_key

    async def start(self):
        try: server = await connect_client(self.server_host, self.server_port)
        except ConnectionRefusedError:
            print('Connection issue to the server, closing')
            raise SystemExit

        server.write(f'auth;{self.target_type};{self.target};{self.auth_key};'.encode('utf-8'))
        await server.flush()
        try: data = await server.readuntil(b';')
        except asyncio.exceptions.IncompleteReadError:
            print('Server disconnected you, closing')
            raise SystemExit

        if data == b'0a;':
            print('Requested resource is not open, closing')
            raise SystemExit
        elif data == b'0b;':
            print('Invalid authentication cridentials, closing')
            raise SystemExit
        elif data == b'0c;':
            print('Requested resource occupied, closing')
            raise SystemExit
        elif data == b'1;':
            print('Authentication successful')
        else:
            print('Invalid returned code, closing')
            raise SystemExit

        while True:
            data = await server.readuntil(b';')
            if data == b'ping;':
                server.write(b'pong;')
                await server.flush()
            elif data == b'request;':
                request_key = await server.readuntil(b';')
                await self.__new_request(request_key[:-1])

    async def __new_request(self, request_key: bytes):
        server = await connect_client(self.server_host, self.server_port)
        server.write(b'bind;' + request_key + b';')
        await server.flush()

        application = await connect_client(self.app_host, self.app_port)
        loop = asyncio.get_event_loop()
        loop.create_task(self.__passthrough(server, application))
        loop.create_task(self.__passthrough(application, server))

    async def __passthrough(self, reader: SocketConnection, writer: SocketConnection):
        while True:
            data = await reader.read(2048)
            if not data:
                reader.close()
                writer.close()
                break
            writer.write(data)
            await writer.flush()

async def main():
    connectExample = 'py tunnelClient.py tcp/http localHost localPort serverDomain serverPort/subdomain password'
    argv = sys.argv
    if len(argv) != 7:
        print(f'Invalid arguments: {connectExample}')
        return

    target = argv[1]

    localHost = argv[2]

    try: localPort = int(argv[3])
    except Exception:
        print(f'localPort should be a number: {connectExample}')
        return

    serverDomain = argv[4]

    if target == 'tcp':
        try: serverCon = int(argv[5])
        except Exception:
            print(f'serverPort (since tcp) should be a number: {connectExample}')
            return
    if target == 'http':
        serverCon = argv[5]
    else:
        print(f'Invalid target type, should be tcp or http: {connectExample}')
        return


    password = argv[6]

    tc = TunnelClient(serverDomain, 9000, localHost, localPort, target, serverCon, password)

    await tc.start()

if __name__ == '__main__':
    asyncio.run(main())
