import logging
from typing import List
from helpers import SocketWrapper, misc
from genericHost import GenericHost
from handlers import ProtocolHandler

logger = logging.getLogger(__name__)


class TcpProtocolHandler(ProtocolHandler):
    def __init__(self, resources: List[GenericHost]):
        self.resources = resources
    
    def find_resource(self, resource: str) -> GenericHost | None:
        port = misc.to_int(resource, None)
        if not port:
            return None
        
        return misc.find_first(self.resources, lambda x: x.con == port)
    
    async def authenticate(self, data: dict, connection: SocketWrapper) -> None:
        resource = data['resource']
        tcp_host = self.find_resource(resource)
        
        if not isinstance(tcp_host, GenericHost):
            connection.close()
            return
        
        await tcp_host.bind(data, connection)
    
    async def bind(self, data: dict, connection: SocketWrapper) -> None:
        resource = data['resource']
        tcp_host: GenericHost | None = self.find_resource(resource)
        
        if not isinstance(tcp_host, GenericHost):
            connection.close()
            return
        
        await tcp_host.new_client(data, connection)
    
    async def auth_request(self, ip: str, resource_item: str, resource_code: str) -> bool:
        port = misc.to_int(resource_item, None)
        if not port:
            return False
        
        tcp = misc.find_first(self.resources, lambda x: x.con == port)
        if not isinstance(tcp, GenericHost):
            return False
        
        return await tcp.auth_request(ip, resource_code)
