from abc import ABC, abstractmethod
from helpers import SocketWrapper
from genericHost import GenericHost


class ProtocolHandler(ABC):
    @abstractmethod
    def find_resource(self, resource: str) -> GenericHost | None:
        pass
    
    @abstractmethod
    async def authenticate(self, data: dict, connection: SocketWrapper) -> None:
        pass
    
    @abstractmethod
    async def bind(self, data: dict, connection: SocketWrapper) -> None:
        pass
    
    @abstractmethod
    async def auth_request(self, ip: str, resource_item: str, resource_code: str) -> bool:
        pass
