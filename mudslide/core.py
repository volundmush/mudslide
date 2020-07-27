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

    def setup(self):
        super().setup()
        self._config_django()
        self._config_ansi()
        self._init_django()
        self._config_web_servers()
        self._init_hypercorn()

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

        # Login Commands
        self.classes['commands_login']['connect'] = 'mudslide.commands.login.ConnectCommand'
        self.classes['commands_login']['create'] = 'mudslide.commands.login.CreateCommand'
        self.classes['commands_login']['help'] = 'mudslide.commands.login.HelpCommand'
        self.classes['commands_login']['look'] = 'mudslide.commands.login.LookCommand'

        # Auth Commands go here.

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
        d = self.django_settings

        # Mapping to extend Evennia's normal ANSI color tags. The mapping is a list of
        # tuples mapping the exact tag (not a regex!) to the ANSI convertion, like
        # `(r"%c%r", ansi.ANSI_RED)` (the evennia.utils.ansi module contains all
        # ANSI escape sequences). Default is to use `|` and `|[` -prefixes.
        d['COLOR_ANSI_EXTRA_MAP'] = []
        # Extend the available regexes for adding XTERM256 colors in-game. This is given
        # as a list of regexes, where each regex must contain three anonymous groups for
        # holding integers 0-5 for the red, green and blue components Default is
        # is r'\|([0-5])([0-5])([0-5])', which allows e.g. |500 for red.
        # XTERM256 foreground color replacement
        d['COLOR_XTERM256_EXTRA_FG'] = []
        # XTERM256 background color replacement. Default is \|\[([0-5])([0-5])([0-5])'
        d['COLOR_XTERM256_EXTRA_BG'] = []
        # Extend the available regexes for adding XTERM256 grayscale values in-game. Given
        # as a list of regexes, where each regex must contain one anonymous group containing
        # a single letter a-z to mark the level from white to black. Default is r'\|=([a-z])',
        # which allows e.g. |=k for a medium gray.
        # XTERM256 grayscale foreground
        d['COLOR_XTERM256_EXTRA_GFG'] = []
        # XTERM256 grayscale background. Default is \|\[=([a-z])'
        d['COLOR_XTERM256_EXTRA_GBG'] = []
        # ANSI does not support bright backgrounds, so Evennia fakes this by mapping it to
        # XTERM256 backgrounds where supported. This is a list of tuples that maps the wanted
        # ansi tag (not a regex!) to a valid XTERM256 background tag, such as `(r'{[r', r'{[500')`.
        d['COLOR_ANSI_XTERM256_BRIGHT_BG_EXTRA_MAP'] = []
        # If set True, the above color settings *replace* the default |-style color markdown
        # rather than extend it.
        d['COLOR_NO_DEFAULT'] = False

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
