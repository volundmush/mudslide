import re


class CmdError(Exception):
    pass


class Command:
    """
    Base class for all Commands that will be executed by Mudslide
    """
    app = None
    name = None
    aliases = []

    def __init__(self, caller, raw_command, match):
        self.caller = caller
        self.raw_command = raw_command
        self.match = match

    @classmethod
    def access(cls, caller):
        return True

    async def parse(self):
        pass

    async def func(self):
        """
        Executes the command.
        """
        pass

    async def at_pre_execute(self):
        pass

    async def get_command_info(self):
        pass

    async def execute(self):
        await self.parse()
        await self.at_pre_execute()
        await self.func()
        await self.at_post_execute()

    async def at_post_execute(self):
        pass
