from . base import Command, CmdError


class PyCommand(Command):
    """
    This is an incredibly dangerous command that exposes a Python interpreter to this connection.
    """
    name = '-py'

    async def func(self):
        con_class = self.app.classes['listeners']['python']
        inp_srv = self.app.services['input']
        await inp_srv.start_listener(self.caller, con_class(self.caller))
        self.caller.msg("Entered Python Interpreter...")

    @classmethod
    def access(cls, caller):
        return caller.is_superuser()
