from honahlee.core import BaseService
from honahlee.utils.misc import fresh_uuid4


class ConnectionService(BaseService):
    """
    This service keeps track of all active game client connections, telnet or otherwise.
    """

    def __init__(self):
        self.connections = dict()

    def register_connection(self, conn):
        new_uuid = fresh_uuid4(self.connections.keys())
        conn.conn_id = new_uuid
        self.connections[conn.conn_id] = conn

    def unregister_connection(self, conn):
        del self.connections[conn.conn_id]
