from honahlee.core import BaseService


class LinkService(BaseService):
    setup_order = -2000

    def __init__(self):
        super().__init__()
        self.links = dict()
