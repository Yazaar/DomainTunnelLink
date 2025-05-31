from helpers import misc
from helpers.socketWrapper import SocketWrapper

class SocketRegistry:
    def __init__(self) -> None:
        self.clients: dict[str, SocketWrapper] = {}

    def register(self, connection: SocketWrapper):
        identifier = misc.new_uuid()
        self.clients[identifier] = connection
        return identifier

    def pop(self, identifier: str):
        return self.clients.pop(identifier, None)
