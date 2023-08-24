import hashlib, asyncio, datetime, pathlib, re
from socketConnection import SocketConnection, SocketServer, HTTPServer, create_server

class OpenMethod:
    def __init__(self, sha256Hex: str, salt: str):
        self.sha256Hex = sha256Hex
        self.salt = salt.encode('utf-8')

    def match(self, authKey: bytes):
        digest = hashlib.sha256(authKey + self.salt).hexdigest()
        return digest == self.sha256Hex

class OpenTCP(OpenMethod):
    def __init__(self, port: int, sha256Hex: str, salt: str):
        super().__init__(sha256Hex=sha256Hex, salt=salt)
        self.port = port

class OpenWeb(OpenMethod):
    def __init__(self, subdomain: str, sha256Hex: str, salt: str):
        super().__init__(sha256Hex=sha256Hex, salt=salt)
        self.subdomain = subdomain

class TunnelServer:
    def __init__(self, webs: list[tuple[str, str, str]], tcps: list[tuple[int, str, str]]):
        self.__hostsServer : SocketServer = None
        self.__httpServer : SocketServer = None
        self.__httpServers : dict[str, HTTPServer] = {}
        self.__tcpServers : dict[int, SocketServer] = {}
        self.__openTCPs : list[OpenTCP] = self.__parseTCPs(tcps)
        self.__openWebs : list[OpenWeb] = self.__parseWebs(webs)

    async def start(self):
        self.__hostsServer = await create_server('0.0.0.0', 9000, self.__onClient, 'hosts.tcpaccess')
        self.__httpServer = await create_server('0.0.0.0', 8001, self.__onHTTP, 'public.httpaccess')

    def close(self):
        self.__hostsServer.close()
        self.__httpServer.close()
        for i in self.__tcpServers.values():
            i.close()
        self.__tcpServers.clear()

    async def join(self):
        await self.__httpServer.join()

    def __parseWebs(self, webs: list[tuple[str, str, str]]):
        parsed: list[OpenWeb] = []
        for i in webs:
            subdomain = i[0]
            passHash = i[1]
            salt = i[2]
            parsed.append(OpenWeb(subdomain, passHash, salt))
        return parsed

    def __parseTCPs(self, tcps: list[tuple[str, str, str]]):
        parsed: list[OpenTCP] = []
        for i in tcps:
            port = i[0]
            passHash = i[1]
            salt = i[2]
            parsed.append(OpenTCP(port, passHash, salt))
        return parsed

    def __bakeOnTCP(self, port: int, clientSocket: SocketConnection):
        async def __onTCP(requestSocket: SocketConnection):
            server = self.__tcpServers.get(port, None)
            if server is None:
                requestSocket.close()
                clientSocket.close()
                return
            requestID = server.register_request_id(requestSocket)
            clientSocket.write(f'request;{requestID};'.encode('utf-8'))
            await clientSocket.flush()
        return __onTCP

    def __getHostHeader(self, requestHeader : str):
        for line in requestHeader.split('\n'):
            content = line.strip().rstrip()
            if content.startswith('Host: '):
                return content[6:]
        return None

    def generateHTTPResponse(self, msg : str):
        utctime = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S UTC')
        return f'HTTP/1.1 200 OK\r\nServer: Werkzeug/2.2.2 Python/3.11.0\r\nDate: {utctime}\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: {len(msg)}\r\nConnection: close\r\n\r\n{msg}'

    async def __onHTTP(self, sc: SocketConnection):
        buffer = await sc.readuntil_any([b'\r\n\r\n', b'\n\n'])
        if buffer is None:
            sc.close()
            return
        buffer = buffer.decode('utf-8')
        hostHeader = self.__getHostHeader(buffer)
        if hostHeader is None or not hostHeader.endswith('yazaar.xyz'):
            sc.write(self.generateHTTPResponse(f'<h1>Invalid host</h1><p>The host {hostHeader} is invalid</p>').encode('utf-8'))
            await sc.flush()
            sc.close()
            return
        subdomain = hostHeader[:-11]

        server = self.__httpServers.get(subdomain)
        if server is None:
            sc.write(self.generateHTTPResponse(f'<h1>No host connection</h1><p>The host {hostHeader} is not connected</p>').encode('utf-8'))
            await sc.flush()
            sc.close()
            return

        sc.push_back(buffer.encode('utf-8'))
        newRequestID = server.register_request_id(sc)
        server.server.write(f'request;{newRequestID};'.encode('utf-8'))
        await server.server.flush()

    async def __onClient(self, sc: SocketConnection):
        action = await sc.readuntil(b';')
        if action == b'auth;':
            await self.__onAuth(sc)
        elif action == b'bind;':
            await self.__onBind(sc)

    async def __onAuth(self, sc: SocketConnection):
        protocol = await sc.readuntil(b';')
        if protocol == b'tcp;':
            await self.__authTCP(sc)
        elif protocol == b'http;':
            await self.__authHTTP(sc)
        else:
            sc.close()

    async def __authTCP(self, sc: SocketConnection):
        port = (await sc.readuntil(b';'))[:-1]
        try:
            port = int(port)
        except Exception:
            sc.close()
            return

        authKey = (await sc.readuntil(b';'))[:-1]

        foundPort = self.__getOpenPort(port)
        if foundPort is None:
            sc.write(b'0a;')
            await sc.flush()
            sc.close()
            return
        if not foundPort.match(authKey):
            sc.write(b'0b;')
            await sc.flush()
            sc.close()
            return
        if self.__portTaken(foundPort.port):
            sc.write(b'0c;')
            await sc.flush()
            sc.close()
            return

        sc.write(b'1;')
        await sc.flush()

        identifier = f'{port}.tcp'
        self.__tcpServers[port] = SocketServer(await create_server('0.0.0.0', port, self.__bakeOnTCP(port, sc), identifier), identifier)

        while True:
            if await sc.read(1024) == b'':
                if port in self.__tcpServers:
                    self.__tcpServers[port].close()
                    del self.__tcpServers[port]
                break

    async def __authHTTP(self, sc: SocketConnection):
        subdomain = (await sc.readuntil(b';'))[:-1].decode('utf-8')
        authkey = (await sc.readuntil(b';'))[:-1]

        openWeb = self.__getMatchingWeb(subdomain)
        if openWeb is None:
            sc.write(b'0a;')
            await sc.flush()
            sc.close()
            return
        if not openWeb.match(authkey):
            sc.write(b'0b;')
            await sc.flush()
            sc.close()
            return
        if self.__webTaken(openWeb.subdomain):
            sc.write(b'0c;')
            await sc.flush()
            sc.close()
            return

        sc.write(b'1;')
        await sc.flush()
        self.__httpServers[subdomain] = HTTPServer(sc, f'{subdomain}.http')

        while True:
            try: data = await sc.readuntil(b';')
            except asyncio.IncompleteReadError:
                sc.close()
                if subdomain in self.__httpServers: del self.__httpServers[subdomain]
                break
            if data == b'ping;':
                sc.write(b'pong;')
                await sc.flush()

    def __getMatchingWeb(self, subdomain: str):
        for i in self.__openWebs:
            if i.subdomain == subdomain:
                return i

    def __webTaken(self, subdomain : str):
        server = self.__httpServers.get(subdomain, None)
        if server is None: return False
        return True

    def __getOpenPort(self, port: int):
        for i in self.__openTCPs:
            if i.port == port:
                return i

    def __portTaken(self, port: int):
        server = self.__tcpServers.get(port, None)
        if server is None: return False
        return server.is_open

    def __getTCPClient(self, id_port_str : str, request_id : str):
        try: id_port = int(id_port_str)
        except Exception: return None
        server = self.__tcpServers.get(id_port, None)
        if server is None: return None
        return server.get_request_id(request_id)

    def __getHTTPClient(self, id_endpoint : str, request_id : str):
        server = self.__httpServers.get(id_endpoint, None)
        if server is None: return None
        return server.get_request_id(request_id)

    async def __onBind(self, sc: SocketConnection):
        requestID = (await sc.readuntil(b';'))[:-1].decode('utf-8')
        try:
            index = requestID.index('+')
        except ValueError:
            sc.close()
            return
        identifier = requestID[:index]
        identifier = identifier.rsplit('.', 1)
        if len(identifier) != 2 or identifier[1] not in ['http', 'tcp']:
            sc.write(b'Invalid request identifier')
            await sc.flush()
            sc.close()
            return
        id_method = identifier[1]
        if id_method == 'tcp': client = self.__getTCPClient(identifier[0], requestID)
        elif id_method == 'http': client = self.__getHTTPClient(identifier[0], requestID)
        else:
            sc.write(b'Invalid identifier method (tcp/http)')
            await sc.flush()
            sc.close()
            return

        if not isinstance(client, SocketConnection):
            sc.write(b'Invalid request identifier')
            await sc.flush()
            sc.close()
            return

        loop = asyncio.get_event_loop()
        loop.create_task(self.__passthrough(client, sc))
        loop.create_task(self.__passthrough(sc, client))

    async def __passthrough(self, reader: SocketConnection, writer: SocketConnection):
        while True:
            data = await reader.read(2048)
            if not data:
                break
            writer.write(data)
            await writer.flush()

