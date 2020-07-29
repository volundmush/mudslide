import re
import traceback
from honahlee.utils.text import partial_match


class CmdError(Exception):
    pass


class Command:
    """
    Base class for all Commands that will be executed by Mudslide
    """
    app = None
    name = None
    service_key = None
    command_category = None
    help_category = None
    aliases = []
    switch_options = dict()

    def __init__(self, caller, raw_command, match):
        self.caller = caller
        self.raw_command = raw_command
        self.match = match
        self.service = self.app.services.get(self.service_key, None)
        self.chosen_switch = None
        self.extra_switches = list()
        self.args = match['args'].strip()
        self.lhs = match['lhs'].strip()
        self.rhs = match['rhs'].strip()

    @classmethod
    def access(cls, caller):
        return True

    def parse(self):
        if self.switch_options and (switches := self.match.get('switches', None)):
            viable_switches = [key for key in self.switch_options.keys() if key]
            if not (found := partial_match(switches[0]), viable_switches):
                raise CmdError(f"Command {self.name} does not support switch {switches[0]}!")
            self.chosen_switch = found
            if len(switches) > 1:
                self.extra_switches = switches[1:]

    async def func(self):
        """
        Executes the command.
        """
        pass

    async def at_pre_execute(self):
        pass

    async def get_command_info(self):
        pass

    async def run(self):
        if self.chosen_switch:
            await getattr(self, f"func_{self.chosen_switch}")()
        else:
            await self.func()

    async def execute(self):
        try:
            self.parse()
            await self.at_pre_execute()
            await self.run()
            await self.at_post_execute()
        except CmdError as e:
            if self.caller:
                self.caller.msg(text=str(e))
            return
        except Exception as e:
            if self.caller:
                if self.app.config.debug_mode:
                    traceback.print_exc(file=self.caller)
                else:
                    self.caller.msg(text=f"Sorry, the {self.name} command encountered an error. Please contact coder.")
                    traceback.print_exc(file=self.app.config.logs['application'])


    async def at_post_execute(self):
        pass

    def syntax_error(self):
        raise CmdError(f'Usage: {self.switch_options[self.chosen_switch]["usage"]}')
