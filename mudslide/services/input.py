import re
from honahlee.core import BaseService
import asyncio


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
            print(f"FOUND CMD! {cmd}")
            return cmd
        return None


class InputService(BaseService):
    cmd_match = re.compile(r"(?si)^(?P<prefix>[@+?$&%-=]+)?(?P<cmd>\w+)(?P<switches>(\/\S+)+?)?(?:\s+(?P<args>(?P<lhs>[^=]+)(?:=(?P<rhs>.*))?)?)?")

    def __init__(self):
        self.containers = dict()
        self.listeners = dict()

    def setup(self):
        for k, v in self.app.classes.items():
            if k.startswith('commands_'):
                pfx, name = k.split('_', 1)
                self.containers[name] = CommandContainer(name, self, v)
        print(self.containers['minus'].commands)

    async def input_text(self, connection, cmd, *args, **kwargs):
        if not len(args) > 0:
            return
        raw = args[0].strip()
        match = {k: v for k, v in self.cmd_match.match(raw).groupdict().items() if v is not None}

        if (listener := self.listeners.get(connection, None)):
            await listener.process_input(raw, *args, **kwargs)
            return

        if connection.is_authenticated():
            if raw.startswith('-'):
                await self.run_command_type('minus', connection, raw, match)
                return
            elif raw.startswith('='):
                await self.run_channel_command(connection, raw, match)
                return
            else:
                await self.send_link_command(connection, raw, match)
                return
        else:
            await self.run_command_type('login', connection, raw, match)

    async def run_command_type(self, cmd_type, conn, raw, match):
        cmd_name = f"{match.get('prefix', '')}{match.get('cmd', '')}"
        if not cmd_name:
            return
        cmds = self.containers[cmd_type]
        if not (cmd := cmds.get(cmd_name, conn)):
            await self.command_not_found(cmd_type, conn, raw, match)
            return
        new_cmd = cmd(conn, raw, match)
        asyncio.create_task(new_cmd.execute())

    async def run_channel_command(self, connection, raw, match):
        connection.msg("Not implemented yet!")

    async def unrecognized_input(self, connection, cmd, *args, **kwargs):
        pass

    async def command_not_found(self, cmd_type, conn, raw, match):
        conn.msg(text="Sorry, didn't recognize that command. Type 'help' for help.")

    async def send_link_command(self, connection, raw, match):
        connection.msg("Game Link not implemented yet!")

    async def start_listener(self, connection, listener):
        self.listeners[connection] = listener
        asyncio.create_task(listener.start())

    async def stop_listener(self, connection):
        if (listener := self.listeners.get(connection, None)):
            del self.listeners[connection]
