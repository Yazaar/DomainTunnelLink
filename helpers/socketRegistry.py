from helpers import misc, SocketWrapper

class RegistryItem:
    def __init__(self, identifier: str, socket: SocketWrapper):
        self.identifier = identifier
        self.socket = socket

class SocketRegistry:
    def __init__(self, max_size: int = 0) -> None:
        self.max_size = max_size
        self.clients: list[RegistryItem] = []

    def register(self, connection: SocketWrapper):
        identifier = misc.new_uuid()
        self.clients.append(RegistryItem(identifier, connection))

        while self.max_size > 0 and len(self.clients) > self.max_size:
            item = self.clients.pop(0)
            item.socket.close()

        return identifier

    def pop(self, identifier: str):
        item: RegistryItem | None = misc.find_first(self.clients, lambda item: item.identifier == identifier)
        if not item: return None
        try: self.clients.remove(item)
        except Exception: pass
        return item.socket
