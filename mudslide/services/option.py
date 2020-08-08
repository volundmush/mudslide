from honahlee.core import BaseService


class OptionService(BaseService):

    def __init__(self):
        super().__init__()
        self.options = dict()

    def setup(self):
        for name, op_def in self.app.config.options.items():
            op_class = self.app.classes['options'][op_def['class']]
            self.options[name] = op_class(self, name, op_def['description'], op_def['default'])

    def get(self, connection, option):
        op = self.options[option]
        return op.get(connection)
