import logging
from typing import List
from helpers import SocketWrapper, misc
from genericHost import GenericHost
from handlers import ProtocolHandler

logger = logging.getLogger(__name__)


class HttpProtocolHandler(ProtocolHandler):
    def __init__(self, resources: List[GenericHost]):
        self.resources = resources
    
    def find_resource(self, resource: str) -> GenericHost | None:
        if not resource:
            return None
        
        return misc.find_first(self.resources, lambda x: x.con == resource)
    
    async def authenticate(self, data: dict, connection: SocketWrapper) -> None:
        resource = data['resource']
        http_host = self.find_resource(resource)
        
        if not isinstance(http_host, GenericHost):
            connection.close()
            return
        
        await http_host.bind(data, connection)
    
    async def bind(self, data: dict, connection: SocketWrapper) -> None:
        resource = data['resource']
        http_host: GenericHost | None = self.find_resource(resource)
        
        if not isinstance(http_host, GenericHost):
            connection.close()
            return
        
        await http_host.new_client(data, connection)
    
    async def auth_request(self, ip: str, resource_item: str, resource_code: str) -> bool:
        if not resource_item:
            return False
        
        http = misc.find_first(self.resources, lambda x: x.con == resource_item)
        if not isinstance(http, GenericHost):
            return False
        
        return await http.auth_request(ip, resource_code)
