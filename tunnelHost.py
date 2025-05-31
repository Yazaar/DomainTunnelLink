import asyncio, sys, hashlib
from helpers.csvReader import CSVReader
from helpers.socketHost import SocketHost
from helpers.socketWrapper import SocketWrapper
from helpers import misc
from genericHost import GenericHost
from DTLAuth.setupDTLAuth import setupDTLAuth

class TunnelHost:
    def __init__(self, csvReader: CSVReader):
        self.__tcps: list[GenericHost] = []
        self.__https: list[GenericHost] = []

        self.__tcpServer = SocketHost('0.0.0.0', 9000, self.__on_tcp_access)
        self.__httpServer = SocketHost('0.0.0.0', 8001, self.__on_http_access)

        for i in csvReader.data:
            type_ = i['type']
            con = i['con']
            sha256hex = i['sha256hex']
            salt = i['salt']

            if type_ == 'tcp': self.__tcps.append(GenericHost('tcp', con, sha256hex, salt))
            elif type_ == 'http': self.__https.append(GenericHost('http', con, sha256hex, salt))

    async def start(self):
        await self.__tcpServer.start()
        await self.__httpServer.start()
    
    async def auth_request(self, ip: str, resourceType: str, resourceItem: str, resourceCode: str):
        if resourceType == 'tcp':
            return await self.__auth_request_tcp(ip, resourceItem, resourceCode)
        elif resourceType == 'http':
            return await self.__auth_request_http(ip, resourceItem, resourceCode)

    async def __auth_request_http(self, ip: str, host: str, resourceCode: str):
        if not host:
            return False

        http = misc.find_first(self.__https, lambda x: x.con == host)
        if not isinstance(http, GenericHost):
            return False

        return await http.auth_request(ip, resourceCode) 

    async def __auth_request_tcp(self, ip: str, resourceItem: str, resourceCode: str):
        port = misc.to_int(resourceItem, None)
        if not port:
            return False

        tcp = misc.find_first(self.__tcps, lambda x: x.con == port)
        if not isinstance(tcp, GenericHost):
            return False

        return await tcp.auth_request(ip, resourceCode) 

    async def __on_http_access(self, connection: SocketWrapper):
        headers = await misc.http_identification(connection)
        domain = headers.get('host', None) if headers else None
        if not domain:
            connection.close()
            return

        httpHost = misc.find_first(self.__https, lambda httpHost: httpHost.con == domain)

        if not isinstance(httpHost, GenericHost):
            connection.write(misc.http_response(f'<h1>Invalid host</h1><p>The host {domain} is invalid</p>').encode())
            await connection.flush()
            connection.close()
            return
        
        misc.queue_task(httpHost.on_client(connection, headers=headers))

    async def __on_tcp_access(self, connection: SocketWrapper):
        stream = await connection.read_until(b';')
        try: parsed = misc.deserialize(stream)
        except Exception:
            connection.close()
            return

        if not isinstance(parsed, dict) or not 'type' in parsed or not 'resource' in parsed or not 'command' in parsed:
            connection.close()
            return

        if parsed['command'] == 'authenticate':
            await self.__handle_tcp_authenticate(parsed, connection)
        elif parsed['command'] == 'bind':
            await self.__handle_tcp_bind(parsed, connection)
        else:
            connection.close()
            return

    async def __handle_tcp_authenticate(self, data: dict, connection: SocketWrapper):
        if not 'secret' in data:
            connection.close()
            return
        if data['type'] == 'tcp':
            await self.__handle_tcp_authenticate_tcp(data, connection)
        elif data['type'] == 'http':
            await self.__handle_tcp_authenticate_http(data, connection)
        else:
            connection.close()

    async def __handle_tcp_authenticate_tcp(self, data: dict, connection: SocketWrapper):
        resource = data['resource']
        tcpHost = misc.find_first(self.__tcps, lambda tcpHost: tcpHost.con == resource)
        if not isinstance(tcpHost, GenericHost):
            connection.close()
            return
        await tcpHost.bind(data, connection)

    async def __handle_tcp_authenticate_http(self, data: dict, connection: SocketWrapper):
        resource = data['resource']
        httpHost = misc.find_first(self.__https, lambda tcpHost: tcpHost.con == resource)
        if not isinstance(httpHost, GenericHost):
            connection.close()
            return
        await httpHost.bind(data, connection)

    async def __handle_tcp_bind(self, data: dict, connection: SocketWrapper):
        if not 'identifier' in data:
            connection.close()
            return
        if data['type'] == 'tcp':
            await self.__handle_tcp_bind_tcp(data, connection)
        elif data['type'] == 'http':
            await self.__handle_tcp_bind_http(data, connection)
        else:
            connection.close()

    async def __handle_tcp_bind_tcp(self, data: dict, connection: SocketWrapper):
        resource = data['resource']
        tcpHost: GenericHost | None = misc.find_first(self.__tcps, lambda tcpHost: tcpHost.con == resource)
        if not isinstance(tcpHost, GenericHost):
            connection.close()
            return
        await tcpHost.new_client(data, connection)

    async def __handle_tcp_bind_http(self, data: dict, connection: SocketWrapper):
        resource = data['resource']
        httpHost: GenericHost | None = misc.find_first(self.__https, lambda httpHost: httpHost.con == resource)
        if not isinstance(httpHost, GenericHost):
            connection.close()
            return
        await httpHost.new_client(data, connection)

async def main():
    parsed_argv = misc.load_argv(sys.argv)

    if parsed_argv.get('sha256gen', None) == '1':
        auth = parsed_argv.get('auth', '')
        salt = parsed_argv.get('salt', '')
        if not auth or not salt:
            print('--auth or --salt missing')
            return
        full_auth = (auth + salt).encode('utf-8')
        print(hashlib.sha256(full_auth).hexdigest() + '\n')
        return

    file = misc.get_file('tunnel_servers.csv')
    csvReader = CSVReader(file)
    th = TunnelHost(csvReader)
    await th.start()
    print('Tunnel host started')
    await setupDTLAuth(parsed_argv, th.auth_request)
    await misc.run_forever()

if __name__ == '__main__':
    asyncio.run(main())
