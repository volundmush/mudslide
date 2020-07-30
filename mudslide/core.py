import re
from honahlee.core import BaseConfig as HonahleeConfig
from hypercorn.config import Config as HyperConfig


class BaseConfig(HonahleeConfig):
    lib_name = 'mudslide'

    def __init__(self):
        super().__init__()
        self.name = 'mudslide'
        self.web_servers = dict()
        from django.conf import global_settings as g
        self.django_settings = {k: v for k, v in g.__dict__.items() if k.isupper()}
        self.django_settings_final = None
        self.hyper_config = HyperConfig()
        self.user_options = dict()

    def setup(self):
        super().setup()
        self._config_django()
        self._config_ansi()
        self._init_django()
        self._config_web_servers()
        self._init_hypercorn()
        self._config_user_options()

    def _config_classes(self):
        super()._config_classes()
        # Services
        self.classes['services']['connect_screen'] = 'mudslide.services.conscreen.ConnectScreenService'
        self.classes['services']['connections'] = 'mudslide.services.connections.ConnectionService'
        self.classes['services']['web'] = 'mudslide.services.web.WebService'
        self.classes['services']['input'] = 'mudslide.services.input.InputService'
        self.classes['services']['entity'] = 'mudslide.services.entity.EntityService'
        self.classes['services']['account'] = 'mudslide.services.account.AccountService'
        self.classes['services']['game'] = 'mudslide.services.game.GameService'

        # Backends
        self.classes['backends']['account'] = 'mudslide.services.account.AccountBackend'

        # Protocols
        self.classes['protocols']['telnet'] = 'mudslide.protocols.telnet.TelnetAsgiProtocol'

        # Consumers for Django Channels
        self.classes['consumers']['telnet'] = 'mudslide.protocols.telnet.AsyncTelnetConsumer'
        self.classes['consumers']['game'] = 'mudslide.services.web.GameConsumer'
        self.classes['consumers']['link'] = 'mudslide.services.web.LinkConsumer'
        self.classes['consumers']['lifespan'] = 'mudslide.services.web.LifespanAsyncConsumer'

        # Entities
        self.classes['entities']['account'] = 'mudslide.entities.account.AccountEntity'
        self.classes['entities']['game'] = 'mudslide.entities.game.GameEntity'
        self.classes['entities']['player'] = 'mudslide.entities.player.PlayerEntity'

        # Listeners
        self.classes['listeners']['python'] = 'mudslide.utils.listeners.PythonConsoleListener'

        # Login Commands
        self.classes['commands_login']['connect'] = 'mudslide.commands.login.ConnectCommand'
        self.classes['commands_login']['create'] = 'mudslide.commands.login.CreateCommand'
        self.classes['commands_login']['help'] = 'mudslide.commands.login.HelpCommand'
        self.classes['commands_login']['look'] = 'mudslide.commands.login.LookCommand'

        # Minus commands
        self.classes['commands_minus']['-py'] = 'mudslide.commands.system.PyCommand'
        self.classes['commands_minus']['-account'] = 'mudslide.commands.account.AccountCommand'

        # Auth Commands go here.

        # Misc Classes go here
        self.classes['mudslide']['styler'] = 'mudslide.utils.styling.Styler'
        self.classes['mudslide']['option'] = 'mudslide.utils.options.OptionHandler'

    def _config_django(self):
        d = self.django_settings

        d['INSTALLED_APPS'] = [
            "channels",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sessions",
            "django.contrib.admin",
            "django.contrib.admindocs",
            "django.contrib.flatpages",
            "django.contrib.sites",
            "django.contrib.staticfiles",
            "django.contrib.messages",
            "rest_framework",
            "django_filters",
            "sekizai",
            'mudslide'
        ]

        d['USE_TZ'] = True
        d['TIME_ZONE'] = 'Etc/UTC'

        d['AUTH_USER_MODEL'] = 'mudslide.Account'

        d['TEMPLATES'] = []

        d['MIDDLEWARE'] = [
            "django.middleware.common.CommonMiddleware",
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",  # 1.4?
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.middleware.csrf.CsrfViewMiddleware",
            "django.contrib.admindocs.middleware.XViewMiddleware",
            "django.contrib.flatpages.middleware.FlatpageFallbackMiddleware",
        ]

        d['MEDIA_ROOT'] = ''
        d['MEDIA_URL'] = ''

        d['STATIC_ROOT'] = None
        d['STATIC_URL'] = None
        d['STATICFILES_DIRS'] = []

        d['DATABASES'] = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": "game.sqlite3",
                "USER": "",
                "PASSWORD": "",
                "HOST": "",
                "PORT": "",
            }
        }

    def _config_ansi(self):
        from mudslide.settings import settings as ansi_settings
        pass

    def _init_django(self):
        import django
        from django.conf import settings
        settings.configure(**self.django_settings)
        self.django_settings_final = settings
        django.setup()

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

    def _config_regex(self):
        super()._config_regex()
        self.regex['entity_name'] = re.compile(r"^(\w+|\.|-|')+( (\w+|\.|-|')+)*$")

    def _config_user_options(self):
        pass
