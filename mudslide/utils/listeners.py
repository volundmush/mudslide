import code
import sys

class BaseListener:
    """
    A 'listener' is a class that's instantiated by the InputService and attached to a Connection.
    It's meant to intercept text input.
    This is the foundation of all menu-driven input systems.
    """
    app = None

    def __init__(self, connection):
        self.connection = connection

    async def process_input(self, raw, *args, **kwargs):
        pass

    async def start(self):
        pass


class PythonConsoleListener(code.InteractiveConsole, BaseListener):
    """
    Borrowed / inspired from Evennia's EvenniaPythonConsole.
    """

    def __init__(self, connection):
        self.connection = connection
        super(PythonConsoleListener, self).__init__(locals={'self': connection, 'app': self.app})

    def write(self, string):
        self.connection.msg(text=string)

    def push(self, line):
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        sys.stdout = self
        sys.stderr = self
        super().push(line)
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    async def process_input(self, raw, *args, **kwargs):
        if raw == 'exit':
            inp_srv = self.app.services['input']
            await inp_srv.stop_listener(self.connection)
            self.connection.msg("Left Python interpreter!")
            return
        result = self.push(raw)
        # self.write(str(result))
