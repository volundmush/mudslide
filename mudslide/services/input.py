import re
from honahlee.core import BaseService


class CommandContainer:

    def __init__(self, name, service, cmd_dict):
        self.name = name
        self.service = service
        self.commands = cmd_dict
        self.aliases = dict()
        for name, cmd in self.commands.items():
            self.aliases[cmd.name] = cmd
            for alias in cmd.aliases:
                self.aliases[alias] = cmd

    def get(self, command, caller):
        if (cmd := self.aliases.get(command.lower())) and cmd.access(caller):
            return cmd
        return None


class InputService(BaseService):
    cmd_match = re.compile(r"(?si)^(?P<prefix>[@+?$&%-]+)?(?P<cmd>\w+)(?P<switches>(\/\S+)+?)?(?:\s+(?P<args>(?P<lhs>[^=]+)(?:=(?P<rhs>.*))?)?)?")

    def __init__(self):
        self.containers = dict()

    def setup(self):
        for k, v in self.app.classes.items():
            if k.startswith('commands_'):
                pfx, name = k.split('_', 1)
                self.containers[name] = CommandContainer(name, self, v)

    async def input_text(self, connection, cmd, *args, **kwargs):
        if not len(args) > 0:
            return
        raw = args[0].strip()
        match = self.cmd_match.match(raw).groupdict()

        if connection.is_authenticated():
            pass
        else:
            await self.run_login_command(connection, raw, match)

    async def run_login_command(self, conn, raw, match):
        if not (cmd_name := match.get('cmd', None)):
            return
        login = self.containers['login']
        if not (cmd := login.get(cmd_name, conn)):
            print("BAD COMMAND")
            return
        new_cmd = cmd(conn, raw, match)
        print(new_cmd)
        await new_cmd.execute()
        #self.app.loop.create_task(new_cmd.execute())

    async def unrecognized_input(self, connection, cmd, *args, **kwargs):
        pass
