from honahlee.core import BaseService


class ConnectScreenService(BaseService):

    def render(self, conn):
        return f"CONNECT SCREEN FOR {conn} HERE!"
