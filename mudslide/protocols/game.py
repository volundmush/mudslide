from channels.consumer import StopConsumer
from channels.auth import login, logout


class AsyncGameConsumerMixin:
    """
    This is a class meant to be added to any Async Consumer that's supposed to be interacting
    as a Game Client.
    """
    # This is a class property that will be set to the CORE APPLICATION.
    app = None
    service = None

    def game_setup(self):
        self.game_id = None
        self.logged_in = None
        self.conn_id = None

    async def game_login(self, account):
        """
        Log this consumer in to the game via Django.

        Args:
            account (User): The Django User account to bind to this Consumer.
        """
        await login(self.scope, account)
        self.logged_in = True

    async def game_logout(self):
        await logout(self.scope)
        self.logged_in = False

    async def game_close(self, reason):
        """
        Call all cleanup routines and close this consumer. This can be triggered by either the client
        or the server.

        Args:
            reason (str): The reason for this closing.
        """
        self.app.services['connections'].unregister_connection(self)
        raise StopConsumer(reason)

    async def game_input(self, cmd, *args, **kwargs):
        """
        Processes input from players in Inputfunc Format. See Evennia specs for details.
        """
        if not self.conn_id:
            # If this connection is not yet registered, ignore all input.
            return
        if (func := self.app.input_funcs.get(cmd, None)):
            await func(self, cmd, *args, **kwargs)

    async def game_link(self, game):
        pass

    async def game_unlink(self, game):
        pass

    async def game_connect(self):
        """
        This is called when a client has finished all protocol-level setup and is ready to begin talking to game logic.
        """
        self.app.services['connections'].register_connection(self)
        await self.game_connect_screen()

    async def game_connect_screen(self):
        """
        This sends the Connect Screen to this client.
        """
        await self.send({
            'type': 'text',
            'data': self.app.services['connect_screen'].render(self)
        })
