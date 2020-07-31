from channels.consumer import StopConsumer
from channels.auth import login, logout
from honahlee.utils.misc import lazy_property


class AsyncGameConsumerMixin:
    """
    This is a class meant to be added to any Async Consumer that's supposed to be interacting
    as a Game Client.
    """
    # This is a class property that will be set to the CORE APPLICATION.
    app = None

    @lazy_property
    def styling(self):
        return self.app.classes['mudslide']['styler'](self)

    @lazy_property
    def options(self):
        return self.app.classes['mudslide']['option'](self)

    def game_setup(self):
        self.game_id = None
        self.logged_in = None
        self.conn_id = None
        self.account = None

    async def game_login(self, account):
        """
        Log this consumer in to the game via Django.

        Args:
            account (User): The Django User account to bind to this Consumer.
        """
        await login(self.scope, account.account_model)
        self.logged_in = True
        self.account = account
        await self.at_game_login()

    async def at_game_login(self):
        await self.send({
            'type': 'text',
            'data': f'You have successfully logged in as {self.scope["user"]}'
        })

    async def game_logout(self):
        await logout(self.scope)
        self.logged_in = False
        self.account = None

    async def game_close(self, reason):
        """
        Call all cleanup routines and close this consumer. This can be triggered by either the client
        or the server.

        Args:
            reason (str): The reason for this closing.
        """
        self.app.services['connections'].unregister_connection(self)
        if self.logged_in:
            await self.game_logout()
        raise StopConsumer(reason)

    async def game_input(self, cmd, *args, **kwargs):
        """
        Processes input from players in Inputfunc Format. See Evennia specs for details.
        """
        if not self.conn_id:
            # If this connection is not yet registered, ignore all input.
            return
        inp = self.app.services['input']
        func = getattr(inp, f'input_{cmd}', inp.unrecognized_input)
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

    def msg(self, text: str):
        self.scope['to_protocol'].put_nowait({
            'type': 'text',
            'data': text
        })

    def is_authenticated(self):
        return self.logged_in

    def see_debug(self):
        return self.is_superuser()

    def is_superuser(self):
        if not self.logged_in:
            return False
        return self.scope['user'].is_superuser

    def uses_screenreader(self):
        return False

    def get_account(self):
        if self.logged_in:
            return self.account
        return None
