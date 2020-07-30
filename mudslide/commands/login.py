from . base import Command, CmdError


class ConnectCommand(Command):
    name = 'connect'

    async def func(self):
        if not ((username := self.match.get('lhs')) and (password := self.match.get('rhs'))):
            raise CmdError('Usage: create <username or email>=<password>')
        service = self.app.services['account']
        account = await service.process_authentication(self.caller, username, password)
        await self.caller.game_login(account)


class CreateCommand(Command):
    name = 'create'

    async def func(self):
        if not ((username := self.match.get('lhs')) and (password := self.match.get('rhs'))):
            raise CmdError('Usage: create <username>=<password>')
        account = await self.app.services['account'].create_account(self.caller, username, password)
        await self.caller.game_login(account)


class HelpCommand(Command):
    name = 'help'


class LookCommand(Command):
    name = 'look'
    aliases = ['l']

    async def func(self):
        print("LOOK IS BEING CALLED!")
        await self.caller.game_connect_screen()