async def main():
    https = []
    tcps = []

    serversFile = pathlib.Path(__file__).parent / 'tunnelServers.csv'
    basedomainFile = pathlib.Path(__file__).parent / 'basedomain.txt'

    if serversFile.is_file():
        with open(serversFile, 'r') as f:
            f.readline() # get rid of head
            while True:
                components = f.readline().strip().rstrip().split(',')
                if len(components) != 4: break
                if components[0] == 'tcp':
                    try: port = int(components[1])
                    except Exception:
                        print('Invalid port for TCP, should be a number (con)')
                        return
                    passhash = components[2]
                    passSalt = components[3]
                    tcps.append((port, passhash, passSalt))
                elif components[0] == 'http':
                    subdomain = components[1]
                    passhash = components[2]
                    passSalt = components[3]
                    https.append((subdomain, passhash, passSalt))
    else:
        with open(serversFile, 'w') as f:
            f.write('type,con,sha256hex,salt')

    if basedomainFile.is_file():
        with open(basedomainFile, 'r') as f:
            currentBasedomain = f.read()
    else:
        with open(basedomainFile, 'w') as f: f.write('')
        currentBasedomain = ''

    if re.match(r'^[a-zA-Z0-9]+\.[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)?$', currentBasedomain) is None:
        print('Invalid domain in basedomain.txt')
        return

    if len(https) == 0 and len(tcps) == 0:
        print('No tunneled ports, exiting')
        return

    ts = TunnelServer(https, tcps)

    print('Starting TunnelServer')

    await ts.start()
    await ts.join()

if __name__ == '__main__':
    asyncio.run(main())
