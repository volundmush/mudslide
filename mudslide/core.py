from honahlee.core import BaseConfig as HonahleeConfig
from hypercorn.config import Config as HyperConfig

class BaseConfig(HonahleeConfig):
    pass

    def __init__(self):
        super().__init__()
        self.web_servers = dict()
        self.hyper_config = HyperConfig()

    def setup(self):
        super().setup()
        self._config_web_servers()
        self._init_hypercorn()

    def _config_classes(self):
        super()._config_classes()

        self.classes['protocols']['telnet'] = 'honahlee.protocols.telnet.TelnetAsgiProtocol'
        self.classes['consumers']['telnet'] = 'honahlee.protocols.telnet.AsyncTelnetConsumer'
        self.classes['consumers']['game'] = 'honahlee.services.web.GameConsumer'
        self.classes['consumers']['link'] = 'honahlee.services.web.LinkConsumer'
        self.classes['consumers']['lifespan'] = 'honahlee.services.web.LifespanAsyncConsumer'

    def _config_servers(self):
        self.servers['telnet'] = {
            'port': 4100,
            'interface': 'external',
            'server_class': 'base',
            'protocol_class': 'telnet',
            'tls': None
        }

    def _config_web_servers(self):
        self.web_servers = {
            'port': 8000,
            'interface': 'external',
            'tls': None
        }

    def _init_hypercorn(self):
        inter = self.interfaces.get(self.web_servers.get('interface'))
        self.hyper_config.bind = [f"{inter}:{self.web_servers.get('port')}"]
