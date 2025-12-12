import asyncio, sys, os, hashlib, logging
from helpers import CSVReader, SocketWrapper, misc, create_host
from genericHost import GenericHost
from handlers import TcpProtocolHandler, HttpProtocolHandler, UdpProtocolHandler
from DTLAuth.setupDTLAuth import setupDTLAuth

logger = logging.getLogger(__name__)

class TunnelHost:
    def __init__(self, csvReader: CSVReader, parsed_argv: dict[str, str]):
        self.__tcps: list[GenericHost] = []
        self.__https: list[GenericHost] = []
        self.__udps: list[GenericHost] = []

        self.tcp_server_port = misc.to_int(parsed_argv.get('tcpPort', None), None) or misc.to_int(os.getenv('TCP_SERVER_PORT', None), None) or 9000
        self.http_server_port = misc.to_int(parsed_argv.get('httpPort', None), None) or misc.to_int(os.getenv('HTTP_SERVER_PORT', None), None) or 8000

        misc.validate_port(self.tcp_server_port)
        misc.validate_port(self.http_server_port)

        if self.tcp_server_port == self.http_server_port:
            raise ValueError('TCP and HTTP port can\'t be the same')

        self.__tcp_server = create_host('0.0.0.0', self.tcp_server_port, self.__on_tcp_access, None)
        self.__http_server = create_host('0.0.0.0', self.http_server_port, self.__on_http_access, None)

        for i in csvReader.data:
            type_ = i['type']
            con = i['con']
            sha256hex = i['sha256hex']
            salt = i['salt']

            if type_ == 'tcp': self.__tcps.append(GenericHost('tcp', con, sha256hex, salt))
            elif type_ == 'http': self.__https.append(GenericHost('http', con, sha256hex, salt))
            elif type_ == 'udp': self.__udps.append(GenericHost('udp', con, sha256hex, salt))

        self.__tcp_handler = TcpProtocolHandler(self.__tcps)
        self.__http_handler = HttpProtocolHandler(self.__https)
        self.__udp_handler = UdpProtocolHandler(self.__udps)

    async def start(self):
        await self.__tcp_server.start()
        await self.__http_server.start()
        logger.info(f'Started servers on ports: tcp={self.tcp_server_port}, http={self.http_server_port}')
    
    async def auth_request(self, ip: str, resourceType: str, resourceItem: str, resourceCode: str):
        if resourceType == 'tcp':
            return await self.__tcp_handler.auth_request(ip, resourceItem, resourceCode)
        elif resourceType == 'http':
            return await self.__http_handler.auth_request(ip, resourceItem, resourceCode)
        elif resourceType == 'udp':
            return await self.__udp_handler.auth_request(ip, resourceItem, resourceCode)
        return False 

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
        if not stream:
            connection.close()
            return
        try: parsed = misc.deserialize(stream)
        except Exception:
            connection.close()
            return

        if not isinstance(parsed, dict) or not 'type' in parsed or not 'resource' in parsed or not 'command' in parsed:
            connection.close()
            return
        
        command = parsed['command']

        if command == 'authenticate':
            await self.__handle_tcp_authenticate(parsed, connection)
        elif command == 'bind':
            await self.__handle_tcp_bind(parsed, connection)
        else:
            connection.close()
            return

    async def __handle_tcp_authenticate(self, data: dict, connection: SocketWrapper):
        if not 'secret' in data:
            connection.close()
            return
        if data['type'] == 'tcp':
            await self.__tcp_handler.authenticate(data, connection)
        elif data['type'] == 'http':
            await self.__http_handler.authenticate(data, connection)
        elif data['type'] == 'udp':
            await self.__udp_handler.authenticate(data, connection)
        else:
            connection.close()

    async def __handle_tcp_bind(self, data: dict, connection: SocketWrapper):
        if not 'identifier' in data:
            connection.close()
            return
        
        data_type = data['type']

        if data_type == 'tcp':
            await self.__tcp_handler.bind(data, connection)
        elif data_type == 'http':
            await self.__http_handler.bind(data, connection)
        elif data_type == 'udp':
            await self.__udp_handler.bind(data, connection)
        else:
            connection.close()

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

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
    th = TunnelHost(csvReader, parsed_argv)
    await th.start()
    logger.info('Tunnel host started')
    await setupDTLAuth(parsed_argv, th.auth_request)
    await misc.run_forever()

if __name__ == '__main__':
    asyncio.run(main())
