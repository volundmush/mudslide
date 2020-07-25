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
        self._init_django()
        self._config_web_servers()
        self._init_hypercorn()

    def _config_classes(self):
        super()._config_classes()
        self.classes['services']['connect_screen'] = 'mudslide.services.conscreen.ConnectScreenService'
        self.classes['services']['connections'] = 'mudslide.services.connections.ConnectionService'
        self.classes['services']['web'] = 'mudslide.services.web.WebService'
        self.classes['protocols']['telnet'] = 'mudslide.protocols.telnet.TelnetAsgiProtocol'
        self.classes['consumers']['telnet'] = 'mudslide.protocols.telnet.AsyncTelnetConsumer'
        self.classes['consumers']['game'] = 'mudslide.services.web.GameConsumer'
        self.classes['consumers']['link'] = 'mudslide.services.web.LinkConsumer'
        self.classes['consumers']['lifespan'] = 'mudslide.services.web.LifespanAsyncConsumer'


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
